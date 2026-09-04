"""BAC (Basic Access Control) primitives for ICAO 9303 chips."""
import hashlib
from dataclasses import dataclass
from os import urandom

from Crypto.Cipher import DES, DES3


def _adjust_des_parity(key: bytes) -> bytes:
    """Return a DES key with odd parity in every byte."""
    return bytes(
        byte ^ 1 if bin(byte).count("1") % 2 == 0 else byte for byte in key
    )


def _iso9797_pad(data: bytes) -> bytes:
    """Apply ISO/IEC 9797-1 padding method 2."""
    padding_length = 8 - ((len(data) + 1) % 8)
    return data + b"\x80" + (b"\x00" * padding_length)


def _retail_mac(key: bytes, data: bytes) -> bytes:
    """Calculate ISO/IEC 9797-1 MAC algorithm 3."""
    padded_data = _iso9797_pad(data)
    first_key = key[:8]
    second_key = key[8:]
    last_block = DES.new(first_key, DES.MODE_CBC, iv=b"\x00" * 8).encrypt(padded_data)[-8:]
    return DES.new(first_key, DES.MODE_ECB).encrypt(
        DES.new(second_key, DES.MODE_ECB).decrypt(last_block)
    )


def _tdes_cbc_encrypt(key: bytes, data: bytes) -> bytes:
    return DES3.new(key + key[:8], DES3.MODE_CBC, iv=b"\x00" * 8).encrypt(data)


def _tdes_cbc_decrypt(key: bytes, data: bytes) -> bytes:
    return DES3.new(key + key[:8], DES3.MODE_CBC, iv=b"\x00" * 8).decrypt(data)


@dataclass(frozen=True, slots=True)
class BACSession:
    """Session keys and send sequence counter negotiated through BAC."""

    encryption_key: bytes
    mac_key: bytes
    send_sequence_counter: bytes


class BACKey:
    """Derives BAC key material from RUN + birth date + expiry date."""

    def __init__(
        self, run: str, fecha_nacimiento: str, fecha_vencimiento: str
    ) -> None:
        """
        Initialize BAC key derivation.

        Args:
            run: Chilean RUN (identity number), e.g., "12345678"
            fecha_nacimiento: Birth date in format "DDMMYY"
            fecha_vencimiento: Document expiry date in format "DDMMYY"
        """
        self.run = run.replace("-", "").replace(".", "").strip().upper()
        self.fecha_nacimiento = fecha_nacimiento
        self.fecha_vencimiento = fecha_vencimiento

    @staticmethod
    def _mrz_checksum(data: str) -> str:
        """
        Calculate ICAO 9303 checksum digit for MRZ data.

        Weights: 7, 3, 1 repeating.
        """
        weights = [7, 3, 1]
        total = 0
        for i, char in enumerate(data):
            if char == "<":
                digit = 0
            elif char.isdigit():
                digit = int(char)
            else:
                digit = ord(char) - ord("A") + 10
            total += digit * weights[i % 3]
        return str(total % 10)

    def _format_mrz_data(self) -> str:
        """
        Format MRZ-like data from RUN and dates.

        Format: document number + check digit + DOB (YYMMDD) + check digit +
        expiry date (YYMMDD) + check digit.
        """
        document_number = self.run[:9].ljust(9, "<")
        birth_date = self._to_mrz_date(self.fecha_nacimiento)
        expiry_date = self._to_mrz_date(self.fecha_vencimiento)
        return (
            f"{document_number}{self._mrz_checksum(document_number)}"
            f"{birth_date}{self._mrz_checksum(birth_date)}"
            f"{expiry_date}{self._mrz_checksum(expiry_date)}"
        )

    @staticmethod
    def _to_mrz_date(date: str) -> str:
        """Convert a DDMMYY UI value to the ICAO YYMMDD representation."""
        if len(date) != 6 or not date.isdigit():
            raise ValueError("Las fechas BAC deben tener el formato DDMMYY.")
        return f"{date[4:6]}{date[2:4]}{date[0:2]}"

    @staticmethod
    def _derive_des_key(seed: bytes, counter: int) -> bytes:
        material = hashlib.sha1(seed + counter.to_bytes(4, "big")).digest()[:16]
        return _adjust_des_parity(material)

    def derive_key_material(self) -> tuple[bytes, bytes]:
        """
        Derive encryption key and MAC key from BAC data.

        Returns:
            (encryption_key, mac_key) as 16-byte values each.
        """
        mrz_data = self._format_mrz_data()

        key_seed = hashlib.sha1(mrz_data.encode("ascii")).digest()[:16]
        return self._derive_des_key(key_seed, 1), self._derive_des_key(key_seed, 2)

    def build_external_authentication(
        self, rnd_icc: bytes, rnd_ifd: bytes | None = None, key_ifd: bytes | None = None
    ) -> tuple[bytes, bytes, bytes]:
        """Build the payload for an ISO 7816 EXTERNAL AUTHENTICATE command."""
        if len(rnd_icc) != 8:
            raise ValueError("GET CHALLENGE debe devolver 8 bytes.")
        rnd_ifd = rnd_ifd or urandom(8)
        key_ifd = key_ifd or urandom(16)
        if len(rnd_ifd) != 8 or len(key_ifd) != 16:
            raise ValueError("Los valores aleatorios BAC tienen un largo inválido.")

        encryption_key, mac_key = self.derive_key_material()
        encrypted = _tdes_cbc_encrypt(encryption_key, rnd_ifd + rnd_icc + key_ifd)
        return encrypted + _retail_mac(mac_key, encrypted), rnd_ifd, key_ifd

    def derive_session(
        self, response: bytes, rnd_icc: bytes, rnd_ifd: bytes, key_ifd: bytes
    ) -> BACSession:
        """Verify the card response and derive BAC secure-messaging keys."""
        if len(response) != 40:
            raise ValueError("La respuesta BAC de la tarjeta tiene un largo inválido.")

        encryption_key, mac_key = self.derive_key_material()
        encrypted, received_mac = response[:32], response[32:]
        if _retail_mac(mac_key, encrypted) != received_mac:
            raise ValueError("La MAC de respuesta BAC no coincide.")

        card_data = _tdes_cbc_decrypt(encryption_key, encrypted)
        if card_data[:8] != rnd_icc or card_data[8:16] != rnd_ifd:
            raise ValueError("Los desafíos BAC de la tarjeta no coinciden.")

        key_icc = card_data[16:]
        key_seed = bytes(ifd_byte ^ icc_byte for ifd_byte, icc_byte in zip(key_ifd, key_icc))
        return BACSession(
            encryption_key=self._derive_des_key(key_seed, 1),
            mac_key=self._derive_des_key(key_seed, 2),
            send_sequence_counter=rnd_icc[-4:] + rnd_ifd[-4:],
        )


__all__ = ["BACKey", "BACSession"]

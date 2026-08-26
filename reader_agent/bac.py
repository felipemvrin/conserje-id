"""BAC (Basic Access Control) implementation for ICAO 9303 chips."""
import hashlib

from Crypto.Cipher import DES3


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
        self.run = run.replace("-", "").replace(".", "").strip()
        self.fecha_nacimiento = fecha_nacimiento
        self.fecha_vencimiento = fecha_vencimiento

    def _mrz_checksum(self, data: str) -> str:
        """
        Calculate ICAO 9303 checksum digit for MRZ data.

        Weights: 7, 3, 1 repeating.
        """
        weights = [7, 3, 1]
        total = 0
        for i, char in enumerate(data):
            if char.isdigit():
                digit = int(char)
            else:
                digit = ord(char) - ord("A") + 10
            total += digit * weights[i % 3]
        return str(total % 10)

    def _format_mrz_data(self) -> str:
        """
        Format MRZ-like data from RUN and dates.

        Format: RUN (without checks) + DOB + DOE
        Example: "123456781990020120300101"
        """
        # Normalize RUN to 8 digits
        run_digits = self.run[:8] if len(self.run) >= 8 else self.run.ljust(8, "0")

        # Build MRZ string
        mrz = f"{run_digits}{self.fecha_nacimiento}{self.fecha_vencimiento}"

        # Append checksum
        checksum = self._mrz_checksum(mrz)
        return mrz + checksum

    def derive_key_material(self) -> tuple[bytes, bytes]:
        """
        Derive encryption key and MAC key from BAC data.

        Returns:
            (encryption_key, mac_key) as 16-byte values each.
        """
        mrz_data = self._format_mrz_data()

        # SHA-1 hash of MRZ data for key derivation
        sha1_hash = hashlib.sha1(mrz_data.encode()).digest()

        # Encryption key: first 16 bytes
        encryption_key = sha1_hash[:16]

        # MAC key: SHA-1(MRZ + 0x01), first 16 bytes
        mac_hash = hashlib.sha1((mrz_data + "01").encode()).digest()
        mac_key = mac_hash[:16]

        return encryption_key, mac_key

    def establish_bac_session(
        self, reader_response: bytes
    ) -> tuple[bytes, bytes] | None:
        """
        Establish BAC session with chip using derived keys.

        Args:
            reader_response: Challenge bytes from reader (8 bytes typically)

        Returns:
            (session_encryption_key, session_mac_key) or None if BAC fails
        """
        try:
            enc_key, mac_key = self.derive_key_material()

            # Encrypt reader challenge with derived key (simplified)
            cipher = DES3.new(enc_key + enc_key[:8], DES3.MODE_CBC, iv=b"\x00" * 8)
            encrypted_challenge = cipher.encrypt(reader_response)

            # Derive session keys (simplified)
            session_enc = hashlib.sha256(encrypted_challenge + b"\x00").digest()[:16]
            session_mac = hashlib.sha256(encrypted_challenge + b"\x01").digest()[:16]

            return session_enc, session_mac
        except Exception as e:
            print(f"[BAC] Error establishing session: {e}")
            return None

"""Chip reader using pyscard and PC/SC."""
import logging
from dataclasses import dataclass

from reader_agent.bac import (
    BACKey,
    BACSession,
    _iso9797_pad,
    _retail_mac,
    _tdes_cbc_decrypt,
    _tdes_cbc_encrypt,
)

try:
    from smartcard.Exceptions import CardConnectionException, SmartcardException
    from smartcard.System import readers
except ModuleNotFoundError as import_error:
    CardConnectionException = SmartcardException = Exception
    readers = None
    _SMARTCARD_IMPORT_ERROR = import_error
else:
    _SMARTCARD_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class CardProtocolError(Exception):
    """The card returned an unexpected ISO 7816 response."""


class BACAuthenticationError(CardProtocolError):
    """BAC authentication could not be completed."""


class PACEAuthenticationRequired(CardProtocolError):
    """The document advertises PACE instead of BAC."""


@dataclass(slots=True)
class ChipData:
    """Raw data extracted from chip."""

    run: str
    nombre_completo: str
    fecha_nacimiento: str
    foto_bytes: bytes | None = None


class ACR122UReader:
    """Interface for ACS ACR122U NFC reader via PC/SC."""

    def __init__(self) -> None:
        """Initialize reader interface."""
        self.connection = None
        self.reader = None
        self.bac_session: BACSession | None = None

    def detect_reader(self) -> bool:
        """
        Detect if ACR122U (or any compatible NFC reader) is connected.

        Returns:
            True if reader found, False otherwise
        """
        if _SMARTCARD_IMPORT_ERROR is not None or readers is None:
            logger.warning("pyscard is not installed; NFC reader support is unavailable.")
            return False

        try:
            available_readers = readers()
            if not available_readers:
                logger.warning("No PC/SC readers detected.")
                return False

            # Look for ACR122U or any compatible reader
            for reader in available_readers:
                reader_name = str(reader)
                logger.info(f"Found reader: {reader_name}")
                if "ACR122" in reader_name or "nfc" in reader_name.lower():
                    self.reader = reader
                    logger.info(f"ACR122U or NFC reader detected: {reader_name}")
                    return True

            # If no ACR122U found, use first available reader (for testing)
            self.reader = available_readers[0]
            logger.info(f"Using fallback reader: {self.reader}")
            return True

        except SmartcardException as e:
            logger.error(f"Error detecting reader: {e}")
            return False

    def connect(self) -> bool:
        """
        Establish connection to detected reader.

        Returns:
            True if connected, False otherwise
        """
        if not self.reader:
            logger.error("No reader detected. Call detect_reader() first.")
            return False

        if _SMARTCARD_IMPORT_ERROR is not None:
            logger.error("Cannot connect to card because pyscard is not installed.")
            return False

        try:
            self.connection = self.reader.createConnection()
            self.connection.connect()
            logger.info("Connected to card.")
            return True

        except CardConnectionException as e:
            logger.error(f"Card connection error: {e}")
            return False
        except SmartcardException as e:
            logger.error(f"Error connecting to reader: {e}")
            return False

    def read_file(self, file_id: bytes) -> bytes | None:
        """
        Read data from chip file using ISO 7816 commands.

        Args:
            file_id: 2-byte file identifier

        Returns:
            File contents or None if error
        """
        if not self.connection:
            logger.error("Not connected to card.")
            return None

        try:
            select_apdu = [0x00, 0xA4, 0x00, 0x00, 0x02] + list(file_id)
            response, sw1, sw2 = self.connection.transmit(select_apdu)

            if sw1 != 0x90:
                logger.warning(f"SELECT FILE failed: {sw1:02x} {sw2:02x}")
                return None

            read_apdu = [0x00, 0xB0, 0x00, 0x00, 0x00]
            response, sw1, sw2 = self.connection.transmit(read_apdu)

            if sw1 != 0x90:
                logger.warning(f"READ BINARY failed: {sw1:02x} {sw2:02x}")
                return None

            return bytes(response)

        except SmartcardException as e:
            logger.error(f"Error reading file: {e}")
            return None

    def select_emrtd_application(self) -> None:
        """Select the ICAO eMRTD application on the card."""
        self._transmit([0x00, 0xA4, 0x04, 0x0C, 0x07, 0xA0, 0x00, 0x00, 0x02, 0x47, 0x10, 0x01])

    def establish_bac(self, bac_key: BACKey) -> None:
        """Authenticate with the chip and enable BAC secure messaging."""
        if self._requires_pace():
            raise PACEAuthenticationRequired(
                "La cédula requiere PACE; BAC no puede acceder a sus datos."
            )
        self.select_emrtd_application()
        rnd_icc = self._transmit([0x00, 0x84, 0x00, 0x00, 0x08])
        if len(rnd_icc) != 8:
            raise BACAuthenticationError("GET CHALLENGE no devolvió 8 bytes.")

        authentication_data, rnd_ifd, key_ifd = bac_key.build_external_authentication(rnd_icc)
        try:
            response = self._transmit(
                [0x00, 0x82, 0x00, 0x00, 0x28] + list(authentication_data) + [0x28]
            )
            self.bac_session = bac_key.derive_session(response, rnd_icc, rnd_ifd, key_ifd)
        except (CardProtocolError, ValueError) as error:
            raise BACAuthenticationError("La autenticación BAC fue rechazada por la tarjeta.") from error

    def _requires_pace(self) -> bool:
        """Return whether EF.CardAccess advertises a PACE security protocol."""
        if not self.connection:
            raise CardProtocolError("No hay conexión con la tarjeta.")

        _, sw1, sw2 = self.connection.transmit([0x00, 0xA4, 0x00, 0x0C, 0x02, 0x3F, 0x00])
        if (sw1, sw2) != (0x90, 0x00):
            return False
        _, sw1, sw2 = self.connection.transmit([0x00, 0xA4, 0x02, 0x0C, 0x02, 0x01, 0x1C])
        if (sw1, sw2) == (0x6A, 0x82):
            return False
        if (sw1, sw2) != (0x90, 0x00):
            return False
        response, sw1, sw2 = self.connection.transmit([0x00, 0xB0, 0x00, 0x00, 0x00])
        if (sw1, sw2) != (0x90, 0x00):
            return False

        return b"\x06\x0A\x04\x00\x7F\x00\x07\x02\x02\x04" in bytes(response)

    def read_protected_file(self, file_id: bytes) -> bytes:
        """Select and read an ICAO elementary file through secure messaging."""
        if len(file_id) != 2:
            raise ValueError("El identificador de archivo debe tener dos bytes.")
        self._transmit_protected(0xA4, 0x02, 0x0C, data=file_id, expected_length=256)

        first_chunk = self._transmit_protected(0xB0, 0x00, 0x00, expected_length=224)
        total_length = self._ber_total_length(first_chunk)
        contents = bytearray(first_chunk)
        while len(contents) < total_length:
            offset = len(contents)
            chunk_length = min(224, total_length - offset)
            contents.extend(
                self._transmit_protected(
                    0xB0,
                    (offset >> 8) & 0xFF,
                    offset & 0xFF,
                    expected_length=chunk_length,
                )
            )
        return bytes(contents[:total_length])

    def _transmit(self, apdu: list[int]) -> bytes:
        """Transmit a plain APDU and require a successful status word."""
        if not self.connection:
            raise CardProtocolError("No hay conexión con la tarjeta.")
        response, sw1, sw2 = self.connection.transmit(apdu)
        if (sw1, sw2) != (0x90, 0x00):
            raise CardProtocolError(f"La tarjeta rechazó la APDU: {sw1:02X}{sw2:02X}.")
        return bytes(response)

    @staticmethod
    def _encode_tlv(tag: int, value: bytes) -> bytes:
        length = len(value)
        if length < 0x80:
            encoded_length = bytes([length])
        elif length <= 0xFF:
            encoded_length = b"\x81" + bytes([length])
        else:
            encoded_length = b"\x82" + length.to_bytes(2, "big")
        return bytes([tag]) + encoded_length + value

    @staticmethod
    def _decode_tlvs(data: bytes) -> list[tuple[int, bytes, bytes]]:
        result: list[tuple[int, bytes, bytes]] = []
        offset = 0
        while offset < len(data):
            start = offset
            tag = data[offset]
            offset += 1
            if offset >= len(data):
                raise CardProtocolError("TLV protegido truncado.")
            length = data[offset]
            offset += 1
            if length & 0x80:
                length_size = length & 0x7F
                if not length_size or offset + length_size > len(data):
                    raise CardProtocolError("Largo TLV protegido inválido.")
                length = int.from_bytes(data[offset : offset + length_size], "big")
                offset += length_size
            if offset + length > len(data):
                raise CardProtocolError("Valor TLV protegido truncado.")
            value = data[offset : offset + length]
            offset += length
            result.append((tag, value, data[start:offset]))
        return result

    @staticmethod
    def _unpad_iso9797(data: bytes) -> bytes:
        marker = data.rfind(b"\x80")
        if marker < 0 or any(data[marker + 1 :]):
            raise CardProtocolError("Padding ISO 9797 inválido en la respuesta.")
        return data[:marker]

    @staticmethod
    def _ber_total_length(data: bytes) -> int:
        if len(data) < 2 or data[0] != 0x61:
            raise CardProtocolError("DG1 no tiene la estructura BER esperada.")
        length = data[1]
        if not length & 0x80:
            return 2 + length
        length_size = length & 0x7F
        if not length_size or len(data) < 2 + length_size:
            raise CardProtocolError("Largo BER de DG1 inválido.")
        return 2 + length_size + int.from_bytes(data[2 : 2 + length_size], "big")

    def _increment_ssc(self) -> bytes:
        if not self.bac_session:
            raise CardProtocolError("No hay una sesión BAC activa.")
        counter = (int.from_bytes(self.bac_session.send_sequence_counter, "big") + 1).to_bytes(8, "big")
        self.bac_session = BACSession(
            encryption_key=self.bac_session.encryption_key,
            mac_key=self.bac_session.mac_key,
            send_sequence_counter=counter,
        )
        return counter

    def _transmit_protected(
        self,
        instruction: int,
        parameter_1: int,
        parameter_2: int,
        data: bytes = b"",
        expected_length: int | None = None,
    ) -> bytes:
        if not self.bac_session:
            raise CardProtocolError("No hay una sesión BAC activa.")

        command_data = b""
        if data:
            encrypted = _tdes_cbc_encrypt(
                self.bac_session.encryption_key, _iso9797_pad(data)
            )
            command_data += self._encode_tlv(0x87, b"\x01" + encrypted)
        if expected_length is not None:
            length = 0 if expected_length == 256 else expected_length
            command_data += self._encode_tlv(0x97, bytes([length]))

        protected_header = bytes([0x0C, instruction, parameter_1, parameter_2])
        command_mac = _retail_mac(
            self.bac_session.mac_key,
            self._increment_ssc() + protected_header + command_data,
        )
        body = command_data + self._encode_tlv(0x8E, command_mac)
        response = self._transmit(protected_header + bytes([len(body)]) + body + b"\x00")

        tlvs = self._decode_tlvs(response)
        values = {tag: value for tag, value, _ in tlvs}
        raw_without_mac = b"".join(raw for tag, _, raw in tlvs if tag != 0x8E)
        response_mac = values.get(0x8E)
        status = values.get(0x99)
        if not response_mac or not status or len(status) != 2:
            raise CardProtocolError("La respuesta protegida no contiene MAC o estado.")
        expected_mac = _retail_mac(self.bac_session.mac_key, self._increment_ssc() + raw_without_mac)
        if response_mac != expected_mac:
            raise CardProtocolError("La MAC de la respuesta protegida no coincide.")
        if status != b"\x90\x00":
            raise CardProtocolError(f"La tarjeta rechazó la APDU protegida: {status.hex().upper()}.")

        encrypted_response = values.get(0x87)
        if not encrypted_response:
            return b""
        if encrypted_response[0] != 0x01:
            raise CardProtocolError("El objeto de datos protegidos no usa el marcador esperado.")
        return self._unpad_iso9797(
            _tdes_cbc_decrypt(self.bac_session.encryption_key, encrypted_response[1:])
        )

    def disconnect(self) -> None:
        """Close connection to reader."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info("Disconnected from card.")
            except SmartcardException as e:
                logger.warning(f"Error disconnecting: {e}")
            finally:
                self.connection = None
                self.bac_session = None

    def __del__(self) -> None:
        """Ensure connection is closed on cleanup."""
        self.disconnect()

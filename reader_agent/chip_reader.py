"""Chip reader using pyscard and PC/SC."""
import logging
from dataclasses import dataclass

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
            # SELECT FILE command
            select_apdu = [0x00, 0xA4, 0x00, 0x00, 0x02] + list(file_id)
            response, sw1, sw2 = self.connection.transmit(select_apdu)

            if sw1 != 0x90:
                logger.warning(f"SELECT FILE failed: {sw1:02x} {sw2:02x}")
                return None

            # READ BINARY command (simplified: read first 256 bytes)
            read_apdu = [0x00, 0xB0, 0x00, 0x00, 0x00]
            response, sw1, sw2 = self.connection.transmit(read_apdu)

            if sw1 != 0x90:
                logger.warning(f"READ BINARY failed: {sw1:02x} {sw2:02x}")
                return None

            return bytes(response)

        except SmartcardException as e:
            logger.error(f"Error reading file: {e}")
            return None

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

    def __del__(self) -> None:
        """Ensure connection is closed on cleanup."""
        self.disconnect()

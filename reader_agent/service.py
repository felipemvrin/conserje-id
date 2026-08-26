"""Main reader service orchestrating chip reading with BAC."""
import logging
from dataclasses import dataclass

from reader_agent.bac import BACKey
from reader_agent.chip_reader import ACR122UReader, ChipData

logger = logging.getLogger(__name__)


class ReaderException(Exception):
    """Base exception for reader errors."""

    pass


class ReaderNotDetectedException(ReaderException):
    """Reader hardware not found."""

    pass


class CardNotDetectedException(ReaderException):
    """No card in reader."""

    pass


class BACFailedException(ReaderException):
    """BAC authentication failed."""

    pass


class InvalidCardException(ReaderException):
    """Card is not compatible or format is invalid."""

    pass


@dataclass(slots=True)
class DatosCedula:
    """Typed object with extracted chip data."""

    run: str
    nombre_completo: str
    fecha_nacimiento: str
    foto_bytes: bytes | None = None


def leer_cedula(
    run: str, fecha_nacimiento: str, fecha_vencimiento: str
) -> DatosCedula:
    """
    Read Chilean identity card (cédula) chip using NFC reader.

    Performs BAC handshake to unlock chip, then extracts personal data.

    Args:
        run: Chilean RUN (identity number), e.g., "12345678" or "12.345.678"
        fecha_nacimiento: Birth date in format "DDMMYY"
        fecha_vencimiento: Document expiry date in format "DDMMYY"

    Returns:
        DatosCedula object with extracted chip data

    Raises:
        ReaderNotDetectedException: If ACR122U reader is not connected
        CardNotDetectedException: If no card is in the reader
        BACFailedException: If BAC handshake fails
        InvalidCardException: If card is not a valid ICAO 9303 chip
    """
    logger.info(
        f"Iniciando lectura de cedula: RUN={run}, "
        f"DOB={fecha_nacimiento}, EXP={fecha_vencimiento}"
    )

    reader = ACR122UReader()

    # Step 1: Detect reader
    if not reader.detect_reader():
        logger.error("No NFC reader detected.")
        raise ReaderNotDetectedException(
            "Lector ACR122U no detectado. Verifique conexión USB y drivers PC/SC."
        )

    # Step 2: Connect to card
    if not reader.connect():
        logger.error("Card not detected in reader.")
        raise CardNotDetectedException(
            "No hay tarjeta en el lector. Acerque la cédula."
        )

    try:
        # Step 3: Derive BAC key
        bac_key = BACKey(run, fecha_nacimiento, fecha_vencimiento)
        logger.info("BAC key derived.")

        # Step 4: Attempt BAC handshake (simplified)
        # In a real implementation, this would include full APDU exchange
        session_keys = bac_key.establish_bac_session(b"\x00" * 8)
        if not session_keys:
            logger.error("BAC handshake failed.")
            raise BACFailedException(
                "Error de autenticación BAC. Verifique datos de cédula."
            )

        logger.info("BAC session established.")

        # Step 5: Read chip data (DG1, DG2, etc.)
        # File IDs for ICAO 9303:
        # DG1: 0x0101 (personal data)
        # DG2: 0x0102 (photo/biometric)
        chip_data = _read_chip_data(reader, run, fecha_nacimiento)

        logger.info(f"Lectura exitosa: {chip_data.nombre_completo}")

        return DatosCedula(
            run=chip_data.run,
            nombre_completo=chip_data.nombre_completo,
            fecha_nacimiento=chip_data.fecha_nacimiento,
            foto_bytes=chip_data.foto_bytes,
        )

    except (ReaderException, Exception) as e:
        logger.error(f"Error during chip reading: {e}")
        raise
    finally:
        reader.disconnect()


def _read_chip_data(
    reader: ACR122UReader, run: str, fecha_nacimiento: str
) -> ChipData:
    """
    Extract data from chip files.

    This is a simplified mock implementation.
    In production, this would parse binary chip files (DG1, DG2, etc.)
    according to ICAO 9303 format.

    Args:
        reader: Connected ACR122UReader instance
        run: RUN from card
        fecha_nacimiento: Birth date

    Returns:
        ChipData object with extracted information
    """
    # Read DG1 (personal data)
    dg1_data = reader.read_file(b"\x01\x01")

    if not dg1_data:
        raise InvalidCardException(
            "No se pudo leer datos de la tarjeta. "
            "Verifique que sea una cédula de identidad válida."
        )

    # Simplified: In real implementation, parse binary DG1 format
    # For now, return mock data that could be enriched from DG1
    nombre_completo = "USUARIO DE PRUEBA"  # Would parse from chip

    # Read DG2 (photo) if available
    foto_bytes = reader.read_file(b"\x01\x02")

    logger.debug(f"DG1 size: {len(dg1_data) if dg1_data else 0} bytes")
    logger.debug(f"DG2 (photo) available: {foto_bytes is not None}")

    return ChipData(
        run=run,
        nombre_completo=nombre_completo,
        fecha_nacimiento=fecha_nacimiento,
        foto_bytes=foto_bytes,
    )

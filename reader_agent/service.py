"""Main reader service orchestrating chip reading with BAC."""
import logging
from dataclasses import dataclass

from reader_agent.bac import BACKey
from reader_agent.chip_reader import (
    ACR122UReader,
    BACAuthenticationError,
    CardProtocolError,
    ChipData,
    PACEAuthenticationRequired,
)

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


class PACERequiredException(ReaderException):
    """The document requires PACE authentication, which is not available."""

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


def _mask_run(run: str) -> str:
    """Mask a RUN before sending it to logs."""
    normalized_run = run.replace("-", "").replace(".", "").strip()
    if len(normalized_run) <= 4:
        return "*" * len(normalized_run)
    return f"{'*' * (len(normalized_run) - 4)}{normalized_run[-4:]}"


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
    logger.info("Iniciando lectura de cedula para RUN=%s", _mask_run(run))

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
        # Step 3: Authenticate with the document using BAC.
        bac_key = BACKey(run, fecha_nacimiento, fecha_vencimiento)
        try:
            reader.establish_bac(bac_key)
        except PACEAuthenticationRequired as error:
            raise PACERequiredException(
                "Esta cédula requiere autenticación PACE con su CAN."
            ) from error
        except BACAuthenticationError as error:
            raise BACFailedException(
                "Error de autenticación BAC. Verifique los datos MRZ de la cédula."
            ) from error

        logger.info("BAC session established.")

        # Step 5: Read chip data (DG1, DG2, etc.)
        # File IDs for ICAO 9303:
        # DG1: 0x0101 (personal data)
        # DG2: 0x0102 (photo/biometric)
        chip_data = _read_chip_data(reader, run, fecha_nacimiento)

        logger.info("Lectura exitosa para RUN=%s", _mask_run(chip_data.run))

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
    try:
        dg1_data = reader.read_protected_file(b"\x01\x01")
    except CardProtocolError as error:
        raise InvalidCardException(
            "No se pudo leer datos de la tarjeta. "
            "Verifique que sea una cédula de identidad válida."
        ) from error

    nombre_completo = _nombre_desde_dg1(dg1_data)

    logger.debug(f"DG1 size: {len(dg1_data) if dg1_data else 0} bytes")

    return ChipData(
        run=run,
        nombre_completo=nombre_completo,
        fecha_nacimiento=fecha_nacimiento,
        foto_bytes=None,
    )


def _nombre_desde_dg1(dg1_data: bytes) -> str:
    """Extract the name field from the MRZ held in ICAO DG1."""
    marker = b"\x5F\x1F"
    offset = dg1_data.find(marker)
    if offset < 0 or offset + 3 > len(dg1_data):
        raise InvalidCardException("DG1 no contiene una zona MRZ válida.")

    length = dg1_data[offset + 2]
    value_start = offset + 3
    if length & 0x80:
        length_size = length & 0x7F
        if not length_size or value_start + length_size > len(dg1_data):
            raise InvalidCardException("El largo MRZ de DG1 es inválido.")
        length = int.from_bytes(dg1_data[value_start : value_start + length_size], "big")
        value_start += length_size
    mrz = dg1_data[value_start : value_start + length].decode("ascii", errors="ignore")

    for line in reversed(mrz.splitlines()):
        if "<<" in line:
            apellido, _, nombres = line.partition("<<")
            nombre = " ".join(
                part for part in (apellido + " " + nombres).replace("<", " ").split() if part
            )
            if nombre:
                return nombre
    raise InvalidCardException("No se pudo extraer el nombre desde DG1.")

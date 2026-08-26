"""Example usage of reader_agent.service.leer_cedula()"""
import logging

from reader_agent.service import (
    BACFailedException,
    CardNotDetectedException,
    InvalidCardException,
    ReaderNotDetectedException,
    leer_cedula,
)

# Configure logging to see debug output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Example: Read Chilean identity card."""
    # These would come from user input in the real app
    run = "12345678"
    fecha_nacimiento = "010190"  # DDMMYY format
    fecha_vencimiento = "010230"  # DDMMYY format

    logger.info(f"Attempting to read card: {run}")

    try:
        # Call the high-level function
        datos = leer_cedula(run, fecha_nacimiento, fecha_vencimiento)

        # Use extracted data
        logger.info("Success! Extracted data:")
        logger.info(f"  RUN: {datos.run}")
        logger.info(f"  Name: {datos.nombre_completo}")
        logger.info(f"  DOB: {datos.fecha_nacimiento}")
        logger.info(f"  Photo: {datos.foto_bytes is not None}")

        # In the API, this would be stored as a Visita record
        return datos

    except ReaderNotDetectedException as e:
        logger.error(f"Reader error: {e}")
        logger.info("Asegúrese de que:")
        logger.info("  1. El lector ACR122U esté conectado por USB")
        logger.info("  2. Los drivers PC/SC estén instalados")
        logger.info("  3. No haya otras aplicaciones usando el lector")

    except CardNotDetectedException as e:
        logger.error(f"Card error: {e}")
        logger.info("Acerque la cédula de identidad al lector NFC.")

    except BACFailedException as e:
        logger.error(f"BAC error: {e}")
        logger.info("Verifique que:")
        logger.info("  1. Los datos de cédula sean correctos")
        logger.info("  2. La cédula sea válida (no vencida)")
        logger.info("  3. El chip sea compatible (ICAO 9303)")

    except InvalidCardException as e:
        logger.error(f"Invalid card: {e}")
        logger.info("Esta tarjeta no es una cédula de identidad válida.")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()

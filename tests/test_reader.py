"""Tests for reader_agent module."""
import pytest

from reader_agent import chip_reader
from reader_agent.bac import BACKey
from reader_agent.chip_reader import ACR122UReader
from reader_agent.service import (
    BACFailedException,
    CardNotDetectedException,
    DatosCedula,
    ReaderNotDetectedException,
    leer_cedula,
)


class TestBACKey:
    """Test BAC key derivation."""

    def test_mrz_checksum(self) -> None:
        """Test ICAO 9303 checksum calculation."""
        bac = BACKey("12345678", "010190", "010230")
        # Example MRZ string
        mrz = "123456781990020120300101"
        checksum = bac._mrz_checksum(mrz)
        assert len(checksum) == 1
        assert checksum.isdigit()

    def test_format_mrz_data(self) -> None:
        """Test MRZ data formatting."""
        bac = BACKey("12345678", "010190", "010230")
        mrz = bac._format_mrz_data()
        assert mrz == "123456780101900102309"
        assert len(mrz) == 21

    def test_derive_key_material(self) -> None:
        """Test encryption and MAC key derivation."""
        bac = BACKey("12345678", "010190", "010230")
        enc_key, mac_key = bac.derive_key_material()
        assert len(enc_key) == 16
        assert len(mac_key) == 16
        assert enc_key != mac_key

    def test_run_normalization(self) -> None:
        """Test RUN normalization (removing dots and dashes)."""
        bac1 = BACKey("12.345.678", "010190", "010230")
        bac2 = BACKey("12-345-678", "010190", "010230")
        bac3 = BACKey("12345678", "010190", "010230")
        # All should produce same key material
        assert bac1.derive_key_material() == bac2.derive_key_material()
        assert bac2.derive_key_material() == bac3.derive_key_material()


class TestReaderService:
    """Test high-level reader service (mocked hardware)."""

    def test_detect_reader_without_pyscard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reader detection should fail cleanly when pyscard is unavailable."""
        monkeypatch.setattr(
            chip_reader,
            "_SMARTCARD_IMPORT_ERROR",
            ModuleNotFoundError("smartcard"),
        )
        monkeypatch.setattr(chip_reader, "readers", None)

        assert ACR122UReader().detect_reader() is False

    def test_connect_uses_detected_reader(self) -> None:
        """Connection should use the reader selected during detection."""
        original_import_error = chip_reader._SMARTCARD_IMPORT_ERROR

        class FakeConnection:
            def connect(self) -> None:
                return None

            def disconnect(self) -> None:
                return None

        class FakeReader:
            def createConnection(self) -> FakeConnection:
                return FakeConnection()

        reader = ACR122UReader()
        reader.reader = FakeReader()
        chip_reader._SMARTCARD_IMPORT_ERROR = None

        try:
            assert reader.connect() is True
            assert reader.connection is not None
        finally:
            chip_reader._SMARTCARD_IMPORT_ERROR = original_import_error

    @pytest.mark.skip(reason="Requires physical ACR122U reader")
    def test_leer_cedula_success(self) -> None:
        """Test successful chip read (requires hardware)."""
        resultado = leer_cedula("12345678", "010190", "010230")
        assert isinstance(resultado, DatosCedula)
        assert resultado.run == "12345678"
        assert resultado.nombre_completo
        assert resultado.fecha_nacimiento == "010190"

    @pytest.mark.skip(reason="Requires physical ACR122U reader")
    def test_leer_cedula_reader_not_detected(self) -> None:
        """Test error when reader is not connected."""
        with pytest.raises(ReaderNotDetectedException):
            leer_cedula("12345678", "010190", "010230")

    @pytest.mark.skip(reason="Requires physical ACR122U reader")
    def test_leer_cedula_card_not_detected(self) -> None:
        """Test error when card is not in reader."""
        with pytest.raises(CardNotDetectedException):
            leer_cedula("12345678", "010190", "010230")

    @pytest.mark.skip(reason="Requires physical ACR122U reader")
    def test_leer_cedula_bac_failed(self) -> None:
        """Test error when BAC handshake fails."""
        # Invalid dates should cause BAC to fail
        with pytest.raises(BACFailedException):
            leer_cedula("12345678", "010190", "010100")

    def test_datos_cedula_dataclass(self) -> None:
        """Test DatosCedula dataclass structure."""
        datos = DatosCedula(
            run="12345678",
            nombre_completo="Juan Pérez",
            fecha_nacimiento="010190",
            foto_bytes=None,
        )
        assert datos.run == "12345678"
        assert datos.nombre_completo == "Juan Pérez"
        assert datos.foto_bytes is None

    def test_leer_cedula_masks_run_in_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Service logs should not include full RUN or birth/expiry dates."""
        reader = ACR122UReader()
        monkeypatch.setattr("reader_agent.service.ACR122UReader", lambda: reader)
        monkeypatch.setattr(reader, "detect_reader", lambda: False)

        with caplog.at_level("INFO"):
            with pytest.raises(ReaderNotDetectedException):
                leer_cedula("12.345.678-5", "010190", "010230")

        messages = " ".join(record.getMessage() for record in caplog.records)
        assert "12.345.678-5" not in messages
        assert "123456785" not in messages
        assert "010190" not in messages
        assert "010230" not in messages
        assert "*****6785" in messages

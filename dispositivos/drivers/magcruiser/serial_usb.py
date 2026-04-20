# dispositivos/drivers/magcruiser/serial.py
import serial


class MagCruiserSerialDriver:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 3.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.conn = None

    def connect(self) -> None:
        self.conn = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def disconnect(self) -> None:
        if self.conn and self.conn.is_open:
            self.conn.close()

    def healthcheck(self) -> dict:
        return {
            "connected": bool(self.conn and self.conn.is_open),
            "port": self.port,
            "baudrate": self.baudrate,
        }

    def read_once(self) -> str:
        if not self.conn or not self.conn.is_open:
            raise RuntimeError("Dispositivo não está ligado.")
        raw = self.conn.readline()
        return raw.decode("utf-8", errors="ignore").strip()
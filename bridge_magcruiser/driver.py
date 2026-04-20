import serial


class MagCruiserDriver:
    def __init__(self, port, baudrate):
        self.conn = serial.Serial(port, baudrate, timeout=3)

    def read(self):
        raw = self.conn.readline()
        return raw.decode("utf-8", errors="ignore").strip()
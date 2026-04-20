class MagCruiserSimulatorDriver:
    def __init__(self):
        self.connected = False
        self.index = 0
        self.samples = [
            "DEPTH=10.00;INC=-45.10;AZI=180.20;MAG=44.20;TEMP=23.50",
            "DEPTH=20.00;INC=-46.00;AZI=181.30;MAG=44.50;TEMP=23.60",
            "DEPTH=30.00;INC=-47.15;AZI=182.10;MAG=44.70;TEMP=23.70",
        ]

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def healthcheck(self) -> dict:
        return {"connected": self.connected, "mode": "simulator"}

    def read_once(self) -> str:
        if not self.connected:
            raise RuntimeError("Simulador não está ligado.")
        value = self.samples[self.index % len(self.samples)]
        self.index += 1
        return value
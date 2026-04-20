# dispositivos/drivers/magcruiser/bluetooth.py
class MagCruiserBluetoothDriver:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address

    def connect(self):
        # implementar depois de confirmar se é BLE ou SPP
        raise NotImplementedError

    def disconnect(self):
        pass

    def read_once(self):
        raise NotImplementedError
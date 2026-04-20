def construir_driver(dispositivo):
    if dispositivo.tipo != "magcruiser":
        raise ValueError("Tipo de dispositivo não suportado.")

    if dispositivo.canal == "usb_serial":
        from dispositivos.drivers.magcruiser.serial_usb import MagCruiserSerialDriver

        return MagCruiserSerialDriver(
            port=dispositivo.porta,
            baudrate=dispositivo.baudrate,
        )

    if dispositivo.canal == "simulador":
        try:
            from dispositivos.drivers.magcruiser.simulador import MagCruiserSimulatorDriver
        except ModuleNotFoundError as exc:
            raise ValueError(
                "O driver simulador do MagCruiser ainda não está disponível."
            ) from exc

        return MagCruiserSimulatorDriver()

    if dispositivo.canal == "bluetooth":
        raise ValueError("Canal Bluetooth ainda não suportado.")

    if dispositivo.canal == "arquivo":
        raise ValueError("Canal por arquivo ainda não suportado.")

    raise ValueError("Canal de comunicação ainda não suportado.")

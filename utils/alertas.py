def analisar_furo(furo):
    alertas = []

    if len(furo.medicoes) < 2:
        return alertas

    ult = furo.medicoes[-1]
    prev = furo.medicoes[-2]

    # 🚨 Inclinação anormal
    if abs(ult["inclinacao"] - prev["inclinacao"]) > 5:
        alertas.append("⚠️ Variação brusca de inclinação")

    # 🚨 Azimute estranho
    if abs(ult["azimute"] - prev["azimute"]) > 10:
        alertas.append("⚠️ Desvio de direção")

    return alertas
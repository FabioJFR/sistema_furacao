from datetime import date, datetime, timedelta

def analisar_furo(furo):
    alertas = []

    if len(furo.medicoes) < 2:
        return alertas

    ult = furo.medicoes[-1]
    prev = furo.medicoes[-2]

    # 🚨 Inclinação anormal
    if abs(ult.inclinacao - prev.inclinacao) > 5:
        alertas.append("⚠️ Variação brusca de inclinação")

    # 🚨 Azimute estranho
    if abs(ult.azimute - prev.azimute) > 10:
        alertas.append("⚠️ Desvio de direção")

    return alertas



def analisar_empregado(empregado):
    """
    Retorna uma lista de alertas automáticos para um empregado.
    """
    alertas = []

    # Alerta contrato
    if empregado.data_fim_contrato:
        fim = datetime.fromisoformat(empregado.data_fim_contrato).date()
        dias_restantes = (fim - date.today()).days
        if dias_restantes < 0:
            alertas.append("Contrato expirado!")
        elif dias_restantes <= 30:
            alertas.append(f"Contrato termina em {dias_restantes} dias")
    else:
        alertas.append("Contrato sem data de término definida")

    # Horas extras elevadas
    if getattr(empregado, "horas_extra", 0) > 20:
        alertas.append(f"Horas extras elevadas: {empregado.horas_extra}h")

    # Salário baixo
    if getattr(empregado, "salario", 0) <= 0:
        alertas.append("Salário não definido ou zerado")

    return alertas
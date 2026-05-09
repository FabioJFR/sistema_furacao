from django import forms


class GeologiaScoreConfigForm(forms.Form):
    sem_logs = forms.IntegerField(min_value=0, max_value=100, required=True)
    conflito_intervalo = forms.IntegerField(min_value=0, max_value=100, required=True)
    pendente_validacao = forms.IntegerField(min_value=0, max_value=100, required=True)
    sem_anexo = forms.IntegerField(min_value=0, max_value=100, required=True)
    sem_log_24h = forms.IntegerField(min_value=0, max_value=100, required=True)
    sem_log_48h = forms.IntegerField(min_value=0, max_value=100, required=True)
    janela_atencao_horas = forms.IntegerField(min_value=1, max_value=240, required=True)
    janela_critico_horas = forms.IntegerField(min_value=1, max_value=240, required=True)

    def clean(self):
        cleaned = super().clean()
        atencao = cleaned.get("janela_atencao_horas")
        critico = cleaned.get("janela_critico_horas")
        if atencao and critico and critico <= atencao:
            self.add_error(
                "janela_critico_horas",
                "A janela crítica tem de ser maior do que a janela de atenção.",
            )
        return cleaned


class ComplianceScoreConfigForm(forms.Form):
    peso_vencidas = forms.IntegerField(min_value=0, max_value=100, required=True)
    peso_criticas = forms.IntegerField(min_value=0, max_value=100, required=True)
    peso_altas = forms.IntegerField(min_value=0, max_value=100, required=True)
    peso_vence_7d = forms.IntegerField(min_value=0, max_value=100, required=True)
    peso_abertas = forms.IntegerField(min_value=0, max_value=100, required=True)
    threshold_medio = forms.IntegerField(min_value=0, max_value=500, required=True)
    threshold_alto = forms.IntegerField(min_value=1, max_value=500, required=True)

    def clean(self):
        cleaned = super().clean()
        threshold_medio = cleaned.get("threshold_medio")
        threshold_alto = cleaned.get("threshold_alto")
        if threshold_medio is not None and threshold_alto is not None and threshold_alto <= threshold_medio:
            self.add_error(
                "threshold_alto",
                "O limiar de risco alto tem de ser maior do que o limiar de risco médio.",
            )
        return cleaned

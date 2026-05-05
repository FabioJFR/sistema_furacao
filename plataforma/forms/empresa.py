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

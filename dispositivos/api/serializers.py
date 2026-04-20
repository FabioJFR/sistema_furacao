from rest_framework import serializers

from dispositivos.models import Dispositivo, SessaoDispositivo, SurveyShot


class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = [
            "id",
            "empresa",
            "nome",
            "tipo",
            "canal",
            "identificador_fisico",
            "porta",
            "mac_address",
            "baudrate",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em"]


class SessaoDispositivoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessaoDispositivo
        fields = ["dispositivo", "furo"]


class SessaoDispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessaoDispositivo
        fields = [
            "id",
            "dispositivo",
            "empresa",
            "empregado",
            "furo",
            "status",
            "mensagem_erro",
            "iniciado_em",
            "terminado_em",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "empregado",
            "status",
            "mensagem_erro",
            "iniciado_em",
            "terminado_em",
        ]


class SurveyShotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyShot
        fields = [
            "id",
            "sessao",
            "furo",
            "empresa",
            "profundidade",
            "inclinacao",
            "azimute",
            "magnetismo",
            "temperatura",
            "valido",
            "origem",
            "criado_em",
        ]
        read_only_fields = ["id", "empresa", "criado_em"]
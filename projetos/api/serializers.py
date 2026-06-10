from rest_framework import serializers

from projetos.models import Furo, FuroVersao


class FuroSerializer(serializers.ModelSerializer):
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Furo
        fields = [
            "id",
            "empresa",
            "projeto",
            "projeto_nome",
            "nome",
            "tipo",
            "tipo_label",
            "estado",
            "estado_label",
            "profundidade_inicial",
            "profundidade_alvo_inicial",
            "profundidade_alvo_atual",
            "profundidade_atual",
            "profundidade_maxima_atingida",
            "inclinacao_planeada_inicial",
            "inclinacao_planeada_atual",
            "inclinacao_real_atual",
            "azimute_planeado_inicial",
            "azimute_planeado_atual",
            "azimute_real_atual",
            "magnetismo",
            "latitude",
            "longitude",
            "altitude",
            "localizacao",
            "local_sondagem",
            "metros_furados",
            "total_horas",
            "data",
        ]
        read_only_fields = ["id", "empresa", "data"]


class FuroVersaoSerializer(serializers.ModelSerializer):
    origem_label = serializers.CharField(source="get_origem_display", read_only=True)
    furo_nome = serializers.CharField(source="furo.nome", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    criado_por_username = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = FuroVersao
        fields = [
            "id",
            "empresa",
            "projeto",
            "projeto_nome",
            "furo",
            "furo_nome",
            "versao_numero",
            "origem",
            "origem_label",
            "hash_estado",
            "dados_snapshot",
            "criado_por",
            "criado_por_username",
            "observacoes",
            "criado_em",
        ]
        read_only_fields = fields

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dispositivos.api.serializers import (
    SessaoDispositivoCreateSerializer,
    SessaoDispositivoSerializer,
)
from dispositivos.selectors.dispositivos import (
    obter_empregado_autenticado,
    obter_sessao_empresa,
    obter_sessao_ligada_empresa,
)
from dispositivos.services.ingestao import guardar_leitura_dispositivo
from dispositivos.services.sessao import criar_sessao_dispositivo, ler_dispositivo_uma_vez


class CriarSessaoDispositivoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessaoDispositivoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empregado = obter_empregado_autenticado(request.user)
        dispositivo = serializer.validated_data["dispositivo"]
        furo = serializer.validated_data.get("furo")

        try:
            sessao = criar_sessao_dispositivo(
                dispositivo=dispositivo,
                furo=furo,
                empregado=empregado,
            )
        except ValidationError as exc:
            erro = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response(
                {"erro": erro},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SessaoDispositivoSerializer(sessao).data,
            status=status.HTTP_201_CREATED,
        )


class LerDispositivoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        empregado = obter_empregado_autenticado(request.user)
        if not empregado or not empregado.empresa_id:
            return Response(
                {"erro": "O utilizador autenticado não está associado a um empregado com empresa válida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao = obter_sessao_empresa(pk=pk, empresa_id=empregado.empresa_id)
        try:
            resultado = ler_dispositivo_uma_vez(sessao=sessao)
            return Response(
                {
                    "ok": True,
                    "raw_payload": resultado["raw_payload"],
                    "dados": resultado["dados"],
                    "medicao_id": resultado["medicao_id"],
                    "shot_id": resultado["shot_id"],
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as exc:
            erro = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response(
                {
                    "ok": False,
                    "erro": erro,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class BridgeLeituraAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        empregado = obter_empregado_autenticado(request.user)
        if not empregado or not empregado.empresa_id:
            return Response(
                {"erro": "O utilizador autenticado não está associado a um empregado com empresa válida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data.get("payload")
        if not payload:
            return Response(
                {"erro": "Payload em falta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao_id = request.data.get("sessao_id")
        if not sessao_id:
            return Response(
                {"erro": "sessao_id em falta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao = obter_sessao_ligada_empresa(sessao_id=sessao_id, empresa_id=empregado.empresa_id)

        resultado = guardar_leitura_dispositivo(
            sessao=sessao,
            raw_payload=payload,
        )

        return Response(
            {
                "ok": True,
                "medicao_id": str(resultado["medicao"].id),
                "shot_id": str(resultado["shot"].id),
                "dados": resultado["dados"],
            },
            status=status.HTTP_200_OK,
        )

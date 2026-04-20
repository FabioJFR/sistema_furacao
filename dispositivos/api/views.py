from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dispositivos.api.serializers import (
    SessaoDispositivoCreateSerializer,
    SessaoDispositivoSerializer,
)
from dispositivos.models import SessaoDispositivo
from dispositivos.services.conexao import construir_driver
from dispositivos.services.ingestao import guardar_leitura_dispositivo
from projetos.models import Empregados


class CriarSessaoDispositivoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessaoDispositivoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
        if not empregado or not empregado.empresa_id:
            return Response(
                {"erro": "O utilizador autenticado não está associado a um empregado com empresa válida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dispositivo = serializer.validated_data["dispositivo"]
        furo = serializer.validated_data.get("furo")

        if dispositivo.empresa_id != empregado.empresa_id:
            return Response(
                {"erro": "O dispositivo não pertence à empresa do empregado autenticado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if furo and furo.empresa_id != empregado.empresa_id:
            return Response(
                {"erro": "O furo não pertence à empresa do empregado autenticado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao = serializer.save(
            empresa=empregado.empresa,
            empregado=empregado,
            status="criada",
        )

        return Response(
            SessaoDispositivoSerializer(sessao).data,
            status=status.HTTP_201_CREATED,
        )


class LerDispositivoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
        if not empregado or not empregado.empresa_id:
            return Response(
                {"erro": "O utilizador autenticado não está associado a um empregado com empresa válida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessao = get_object_or_404(
            SessaoDispositivo.objects.select_related("dispositivo", "furo", "empresa", "empregado"),
            pk=pk,
            empresa_id=empregado.empresa_id,
        )

        driver = construir_driver(sessao.dispositivo)

        try:
            sessao.status = "ligando"
            sessao.mensagem_erro = ""
            sessao.save(update_fields=["status", "mensagem_erro"])

            driver.connect()

            sessao.status = "ligado"
            sessao.save(update_fields=["status"])

            raw = driver.read_once()
            resultado = guardar_leitura_dispositivo(sessao=sessao, raw_payload=raw)

            return Response(
                {
                    "ok": True,
                    "raw_payload": raw,
                    "dados": resultado["dados"],
                    "medicao_id": str(resultado["medicao"].id),
                    "shot_id": str(resultado["shot"].id),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            sessao.status = "erro"
            sessao.mensagem_erro = str(e)
            sessao.save(update_fields=["status", "mensagem_erro"])

            return Response(
                {
                    "ok": False,
                    "erro": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        finally:
            try:
                driver.disconnect()
            except Exception:
                pass

            if sessao.status != "erro":
                sessao.status = "encerrada"
                sessao.terminado_em = timezone.now()
                sessao.save(update_fields=["status", "terminado_em"])


class BridgeLeituraAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
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

        sessao = get_object_or_404(
            SessaoDispositivo.objects.select_related("empresa", "furo", "dispositivo"),
            pk=sessao_id,
            empresa_id=empregado.empresa_id,
            status="ligado",
        )

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

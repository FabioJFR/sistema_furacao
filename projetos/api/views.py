from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projetos.api.serializers import FuroSerializer, FuroVersaoSerializer
from projetos.api.selectors import (
    listar_furos_api_qs,
    listar_versoes_furo_api_qs,
    obter_furo_api,
    resolver_empresa_api as resolver_empresa_api_selector,
)


def _resolver_empresa_api(request):
    empresa_id = (request.GET.get("empresa") or request.POST.get("empresa") or "").strip()
    empresa, erro = resolver_empresa_api_selector(request.user, empresa_id=empresa_id)
    if not erro:
        return empresa, None

    if erro == "empresa_invalida":
        return None, Response({"erro": "Empresa inválida."}, status=status.HTTP_404_NOT_FOUND)
    if erro == "sem_empresas":
        return None, Response({"erro": "Sem empresas disponíveis."}, status=status.HTTP_400_BAD_REQUEST)

    return None, Response(
        {"erro": "Conta sem empresa associada para acesso API."},
        status=status.HTTP_403_FORBIDDEN,
    )


class FuroListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa, erro = _resolver_empresa_api(request)
        if erro:
            return erro

        estado = (request.GET.get("estado") or "").strip()
        projeto_id = (request.GET.get("projeto_id") or "").strip()
        nome = (request.GET.get("q") or "").strip()
        limit = min(max(int(request.GET.get("limit", 100) or 100), 1), 500)

        queryset = listar_furos_api_qs(empresa)
        if estado:
            queryset = queryset.filter(estado=estado)
        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)
        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        data = FuroSerializer(queryset[:limit], many=True).data
        return Response({"empresa_id": str(empresa.pk), "total": len(data), "items": data}, status=status.HTTP_200_OK)


class FuroDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa, erro = _resolver_empresa_api(request)
        if erro:
            return erro

        furo = obter_furo_api(pk=pk, empresa=empresa)
        return Response(FuroSerializer(furo).data, status=status.HTTP_200_OK)


class FuroVersaoListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa, erro = _resolver_empresa_api(request)
        if erro:
            return erro

        furo = obter_furo_api(pk=pk, empresa=empresa)
        origem = (request.GET.get("origem") or "").strip()
        limit = min(max(int(request.GET.get("limit", 50) or 50), 1), 200)

        queryset = listar_versoes_furo_api_qs(furo=furo, empresa=empresa)
        if origem:
            queryset = queryset.filter(origem=origem)

        items = FuroVersaoSerializer(queryset[:limit], many=True).data
        return Response(
            {
                "furo_id": str(furo.pk),
                "furo_nome": furo.nome,
                "total": len(items),
                "items": items,
            },
            status=status.HTTP_200_OK,
        )


class FuroUltimaVersaoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa, erro = _resolver_empresa_api(request)
        if erro:
            return erro

        furo = obter_furo_api(pk=pk, empresa=empresa)
        versao = listar_versoes_furo_api_qs(furo=furo, empresa=empresa).first()
        if not versao:
            return Response(
                {"furo_id": str(furo.pk), "furo_nome": furo.nome, "item": None},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"furo_id": str(furo.pk), "furo_nome": furo.nome, "item": FuroVersaoSerializer(versao).data},
            status=status.HTTP_200_OK,
        )

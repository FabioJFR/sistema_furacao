from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from plataforma.models import Empresa, PerfilPlataforma
from projetos.api.serializers import FuroSerializer, FuroVersaoSerializer
from projetos.models import Empregados, Furo, FuroVersao


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


def _resolver_empresa_api(request):
    if request.user.is_superuser:
        empresa_id = (request.GET.get("empresa") or request.POST.get("empresa") or "").strip()
        empresas = Empresa.objects.all().order_by("nome")
        if empresa_id:
            empresa = empresas.filter(pk=empresa_id).first()
            if empresa:
                return empresa, None
            return None, Response({"erro": "Empresa inválida."}, status=status.HTTP_404_NOT_FOUND)
        empresa = empresas.first()
        if empresa:
            return empresa, None
        return None, Response({"erro": "Sem empresas disponíveis."}, status=status.HTTP_400_BAD_REQUEST)

    perfil = (
        PerfilPlataforma.objects.filter(
            user=request.user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
        )
        .select_related("empresa")
        .first()
    )
    if perfil and perfil.empresa_id:
        return perfil.empresa, None

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if empregado and empregado.empresa_id:
        return empregado.empresa, None

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

        queryset = Furo.objects.filter(empresa=empresa).select_related("projeto").order_by("-data", "nome")
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

        furo = get_object_or_404(
            Furo.objects.select_related("projeto"),
            pk=pk,
            empresa=empresa,
        )
        return Response(FuroSerializer(furo).data, status=status.HTTP_200_OK)


class FuroVersaoListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa, erro = _resolver_empresa_api(request)
        if erro:
            return erro

        furo = get_object_or_404(Furo, pk=pk, empresa=empresa)
        origem = (request.GET.get("origem") or "").strip()
        limit = min(max(int(request.GET.get("limit", 50) or 50), 1), 200)

        queryset = (
            FuroVersao.objects.filter(furo=furo, empresa=empresa)
            .select_related("projeto", "furo", "criado_por")
            .order_by("-versao_numero")
        )
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

        furo = get_object_or_404(Furo, pk=pk, empresa=empresa)
        versao = (
            FuroVersao.objects.filter(furo=furo, empresa=empresa)
            .select_related("projeto", "furo", "criado_por")
            .order_by("-versao_numero")
            .first()
        )
        if not versao:
            return Response(
                {"furo_id": str(furo.pk), "furo_nome": furo.nome, "item": None},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"furo_id": str(furo.pk), "furo_nome": furo.nome, "item": FuroVersaoSerializer(versao).data},
            status=status.HTTP_200_OK,
        )


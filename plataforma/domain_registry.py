from plataforma.models import (
    ConfiguracaoFeatureAcesso,
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    Plano,
    SubscricaoEmpresa,
)


PLATAFORMA_MODEL_MAP = {
    "Empresa": Empresa,
    "ConfiguracaoFeatureAcesso": ConfiguracaoFeatureAcesso,
    "PerfilPlataforma": PerfilPlataforma,
    "Plano": Plano,
    "PagamentoEmpresa": PagamentoEmpresa,
    "SubscricaoEmpresa": SubscricaoEmpresa,
    "MovimentoFinanceiroPlataforma": MovimentoFinanceiroPlataforma,
}


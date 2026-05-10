from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

from website import selectors
from website import services

REGISTO_STARTED_AT_SESSION_KEY = "website_registo_started_at"


def _website_quick_links():
    return [
        {"label": _("Sobre"), "url_name": "website:sobre"},
        {"label": _("Contactos"), "url_name": "website:contactos"},
        {"label": _("Feedback"), "url_name": "website:feedback"},
        {"label": _("Termos & Condições"), "url_name": "website:termos_condicoes"},
        {"label": _("Política de Privacidade"), "url_name": "website:politica_privacidade"},
    ]


def _render_public_info_page(request, *, title, eyebrow, intro, sections, meta_notice=""):
    return render(
        request,
        "website/info_page.html",
        {
            "title": title,
            "eyebrow": eyebrow,
            "intro": intro,
            "meta_notice": meta_notice,
            "sections": sections,
            "quick_links": _website_quick_links(),
        },
    )


def home(request):
    planos_qs = selectors.listar_planos_ativos()
    planos_cards = selectors.construir_planos_para_cards(planos_qs)
    return render(
        request,
        "website/home.html",
        {
            "planos": planos_cards[:3],
            "quick_links": _website_quick_links(),
        },
    )


def planos(request):
    planos_qs = selectors.listar_planos_ativos()
    planos_cards = selectors.construir_planos_para_cards(planos_qs)
    return render(
        request,
        "website/planos.html",
        {
            "planos": planos_cards,
        },
    )


def sobre(request):
    return _render_public_info_page(
        request,
        title=_("Sobre o Sistema Furação"),
        eyebrow=_("Plataforma"),
        intro=_("Conhece a missão da plataforma, o contexto do produto e a base legal e operacional que suporta a sua evolução."),
        sections=[
            {
                "title": _("Sobre a plataforma"),
                "paragraphs": [
                    _("O Sistema Furação foi desenhado para apoiar equipas de perfuração e geologia com foco em produtividade, rastreabilidade técnica e apoio à decisão."),
                    _("A plataforma junta operação diária, gestão empresarial, IA aplicada, analytics e modelos 3D numa base única e escalável."),
                ],
            },
            {
                "title": _("Sobre o desenvolvimento"),
                "paragraphs": [
                    _("Desenvolvimento liderado por Fábio Revez, com evolução contínua baseada no uso real de campo e feedback operacional das equipas."),
                ],
            },
            {
                "title": _("Licenças e propriedade intelectual"),
                "paragraphs": [
                    _("Todos os conteúdos, código, design, marca e componentes do Sistema Furação estão protegidos por direitos de propriedade intelectual e legislação aplicável."),
                    _("É proibida a reprodução, distribuição ou utilização não autorizada, total ou parcial, sem consentimento expresso dos titulares dos direitos."),
                ],
            },
        ],
    )


def contactos(request):
    return _render_public_info_page(
        request,
        title=_("Contactos"),
        eyebrow=_("Suporte e contacto"),
        intro=_("Pontos de contacto públicos para questões comerciais, suporte, privacidade e reclamações."),
        sections=[
            {
                "title": _("Contacto geral"),
                "paragraphs": [
                    _("Email: sistemafuracao@gmail.com"),
                    _("Website: https://www.sistemafuracao.pt"),
                    _("Telefone: 928044839"),
                ],
            },
            {
                "title": _("Privacidade e dados"),
                "paragraphs": [
                    _("Para assuntos de privacidade e direitos de dados pessoais, utiliza o email sistemafuracao@gmail.com."),
                ],
            },
            {
                "title": _("Reclamações"),
                "paragraphs": [
                    _("Para reclamações formais em Portugal, podes utilizar o Livro de Reclamações eletrónico."),
                ],
                "links": [
                    {
                        "label": _("Livro de Reclamações"),
                        "url": "https://www.livroreclamacoes.pt/Inicio/",
                        "external": True,
                    }
                ],
            },
        ],
    )


def feedback(request):
    return _render_public_info_page(
        request,
        title=_("Feedback e contacto público"),
        eyebrow=_("Visitantes"),
        intro=_("Escolhe o canal mais adequado para deixar uma mensagem, avaliar a plataforma ou reportar um problema de forma simples."),
        sections=[
            {
                "title": _("Deixar uma mensagem"),
                "paragraphs": [
                    _("Se queres fazer uma pergunta, pedir mais informação ou iniciar contacto comercial, podes enviar-nos uma mensagem direta."),
                    _("Usa este canal para pedidos gerais, dúvidas iniciais ou conversas de apresentação da plataforma."),
                ],
                "links": [
                    {
                        "label": _("Enviar mensagem"),
                        "url": "mailto:sistemafuracao@gmail.com?subject=Mensagem%20sobre%20o%20Sistema%20de%20Fura%C3%A7%C3%A3o",
                        "external": True,
                    }
                ],
            },
            {
                "title": _("Avaliar a plataforma"),
                "paragraphs": [
                    _("Se já viste a plataforma, a landing page ou uma demonstração, podes enviar a tua opinião e avaliação geral."),
                    _("Este canal é útil para perceção de valor, clareza da proposta e feedback sobre a experiência pública."),
                ],
                "links": [
                    {
                        "label": _("Enviar avaliação"),
                        "url": "mailto:sistemafuracao@gmail.com?subject=Avalia%C3%A7%C3%A3o%20da%20plataforma",
                        "external": True,
                    }
                ],
            },
            {
                "title": _("Reportar um problema"),
                "paragraphs": [
                    _("Se encontraste um erro, falha técnica, link partido ou comportamento inesperado, podes reportar o problema diretamente."),
                    _("Se possível, inclui o que estavas a fazer, a página afetada e uma captura de ecrã para acelerar a análise."),
                ],
                "links": [
                    {
                        "label": _("Reportar problema"),
                        "url": "mailto:sistemafuracao@gmail.com?subject=Reporte%20de%20problema%20na%20plataforma",
                        "external": True,
                    },
                    {
                        "label": _("Livro de Reclamações"),
                        "url": "https://www.livroreclamacoes.pt/Inicio/",
                        "external": True,
                    },
                ],
            },
        ],
    )


def termos_condicoes(request):
    return _render_public_info_page(
        request,
        title=_("Termos & Condições"),
        eyebrow=_("Informação legal"),
        intro=_("Condições gerais de utilização da plataforma Sistema Furação."),
        meta_notice=_("Versão pública informativa, revista em maio de 2026."),
        sections=[
            {
                "title": _("Identificação do titular da plataforma"),
                "paragraphs": [
                    _("Nome: Fabio Jorge Felicio Revez"),
                    _("Sede operacional: Portugal"),
                    _("Email de suporte: sistemafuracao@gmail.com"),
                    _("Telefone: 928044839"),
                ],
            },
            {
                "title": _("Objeto e aceitação"),
                "paragraphs": [
                    _("Os presentes Termos & Condições regulam o acesso e utilização da plataforma Sistema Furação por empresas, profissionais e utilizadores particulares com idade mínima de 18 anos."),
                    _("Ao utilizar a plataforma, o utilizador declara que leu, compreendeu e aceitou estes termos."),
                ],
            },
            {
                "title": _("Planos, subscrições e cancelamento"),
                "paragraphs": [
                    _("A plataforma pode operar com subscrição mensal ou anual, de acordo com o plano contratado."),
                    _("Pode existir período de teste inicial, nos termos apresentados no momento de adesão."),
                    _("Em caso de cancelamento, aplica-se a política definida: sem reembolso, ou reembolso proporcional ao tempo remanescente da subscrição, quando aplicável e validado pelo titular da plataforma."),
                ],
            },
            {
                "title": _("Utilização permitida e responsabilidade"),
                "paragraphs": [
                    _("É proibido utilizar a plataforma para finalidades ilícitas, manipulação indevida de dados, tentativas de acesso não autorizado, engenharia reversa ou qualquer atividade que comprometa a segurança e disponibilidade do serviço."),
                    _("A plataforma procura assegurar elevada disponibilidade, mas poderão ocorrer interrupções para manutenção, atualizações, falhas técnicas ou motivos de força maior."),
                ],
            },
            {
                "title": _("Lei aplicável e contacto"),
                "paragraphs": [
                    _("Estes termos regem-se pela lei portuguesa. Para resolução de litígios, é competente o foro de Lisboa, com expressa renúncia a qualquer outro."),
                    _("Para questões de suporte, contacte sistemafuracao@gmail.com."),
                ],
                "links": [
                    {
                        "label": _("Política de Privacidade"),
                        "url_name": "website:politica_privacidade",
                    }
                ],
            },
        ],
    )


def politica_privacidade(request):
    return _render_public_info_page(
        request,
        title=_("Política de Privacidade"),
        eyebrow=_("Informação legal"),
        intro=_("Informação sobre o tratamento de dados pessoais no Sistema Furação."),
        meta_notice=_("Versão pública informativa, revista em maio de 2026."),
        sections=[
            {
                "title": _("Responsável pelo tratamento"),
                "paragraphs": [
                    _("Nome: Fabio Jorge Felicio Revez"),
                    _("Localização: Portugal"),
                    _("Email: sistemafuracao@gmail.com"),
                ],
            },
            {
                "title": _("Que dados tratamos"),
                "paragraphs": [
                    _("Dados de conta (nome, email, perfil), dados operacionais inseridos pelos utilizadores (projetos, furos, logs, registos), e dados técnicos necessários ao funcionamento e segurança da plataforma."),
                ],
            },
            {
                "title": _("Finalidades e base legal"),
                "paragraphs": [
                    _("Gestão de acesso, prestação do serviço, suporte ao utilizador, melhoria do produto, segurança operacional e cumprimento de obrigações legais."),
                    _("Execução de contrato, diligências pré-contratuais, interesse legítimo na segurança e evolução do serviço, e cumprimento de obrigações legais."),
                ],
            },
            {
                "title": _("Cookies e medição de utilização"),
                "paragraphs": [
                    _("As páginas públicas da plataforma podem usar ferramentas técnicas de medição e análise de visitas para compreender o uso do website e melhorar a experiência disponibilizada aos visitantes."),
                    _("Essas medições podem incluir serviços de analytics de terceiros, como o Google Analytics, aplicados às páginas públicas institucionais."),
                    _("Se preferires, podes limitar ou bloquear cookies e tecnologias semelhantes através das definições do teu navegador."),
                ],
            },
            {
                "title": _("Conservação, partilha e direitos"),
                "paragraphs": [
                    _("Os dados são conservados pelo período necessário às finalidades indicadas, podendo ser mantidos por prazo superior quando exigido por lei ou para defesa de direitos."),
                    _("Os dados não são vendidos. Podem ser partilhados com prestadores de serviços essenciais ao funcionamento da plataforma, sempre com medidas de proteção adequadas."),
                    _("Nos termos legais, pode solicitar acesso, retificação, apagamento, limitação, oposição e portabilidade dos seus dados, bem como retirar consentimentos quando aplicável."),
                ],
            },
            {
                "title": _("Segurança e contacto"),
                "paragraphs": [
                    _("São aplicadas medidas técnicas e organizativas para proteger os dados contra acesso não autorizado, perda, alteração ou divulgação indevida."),
                    _("Para assuntos de privacidade, utilize o email sistemafuracao@gmail.com."),
                ],
                "links": [
                    {
                        "label": _("Livro de Reclamações"),
                        "url": "https://www.livroreclamacoes.pt/Inicio/",
                        "external": True,
                    }
                ],
            },
        ],
    )


def registo(request):
    planos_qs = selectors.listar_planos_ativos()
    planos_contexto = selectors.construir_planos_contexto(planos_qs)

    if request.method == "POST":
        resultado = services.executar_registo(
            request.POST,
            request=request,
            registo_started_at=request.session.get(REGISTO_STARTED_AT_SESSION_KEY),
        )
        if not resultado.sucesso:
            for erro in resultado.erros:
                messages.error(request, erro)
            return render(
                request,
                "website/registo.html",
                {
                    "planos": planos_qs,
                    "dados": request.POST,
                    "planos_contexto": planos_contexto,
                },
            )

        messages.success(
            request,
            _("Conta criada com sucesso. Enviámos um email para confirmares a conta antes do primeiro login."),
        )
        request.session.pop(REGISTO_STARTED_AT_SESSION_KEY, None)
        return redirect("login")

    request.session[REGISTO_STARTED_AT_SESSION_KEY] = timezone.now().timestamp()
    return render(
        request,
        "website/registo.html",
        {
            "planos": planos_qs,
            "planos_contexto": planos_contexto,
        },
    )


def logout_user(request):
    logout(request)
    return redirect("website:home")


def confirmar_conta(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid).first()
    except (TypeError, ValueError, OverflowError):
        user = None

    if not user:
        messages.error(request, _("Link de confirmação inválido."))
        return redirect("login")

    if user.is_active:
        messages.info(request, _("A tua conta já está confirmada. Podes iniciar sessão."))
        return redirect("login")

    if not default_token_generator.check_token(user, token):
        messages.error(request, _("Este link de confirmação é inválido ou já expirou."))
        return redirect("login")

    user.is_active = True
    user.save(update_fields=["is_active"])
    messages.success(request, _("Conta confirmada com sucesso. Já podes iniciar sessão."))
    return redirect("login")


def reenviar_confirmacao(request):
    if request.method != "POST":
        return redirect("login")

    email = (request.POST.get("email") or "").strip()
    if not email:
        messages.error(request, _("Indica o email para reenviar a confirmação."))
        return redirect("login")

    try:
        services.reenviar_confirmacao_por_email(email=email, request=request)
    except Exception:
        messages.error(
            request,
            _("Não foi possível reenviar o email de confirmação neste momento. Tenta novamente."),
        )
        return redirect("login")

    messages.success(
        request,
        _("Se existir uma conta pendente com esse email, enviámos um novo link de confirmação."),
    )
    return redirect("login")


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /app/",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import Projeto, Furo, Empregados, EmpregadoProjeto, EmpregadoFicheiro, Maquina, Material, Medicao
from .forms import *
import plotly.graph_objs as go
from plotly.offline import plot
from .utils import calcular_trajetoria_min_curv
from django.contrib import messages
import math
import requests
from urllib.parse import quote
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import resolve_url
from .decorators import admin_required, empregado_required
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.utils.dateparse import parse_date
from collections import OrderedDict
from django.db.models import Sum, Count, F
from datetime import timedelta


# -------------- DASHBOARD ---------------


@login_required
@admin_required
def dashboard(request):
    projetos_qs = Projeto.objects.all().order_by('nome')

    projetos = []
    for p in projetos_qs:
        projetos.append({
            "id": str(p.id),
            "nome": p.nome,
            "cidade": p.cidade,
            "pais": p.pais,
            "status": p.status,
            "localizacao_lat": float(p.localizacao_lat) if p.localizacao_lat is not None else None,
            "localizacao_lon": float(p.localizacao_lon) if p.localizacao_lon is not None else None,
        })

    # -------- TOTAIS GERAIS --------
    total_projetos = Projeto.objects.count()
    total_furos = Furo.objects.count()
    total_empregados = Empregados.objects.count()
    total_maquinas = Maquina.objects.count()
    total_materiais = Material.objects.count()

    # -------- ALERTAS --------
    materiais_stock_baixo = Material.objects.filter(
        ativo=True,
        quantidade__lte=F('stock_minimo')
    ).order_by('quantidade')

    maquinas_alerta = Maquina.objects.filter(
        estado__in=['avariada', 'reparacao', 'parada']
    ).order_by('nome')

    # -------- REGISTOS DIÁRIOS --------
    registos = RegistoDiarioEmpregado.objects.select_related(
        'empregado', 'projeto', 'furo'
    ).order_by('data')

    agregados_dia = OrderedDict()

    for registo in registos:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados_dia:
            agregados_dia[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados_dia[chave]["metros"] += registo.metros_furados or 0
        agregados_dia[chave]["horas"] += registo.horas_trabalhadas or 0

    labels_dia = []
    metros_dia = []
    horas_dia = []
    produtividade_dia = []

    for data_label, valores in agregados_dia.items():
        labels_dia.append(data_label)

        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = metros / horas if horas > 0 else 0

        metros_dia.append(round(metros, 2))
        horas_dia.append(round(horas, 2))
        produtividade_dia.append(round(produtividade, 2))

    # -------- METROS POR EMPREGADO --------
    empregados_stats = Empregados.objects.order_by('-total_metros_furados')[:10]
    labels_empregados = [e.nome for e in empregados_stats]
    metros_empregados = [round(e.total_metros_furados or 0, 2) for e in empregados_stats]

    # -------- METROS POR PROJETO --------
    projetos_stats = Projeto.objects.annotate(
        total_metros=Sum('registos_empregados__metros_furados')
    ).order_by('-total_metros')[:10]

    labels_projetos = [p.nome for p in projetos_stats]
    metros_projetos = [round(p.total_metros or 0, 2) for p in projetos_stats]

    # -------- METROS POR FURO --------
    furos_stats = Furo.objects.annotate(
        total_metros=Sum('registos_empregados__metros_furados')
    ).order_by('-total_metros')[:10]

    labels_furos = [f.nome for f in furos_stats]
    metros_furos = [round(f.total_metros or 0, 2) for f in furos_stats]

    context = {
        "total_projetos": total_projetos,
        "total_furos": total_furos,
        "total_empregados": total_empregados,
        "total_maquinas": total_maquinas,
        "total_materiais": total_materiais,

        "projetos": projetos,

        "materiais_stock_baixo": materiais_stock_baixo,
        "maquinas_alerta": maquinas_alerta,

        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,

        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,

        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,

        "labels_furos": labels_furos,
        "metros_furos": metros_furos,
    }

    return render(request, "projetos/dashboard.html", context)

# ---------------- HOME ----------------
def home(request):
    projetos = Projeto.objects.all().values(
        "id", "nome", "localizacao_lat", "localizacao_lon"
    )
    return render(request, "projetos/home.html", {
        "projetos": list(projetos)
    })


# ---------------- PROJETOS ----------------
@login_required
@admin_required
def projeto_list(request):
    projetos_qs = Projeto.objects.all()
    projetos_serializaveis = list(projetos_qs.values(
        'id', 'pk', 'nome', 'cliente', 'cidade', 'pais', 'localizacao_lat', 'localizacao_lon'
    ))
    context = {'projetos': projetos_serializaveis}
    return render(request, 'projetos/projeto_list.html', context)

def projeto_detail(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    levantamentos = projeto.levantamentos_materiais.select_related(
        'empregado', 'material', 'furo'
    ).all()

    return render(request, "projetos/projeto_detail.html", {
        "projeto": projeto,
        "levantamentos": levantamentos,
    })

@login_required
@admin_required
def projeto_create(request):
    if request.method == 'POST':
        form = ProjetoForm(request.POST)
        if form.is_valid():
            projeto = form.save(commit=False)

            lat, lon = obter_coordenadas_por_cidade_pais(
                projeto.cidade,
                projeto.pais
            )

            projeto.localizacao_lat = lat
            projeto.localizacao_lon = lon

            projeto.save()
            messages.success(request, "Projeto criado com sucesso.")
            return redirect('projetos:projeto_list')
        else:
            messages.error(request, "Erro ao criar o projeto. Verifique os dados.")
    else:
        form = ProjetoForm()

    return render(request, 'projetos/projeto_form.html', {'form': form})

@login_required
@admin_required
def projeto_update(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    form = ProjetoForm(request.POST or None, instance=projeto)

    if request.method == "POST":
        if form.is_valid():
            projeto = form.save(commit=False)

            lat, lon = obter_coordenadas_por_cidade_pais(
                projeto.cidade,
                projeto.pais
            )

            projeto.localizacao_lat = lat
            projeto.localizacao_lon = lon

            projeto.save()
            messages.success(request, "Projeto atualizado com sucesso.")
            return redirect("projetos:projeto_detail", pk=projeto.pk)
        else:
            messages.error(request, "Erro ao atualizar o projeto. Verifique os dados.")

    return render(request, "projetos/projeto_editar.html", {
        "form": form,
        "projeto": projeto
    })

@login_required
@admin_required
def projeto_delete(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)

    if request.method == "POST":
        projeto.delete()
        return redirect('projetos:projeto_list')

    return render(request, 'projetos/projeto_confirm_delete.html', {
        'projeto': projeto
    })


# ---------------- FUROS ----------------
@login_required
@admin_required
def furo_create(request):
    if request.method == 'POST':
        form = FuroCreateForm(request.POST)
        if form.is_valid():
            furo = form.save(commit=False)

            # Garantir defaults técnicos
            furo.origem_este = furo.origem_este or 0.0
            furo.origem_norte = furo.origem_norte or 0.0
            furo.origem_tvd = furo.origem_tvd or 0.0

            # Garantir coerência inicial
            furo.profundidade_atual = furo.profundidade_inicial or 0.0
            if (furo.profundidade_final or 0.0) < (furo.profundidade_atual or 0.0):
                furo.profundidade_final = furo.profundidade_atual

            furo.save()

            messages.success(request, "Furo criado com sucesso.")
            return redirect('projetos:furo_detail', pk=furo.pk)
        else:
            messages.error(request, "Erro ao criar o furo. Verifique os dados.")
    else:
        form = FuroCreateForm()

    return render(request, 'projetos/form.html', {
        'form': form,
        'titulo': 'Criar Novo Furo'
    })

@login_required
@admin_required
def furo_detail(request, pk):
    furo = get_object_or_404(Furo, pk=pk)

    levantamentos = furo.levantamentos_materiais.select_related(
        'empregado', 'material', 'projeto'
    ).all()

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES, furo=furo)
        if form.is_valid():
            medicao = form.save(commit=False)
            medicao.furo = furo
            medicao.nome_furo = furo.nome

            # Herdar localização do furo se não vier preenchida na medição
            if medicao.latitude is None:
                medicao.latitude = furo.latitude
            if medicao.longitude is None:
                medicao.longitude = furo.longitude
            if medicao.altitude is None:
                medicao.altitude = furo.altitude

            medicao.save()

            # Atualizar resumo do furo com base na última medição
            profundidade = medicao.profundidade or 0.0
            furo.profundidade_atual = profundidade

            if profundidade > (furo.profundidade_final or 0.0):
                furo.profundidade_final = profundidade

            if medicao.inclinacao is not None:
                furo.inclinacao = medicao.inclinacao
            if medicao.azimute is not None:
                furo.azimute = medicao.azimute
            if medicao.magnetismo is not None:
                furo.magnetismo = medicao.magnetismo

            furo.save()

            messages.success(request, "Medição registrada com sucesso!")
            return redirect('projetos:furo_detail', pk=furo.pk)
        else:
            messages.error(request, "Erro ao registrar medição. Verifique os dados.")
    else:
        form = MedicaoForm(furo=furo)

    context = {
        'furo': furo,
        'form': form,
        'levantamentos': levantamentos,
    }
    return render(request, 'projetos/furo_detail.html', context)

@login_required
@admin_required
def furo_list(request):
    furos = Furo.objects.all()
    return render(request, 'projetos/furo_list.html', {'furos': furos})

@login_required
@admin_required
def furo_update(request, pk):
    furo = get_object_or_404(Furo, pk=pk)

    if request.method == 'POST':
        form = FuroForm(request.POST, instance=furo)
        if form.is_valid():
            furo = form.save(commit=False)

            # 🔧 Garantir coerência das profundidades
            if furo.profundidade_atual and furo.profundidade_final:
                if furo.profundidade_atual > furo.profundidade_final:
                    furo.profundidade_final = furo.profundidade_atual

            # 🔧 Se não houver medições, limpar valores dependentes
            if not furo.medicoes.exists():
                furo.profundidade_atual = 0.0
                furo.profundidade_final = 0.0

            # 🔧 Garantir origem válida (importante para o 3D)
            furo.origem_este = furo.origem_este or 0.0
            furo.origem_norte = furo.origem_norte or 0.0
            furo.origem_tvd = furo.origem_tvd or 0.0

            furo.save()

            messages.success(request, "Furo atualizado com sucesso.")
            return redirect('projetos:furo_detail', pk=furo.pk)
        else:
            messages.error(request, "Erro ao atualizar o furo. Verifique os dados.")
            print("ERROS DO FORM:", form.errors)
            messages.error(request, "Erro ao atualizar o furo.")
    else:
        form = FuroForm(instance=furo)

    return render(request, 'projetos/furo_update.html', {
        'form': form,
        'furo': furo
    })

@login_required
@admin_required
def furo_delete(request, pk):
    furo = get_object_or_404(Furo, pk=pk)
    if request.method == 'POST':
        furo.delete()
        return redirect('projetos:furo_list')
    return render(request, 'projetos/furo_confirm_delete.html', {'furo': furo})


# ---------------- 3D ----------------
@login_required
@admin_required
def projeto_3d(request, pk):
    projeto = get_object_or_404(Projeto, id=pk)
    fig = go.Figure()
    tem_dados = False

    for furo in projeto.furos.all():
        medicoes = list(furo.medicoes.all().order_by("profundidade"))

        if not medicoes:
            continue

        tem_dados = True

        origem = (
            float(furo.origem_este or 0.0),
            float(furo.origem_norte or 0.0),
            float(furo.origem_tvd or 0.0)
        )

        pontos, doglegs, alertas = calcular_trajetoria_min_curv(
            medicoes,
            origem=origem
        )

        x = [p[0] for p in pontos]
        y = [p[1] for p in pontos]
        z = [p[2] for p in pontos]

        customdata = []

        customdata.append([
            0.0,
            0.0,
            0.0,
            "ORIGEM",
            furo.nome
        ])

        for i, med in enumerate(medicoes, start=1):
            estado = alertas[i] if i < len(alertas) else "OK"
            customdata.append([
                med.profundidade or 0.0,
                med.inclinacao or 0.0,
                med.azimute or 0.0,
                estado,
                furo.nome
            ])

        fig.add_trace(go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='lines+markers',
            name=furo.nome,
            marker=dict(size=6),
            line=dict(width=4),
            customdata=customdata,
            hovertemplate=(
                "Furo: %{customdata[4]}<br>"
                "Este: %{x:.2f} m<br>"
                "Norte: %{y:.2f} m<br>"
                "Profundidade: %{z:.2f} m<br>"
                "MD: %{customdata[0]:.2f} m<br>"
                "Inclinação: %{customdata[1]:.2f}°<br>"
                "Azimute: %{customdata[2]:.2f}°<br>"
                "Estado: %{customdata[3]}<br>"
                "<extra></extra>"
            )
        ))

    if not tem_dados:
        messages.warning(request, "Este projeto ainda não possui furos com medições.")
        return render(request, "projetos/projeto_3d.html", {
            "projeto": projeto,
            "graph": None
        })

    fig.update_layout(
        scene=dict(
            xaxis_title='Este (m)',
            yaxis_title='Norte (m)',
            zaxis_title='Profundidade (m)',
            zaxis=dict(autorange="reversed"),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.2)
            )
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.85,   # 👈 BAIXA A LEGENDA (ajusta se precisares)
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11)
        ),
        margin=dict(l=0, r=140, t=20, b=0),
        height=800
    )

    graph = plot(fig, output_type='div')
    return render(request, "projetos/projeto_3d.html", {
        "projeto": projeto,
        "graph": graph
    })

@login_required
def furo_3d_geologico(request, furo_id):
    furo = get_object_or_404(Furo, id=furo_id)

    # ---------------- CONTROLO DE ACESSO ----------------
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Administradores').exists()

    if not is_admin:
        empregado = get_object_or_404(Empregados, user=request.user)

        trabalhou_no_furo = RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            furo=furo
        ).exists()

        if not trabalhou_no_furo:
            messages.error(request, "Não tens permissão para ver o 3D deste furo.")
            return redirect('projetos:area_empregado')

    medicoes = list(furo.medicoes.all().order_by("profundidade"))

    if not medicoes:
        messages.warning(request, "Este furo ainda não possui medições.")
        return render(request, "projetos/furo_3d.html", {
            "furo": furo,
            "graph": None,
            "numero_medicoes": 0,
            "profundidade_final": 0.0,
            "dogleg_max": 0.0,
            "estado_max": "OK",
        })

    origem = (
        float(furo.origem_este or 0.0),
        float(furo.origem_norte or 0.0),
        float(furo.origem_tvd or 0.0)
    )

    pontos, doglegs, alertas = calcular_trajetoria_min_curv(
        medicoes,
        origem=origem
    )

    x, y, z = [], [], []
    customdata = []

    # -------------------------------------------------
    # PONTO 0 = ORIGEM
    # -------------------------------------------------
    x.append(pontos[0][0])
    y.append(pontos[0][1])
    z.append(pontos[0][2])
    customdata.append([0.0, 0.0, 0.0, 0.0, None, "ORIGEM"])

    # -------------------------------------------------
    # PONTOS SEGUINTES = MEDIÇÕES
    # pontos[1] -> medicoes[0]
    # pontos[2] -> medicoes[1]
    # etc.
    # -------------------------------------------------
    for i, med in enumerate(medicoes, start=1):
        if i >= len(pontos):
            break

        x_coord, y_coord, z_coord = pontos[i]

        prof = med.profundidade or 0.0
        incl = med.inclinacao or 0.0
        azim = med.azimute or 0.0
        mag = med.magnetismo if med.magnetismo is not None else 0.0

        img = med.imagem if med.imagem else None
        img_url = img.url if img else None

        estado = alertas[i] if i < len(alertas) else "OK"

        x.append(x_coord)
        y.append(y_coord)
        z.append(z_coord)

        customdata.append([prof, incl, azim, mag, img_url, estado])

    # -------------------------------------------------
    # SETAS
    # -------------------------------------------------
    seta_tracos = []
    for i in range(1, len(x)):
        if i % 3 != 0:
            continue

        x0, y0, z0 = x[i - 1], y[i - 1], z[i - 1]
        x1, y1, z1 = x[i], y[i], z[i]

        seta_tracos.append(go.Cone(
            x=[x0],
            y=[y0],
            z=[z0],
            u=[x1 - x0],
            v=[y1 - y0],
            w=[z1 - z0],
            sizemode="absolute",
            sizeref=8,
            anchor="tail",
            colorscale="Viridis",
            showscale=False,
            hoverinfo="skip"
        ))

    # -------------------------------------------------
    # SCATTER PRINCIPAL
    # -------------------------------------------------
    scatter = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='lines+markers',
        line=dict(width=5, color='blue'),
        marker=dict(
            size=8,
            color=doglegs[:len(x)],
            colorscale=[
                [0, "green"],
                [0.5, "yellow"],
                [1, "red"]
            ],
            colorbar=dict(
                title='Dogleg',
                len=0.6,
                thickness=12,
                x=1.08,
                y=0.45,
            ),
            showscale=True
        ),
        customdata=customdata,
        hovertemplate=(
            "Profundidade: %{customdata[0]:.2f} m<br>"
            "Inclinação: %{customdata[1]:.2f}°<br>"
            "Azimute: %{customdata[2]:.2f}°<br>"
            "Magnetismo: %{customdata[3]:.2f}<br>"
            "Estado: %{customdata[5]}<br>"
            "<extra></extra>"
        )
    )

    tubo = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='lines',
        line=dict(
            width=14,
            color='rgba(52, 152, 219, 0.6)'
        ),
        hoverinfo='skip'
    )

    fig = go.Figure(data=[tubo, scatter] + seta_tracos)

    dogleg_max = max(doglegs) if doglegs else 0.0
    estado_max = "OK"
    if any(a == "CRÍTICO" for a in alertas):
        estado_max = "CRÍTICO"
    elif any(a == "ATENÇÃO" for a in alertas):
        estado_max = "ATENÇÃO"

    fig.update_layout(
        scene=dict(
            xaxis_title='Este (m)',
            yaxis_title='Norte (m)',
            zaxis_title='Profundidade (m)',
            zaxis=dict(autorange="reversed"),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.2)
            )
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11)
        ),
        margin=dict(l=0, r=140, t=20, b=0),
        height=800
    )

    graph = fig.to_html(full_html=False)

    return render(request, "projetos/furo_3d.html", {
        "furo": furo,
        "graph": graph,
        "numero_medicoes": len(medicoes),
        "profundidade_final": medicoes[-1].profundidade if medicoes else 0.0,
        "dogleg_max": dogleg_max,
        "estado_max": estado_max,
    })

# ---------------- MAQUINAS ----------------
@login_required
@admin_required
def maquina_list(request):
    maquinas = Maquina.objects.all().order_by('nome')
    return render(request, "projetos/maquina_list.html", {
        "maquinas": maquinas
    })


@login_required
@admin_required
def maquina_detail(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    return render(request, "projetos/maquina_detail.html", {
        "maquina": maquina
    })


@login_required
@admin_required
def maquina_create(request):
    if request.method == "POST":
        form = MaquinaForm(request.POST)
        if form.is_valid():
            maquina = form.save()
            messages.success(request, "Máquina criada com sucesso.")
            return redirect('projetos:maquina_detail', maquina_id=maquina.id)
        else:
            messages.error(request, "Erro ao criar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm()

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Nova Máquina'
    })


@login_required
@admin_required
def maquina_update(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)

    if request.method == "POST":
        form = MaquinaForm(request.POST, instance=maquina)
        if form.is_valid():
            form.save()
            messages.success(request, "Máquina atualizada com sucesso.")
            return redirect('projetos:maquina_detail', maquina_id=maquina.id)
        else:
            messages.error(request, "Erro ao atualizar a máquina. Verifique os dados.")
    else:
        form = MaquinaForm(instance=maquina)

    return render(request, 'projetos/maquina_form.html', {
        'form': form,
        'titulo': 'Editar Máquina',
        'maquina': maquina
    })


@login_required
@admin_required
def maquina_delete(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)

    if request.method == "POST":
        maquina.delete()
        messages.success(request, "Máquina apagada com sucesso.")
        return redirect('projetos:maquina_list')

    return render(request, 'projetos/maquina_confirm_delete.html', {
        'maquina': maquina
    })

# ---------------- EMPREGADOS ----------------
def registo_empregado(request):
    if request.method == "POST":
        form = EmpregadoRegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = False
            user.save()

            Empregados.objects.create(
                user=user,
                nome=form.cleaned_data['nome'],
                email=form.cleaned_data['email'],
                telefone=form.cleaned_data.get('telefone'),
                funcao=form.cleaned_data.get('funcao'),
                aprovado=False
            )

            messages.success(request, "Registo enviado com sucesso. Aguarde aprovação do administrador.")
            return redirect('login')
        else:
            messages.error(request, "Existem erros no formulário. Corrija os campos assinalados.")
            print("ERROS REGISTO:", form.errors)
    else:
        form = EmpregadoRegistroForm()

    return render(request, "projetos/registo_empregado.html", {
        "form": form,
        "titulo": "Registo de Empregado"
    })

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
@admin_required
def empregado_list(request):
    empregados = Empregados.objects.all().order_by('nome')
    return render(request, "projetos/empregado_list.html", {
        "empregados": empregados
    })

@login_required
@admin_required
def empregado_create(request):
    form = EmpregadoCreateForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        empregado = form.save()

        # 🔹 Criar user automaticamente
        username = empregado.email or empregado.nome.replace(" ", "").lower()
        password = "123456"  # depois podes melhorar isto

        user = User.objects.create_user(
            username=username,
            password=password,
            email=empregado.email
        )

        # 🔹 ligar ao empregado
        empregado.user = user
        empregado.save()

        # 🔹 adicionar ao grupo empregado
        grupo = Group.objects.get(name='Empregados')
        user.groups.add(grupo)

        messages.success(request, "Empregado criado com sucesso.")
        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Novo Empregado"
    })

@login_required
@admin_required
def empregado_detail(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    return render(request, "projetos/empregado_detail.html", {
        "empregado": empregado
    })

@login_required
@admin_required
def empregado_update(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoUpdateForm(request.POST, request.FILES, instance=empregado)
        if form.is_valid():
            form.save()
            messages.success(request, "Empregado atualizado com sucesso.")
            return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao atualizar empregado. Verifique os dados.")
            print("ERROS DO FORM:", form.errors)
    else:
        form = EmpregadoUpdateForm(instance=empregado)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Editar Empregado",
        "empregado": empregado
    })

@login_required
@admin_required
def empregado_delete(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        empregado.delete()
        messages.success(request, "Empregado apagado com sucesso.")
        return redirect("projetos:empregado_list")

    return render(request, "projetos/empregado_confirm_delete.html", {
        "empregado": empregado
    })

@login_required
@admin_required
def empregado_adicionar_projeto(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoProjetoForm(request.POST)
        if form.is_valid():
            ligacao = form.save(commit=False)
            ligacao.empregado = empregado

            # Evita duplicar ligação ativa ao mesmo projeto
            existe_ativa = EmpregadoProjeto.objects.filter(
                empregado=empregado,
                projeto=ligacao.projeto,
                ativo=True
            ).exists()

            if ligacao.ativo and existe_ativa:
                form.add_error('projeto', 'Este empregado já está associado de forma ativa a este projeto.')
            else:
                ligacao.save()
                messages.success(request, "Projeto associado ao empregado com sucesso.")
                return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao associar projeto. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm()

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Associar Projeto ao Empregado"
    })

@login_required
@admin_required
def empregado_editar_projeto(request, pk, ligacao_id):
    empregado = get_object_or_404(Empregados, pk=pk)
    ligacao = get_object_or_404(EmpregadoProjeto, id=ligacao_id, empregado=empregado)

    if request.method == "POST":
        form = EmpregadoProjetoForm(request.POST, instance=ligacao)
        if form.is_valid():
            nova_ligacao = form.save(commit=False)
            nova_ligacao.empregado = empregado

            existe_ativa = EmpregadoProjeto.objects.filter(
                empregado=empregado,
                projeto=nova_ligacao.projeto,
                ativo=True
            ).exclude(id=ligacao.id).exists()

            if nova_ligacao.ativo and existe_ativa:
                form.add_error('projeto', 'Este empregado já está associado de forma ativa a este projeto.')
            else:
                nova_ligacao.save()
                messages.success(request, "Ligação projeto/empregado atualizada com sucesso.")
                return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao atualizar ligação. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm(instance=ligacao)

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Editar Ligação de Projeto"
    })

@login_required
@admin_required
def empregado_terminar_projeto(request, pk, ligacao_id):
    empregado = get_object_or_404(Empregados, pk=pk)
    ligacao = get_object_or_404(EmpregadoProjeto, id=ligacao_id, empregado=empregado)

    if request.method == "POST":
        ligacao.ativo = False
        if not ligacao.data_fim:
            ligacao.data_fim = timezone.now().date()
        ligacao.save()

        messages.success(request, "Projeto encerrado para este empregado com sucesso.")
        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_projeto_confirm_terminar.html", {
        "empregado": empregado,
        "ligacao": ligacao
    })

@login_required
@admin_required
def empregado_adicionar_ficheiro(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoFicheiroForm(request.POST, request.FILES)
        if form.is_valid():
            ficheiro = form.save(commit=False)
            ficheiro.empregado = empregado
            ficheiro.save()
            messages.success(request, "Ficheiro adicionado com sucesso.")
            return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao adicionar ficheiro. Verifique os dados.")
    else:
        form = EmpregadoFicheiroForm()

    return render(request, "projetos/empregado_ficheiro_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Adicionar Ficheiro ao Empregado"
    })

@login_required
@admin_required
def empregado_apagar_ficheiro(request, pk, ficheiro_id):
    empregado = get_object_or_404(Empregados, pk=pk)
    ficheiro = get_object_or_404(EmpregadoFicheiro, id=ficheiro_id, empregado=empregado)

    if request.method == "POST":
        if ficheiro.ficheiro:
            ficheiro.ficheiro.delete(save=False)
        ficheiro.delete()
        messages.success(request, "Ficheiro removido com sucesso.")
        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_ficheiro_confirm_delete.html", {
        "empregado": empregado,
        "ficheiro": ficheiro
    })

@login_required
@admin_required
def empregado_pendentes(request):
    empregados = Empregados.objects.filter(aprovado=False).order_by('-data_registo')
    return render(request, "projetos/empregado_pendentes.html", {
        "empregados": empregados
    })

@login_required
@admin_required
def empregado_aprovar(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        empregado.aprovado = True
        empregado.data_aprovacao = timezone.now()
        empregado.save()

        if empregado.user:
            empregado.user.is_active = True
            empregado.user.save()

            grupo, _ = Group.objects.get_or_create(name='Empregados')
            empregado.user.groups.add(grupo)

        messages.success(request, "Empregado aprovado com sucesso.")
        return redirect('projetos:empregado_pendentes')

    return render(request, "projetos/empregado_aprovar_confirm.html", {
        "empregado": empregado
    })

#-------------- AREA EMPREGADO ------------- #
@login_required
@empregado_required
def area_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    furos_trabalhados = Furo.objects.filter(
        registos_empregados__empregado=empregado
    ).distinct()
    ultimos_registos = empregado.registos_diarios.select_related(
        'projeto', 'furo'
    ).all()[:5]

    # -------- DADOS RESUMIDOS --------
    horas_hoje = empregado.horas_diarias or 0
    horas_mes = empregado.horas_trabalhadas_mes or 0
    horas_total = empregado.horas_total or 0

    metros_hoje = empregado.metros_furados_hoje or 0
    metros_total = empregado.total_metros_furados or 0

    total_furos = empregado.total_furos_trabalhados or 0
    media_metros_hora = empregado.media_metros_por_hora or 0
    media_metros_dia = empregado.media_metros_por_dia or 0

    # -------- DADOS PARA GRÁFICOS --------
    registos_grafico = empregado.registos_diarios.order_by('data')

    labels = []
    metros_por_dia = []
    horas_por_dia = []
    produtividade_por_dia = []

    agregados = {}

    for registo in registos_grafico:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados:
            agregados[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados[chave]["metros"] += registo.metros_furados or 0
        agregados[chave]["horas"] += registo.horas_trabalhadas or 0

    for data_label, valores in agregados.items():
        labels.append(data_label)
        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = (metros / horas) if horas > 0 else 0

        metros_por_dia.append(round(metros, 2))
        horas_por_dia.append(round(horas, 2))
        produtividade_por_dia.append(round(produtividade, 2))

    return render(request, "projetos/area_empregado.html", {
        "empregado": empregado,
        "horas_hoje": horas_hoje,
        "horas_mes": horas_mes,
        "horas_total": horas_total,
        "metros_hoje": metros_hoje,
        "metros_total": metros_total,
        "total_furos": total_furos,
        "media_metros_hora": media_metros_hora,
        "media_metros_dia": media_metros_dia,
        "ultimos_registos": ultimos_registos,
        "grafico_labels": labels,
        "grafico_metros": metros_por_dia,
        "grafico_horas": horas_por_dia,
        "grafico_produtividade": produtividade_por_dia,
        "furos_trabalhados": furos_trabalhados,
    })


# --------- REDIRECT ------------
def redirect_after_login(request):
    if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
        return redirect('projetos:dashboard')

    if request.user.groups.filter(name='Empregados').exists():
        return redirect('projetos:area_empregado')

    return redirect('login')


# -------- REGISTOS --------------
@login_required
@empregado_required
def registo_diario_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            registo = form.save(commit=False)
            registo.empregado = empregado
            registo.save()

            # -------- EMPREGADO --------
            horas = registo.horas_trabalhadas or 0

            empregado.horas_total = (empregado.horas_total or 0) + horas

            hoje = registo.data
            inicio_mes = hoje.replace(day=1)

            horas_mes = empregado.registos_diarios.filter(
                data__gte=inicio_mes,
                data__lte=hoje
            ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

            horas_dia = empregado.registos_diarios.filter(
                data=hoje
            ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

            empregado.horas_trabalhadas_mes = horas_mes
            empregado.horas_diarias = horas_dia
            empregado.save(update_fields=[
                'horas_total',
                'horas_trabalhadas_mes',
                'horas_diarias',
            ])

            # -------- FURO --------
            if registo.furo:
                metros = registo.metros_furados or 0

                registo.furo.profundidade_atual = (registo.furo.profundidade_atual or 0) + metros

                if (registo.furo.profundidade_atual or 0) > (registo.furo.profundidade_final or 0):
                    registo.furo.profundidade_final = registo.furo.profundidade_atual

                registo.furo.save(update_fields=['profundidade_atual', 'profundidade_final'])

            messages.success(request, "Registo diário guardado com sucesso.")
            return redirect('projetos:area_empregado')
        else:
            messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")
    else:
        form = RegistoDiarioEmpregadoForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/registo_diario_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Novo Registo Diário"
    })


@login_required
@empregado_required
def registo_diario_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    registos = empregado.registos_diarios.all()

    return render(request, "projetos/registo_diario_list.html", {
        "empregado": empregado,
        "registos": registos
    })

@login_required
@empregado_required
def registo_diario_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(request.POST, request.FILES, empregado=empregado)
        if form.is_valid():
            registo = form.save(commit=False)
            registo.empregado = empregado
            registo.save()

            recalcular_resumo_empregado(empregado)

            if registo.furo:
                recalcular_resumo_furo(registo.furo)

            messages.success(request, "Registo diário guardado com sucesso.")
            return redirect('projetos:area_empregado')
        else:
            messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")
    else:
        form = RegistoDiarioEmpregadoForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/registo_diario_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Novo Registo Diário"
    })

@login_required
@empregado_required
def registo_diario_update(request, pk):
    empregado = get_object_or_404(Empregados, user=request.user)
    registo = get_object_or_404(RegistoDiarioEmpregado, pk=pk, empregado=empregado)

    furo_antigo = registo.furo

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            instance=registo,
            empregado=empregado
        )
        if form.is_valid():
            registo = form.save(commit=False)
            registo.editado_por_empregado = True
            registo.editado_em = timezone.now()
            registo.save()

            recalcular_resumo_empregado(empregado)

            if furo_antigo:
                recalcular_resumo_furo(furo_antigo)

            if registo.furo and registo.furo != furo_antigo:
                recalcular_resumo_furo(registo.furo)

            elif registo.furo:
                recalcular_resumo_furo(registo.furo)

            messages.success(request, "Registo diário atualizado com sucesso.")
            return redirect('projetos:registo_diario_list')
        else:
            messages.error(request, "Erro ao atualizar o registo diário.")
    else:
        form = RegistoDiarioEmpregadoForm(instance=registo, empregado=empregado)

    return render(request, "projetos/registo_diario_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Editar Registo Diário"
    })


@login_required
@admin_required
def registos_admin_list(request):
    registos = RegistoDiarioEmpregado.objects.select_related(
        'empregado', 'projeto', 'furo'
    ).all()

    empregado_id = request.GET.get('empregado')
    projeto_id = request.GET.get('projeto')
    furo_id = request.GET.get('furo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if empregado_id:
        registos = registos.filter(empregado_id=empregado_id)

    if projeto_id:
        registos = registos.filter(projeto_id=projeto_id)

    if furo_id:
        registos = registos.filter(furo_id=furo_id)

    if data_inicio:
        registos = registos.filter(data__gte=parse_date(data_inicio))

    if data_fim:
        registos = registos.filter(data__lte=parse_date(data_fim))

    totais = registos.aggregate(
        total_horas=Sum('horas_trabalhadas'),
        total_metros=Sum('metros_furados'),
        total_paragem=Sum('horas_paragem'),
    )

    empregados = Empregados.objects.all().order_by('nome')
    projetos = Projeto.objects.all().order_by('nome')
    furos = Furo.objects.all().order_by('nome')

    return render(request, "projetos/registos_admin_list.html", {
        "registos": registos,
        "empregados": empregados,
        "projetos": projetos,
        "furos": furos,
        "filtros": {
            "empregado": empregado_id or "",
            "projeto": projeto_id or "",
            "furo": furo_id or "",
            "data_inicio": data_inicio or "",
            "data_fim": data_fim or "",
        },
        "total_horas": totais['total_horas'] or 0,
        "total_metros": totais['total_metros'] or 0,
        "total_paragem": totais['total_paragem'] or 0,
    })


@login_required
@admin_required
def registo_admin_update(request, pk):
    registo = get_object_or_404(RegistoDiarioEmpregado, pk=pk)

    empregado_antigo = registo.empregado
    furo_antigo = registo.furo

    if request.method == "POST":
        form = RegistoDiarioEmpregadoAdminForm(
            request.POST,
            request.FILES,
            instance=registo
        )
        if form.is_valid():
            registo = form.save()

            recalcular_resumo_empregado(empregado_antigo)
            if registo.empregado != empregado_antigo:
                recalcular_resumo_empregado(registo.empregado)

            if furo_antigo:
                recalcular_resumo_furo(furo_antigo)
            if registo.furo and registo.furo != furo_antigo:
                recalcular_resumo_furo(registo.furo)
            elif registo.furo:
                recalcular_resumo_furo(registo.furo)

            messages.success(request, "Registo corrigido com sucesso.")
            return redirect('projetos:registos_admin_list')
        else:
            messages.error(request, "Erro ao corrigir o registo.")
    else:
        form = RegistoDiarioEmpregadoAdminForm(instance=registo)

    return render(request, "projetos/registo_admin_form.html", {
        "form": form,
        "registo": registo,
        "titulo": "Corrigir Registo de Produção"
    })


# ------ RECALCULAR RESUMO EMPREGADO ---- ####
def recalcular_resumo_empregado(empregado):
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    total_horas = empregado.registos_diarios.aggregate(
        total=Sum('horas_trabalhadas')
    )['total'] or 0

    horas_mes = empregado.registos_diarios.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    horas_hoje = empregado.registos_diarios.filter(
        data=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    total_metros = empregado.registos_diarios.aggregate(
        total=Sum('metros_furados')
    )['total'] or 0

    metros_mes = empregado.registos_diarios.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    metros_hoje = empregado.registos_diarios.filter(
        data=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    total_furos = empregado.registos_diarios.exclude(
        furo__isnull=True
    ).values('furo').distinct().count()

    total_dias_com_registo = empregado.registos_diarios.values('data').distinct().count()

    media_m_h = total_metros / total_horas if total_horas > 0 else 0
    media_m_d = total_metros / total_dias_com_registo if total_dias_com_registo > 0 else 0

    empregado.horas_total = total_horas
    empregado.horas_trabalhadas_mes = horas_mes
    empregado.horas_diarias = horas_hoje

    empregado.total_metros_furados = total_metros
    empregado.metros_furados_mes = metros_mes
    empregado.metros_furados_hoje = metros_hoje
    empregado.total_furos_trabalhados = total_furos
    empregado.media_metros_por_hora = round(media_m_h, 2)
    empregado.media_metros_por_dia = round(media_m_d, 2)

    empregado.save(update_fields=[
        'horas_total',
        'horas_trabalhadas_mes',
        'horas_diarias',
        'total_metros_furados',
        'metros_furados_mes',
        'metros_furados_hoje',
        'total_furos_trabalhados',
        'media_metros_por_hora',
        'media_metros_por_dia',
    ])


def recalcular_resumo_furo(furo):
    total_metros = furo.registos_empregados.aggregate(
        total=Sum('metros_furados')
    )['total'] or 0

    furo.profundidade_atual = total_metros
    furo.profundidade_final = total_metros

    furo.save(update_fields=[
        'profundidade_atual',
        'profundidade_final',
    ])

# ---------------- MATERIAIS ----------------
@login_required
@admin_required
def material_list(request):
    materiais = Material.objects.select_related('projeto', 'furo').all().order_by('nome')
    return render(request, 'projetos/material_list.html', {
        'materiais': materiais
    })


@login_required
@admin_required
def material_detail(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    devolucoes = material.devolucoes.select_related(
        'empregado', 'projeto', 'furo'
    ).all()
    levantamentos = material.levantamentos.select_related(
        'empregado', 'projeto', 'furo'
    ).all()

    return render(request, 'projetos/material_detail.html', {
        'material': material,
        'levantamentos': levantamentos,
        'devolucoes': devolucoes,
    })


@login_required
@admin_required
def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save()
            messages.success(request, "Material criado com sucesso.")
            return redirect('projetos:material_detail', material_id=material.id)
        else:
            messages.error(request, "Erro ao criar o material. Verifique os dados.")
    else:
        form = MaterialForm()

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Novo Material'
    })


@login_required
@admin_required
def material_update(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material atualizado com sucesso.")
            return redirect('projetos:material_detail', material_id=material.id)
        else:
            messages.error(request, "Erro ao atualizar o material. Verifique os dados.")
    else:
        form = MaterialForm(instance=material)

    return render(request, 'projetos/material_form.html', {
        'form': form,
        'titulo': 'Editar Material',
        'material': material
    })


@login_required
@admin_required
def material_delete(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        material.delete()
        messages.success(request, "Material apagado com sucesso.")
        return redirect('projetos:material_list')

    return render(request, 'projetos/material_confirm_delete.html', {
        'material': material
    })


# ------------ Levantamento Materiais ----------------- #

@login_required
@empregado_required
def levantamento_material_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = LevantamentoMaterialForm(request.POST, empregado=empregado)
        if form.is_valid():
            levantamento = form.save(commit=False)
            levantamento.empregado = empregado
            levantamento.save()

            material = levantamento.material
            material.quantidade = material.quantidade - levantamento.quantidade
            material.save(update_fields=['quantidade'])

            messages.success(request, "Levantamento de material registado com sucesso.")
            return redirect('projetos:levantamento_material_list')
        else:
            messages.error(request, "Erro ao registar o levantamento. Verifique os dados.")
    else:
        form = LevantamentoMaterialForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/levantamento_material_form.html", {
        "form": form,
        "titulo": "Levantar Material"
    })


@login_required
@empregado_required
def levantamento_material_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    levantamentos = empregado.levantamentos_materiais.select_related(
        'material', 'projeto', 'furo'
    ).all()

    return render(request, "projetos/levantamento_material_list.html", {
        "levantamentos": levantamentos
    })

@login_required
@admin_required
def levantamento_material_admin_list(request):
    levantamentos = LevantamentoMaterial.objects.select_related(
        'empregado', 'material', 'projeto', 'furo'
    ).all().order_by('-data', '-criado_em')

    empregado_id = request.GET.get('empregado')
    material_id = request.GET.get('material')
    projeto_id = request.GET.get('projeto')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if empregado_id:
        levantamentos = levantamentos.filter(empregado_id=empregado_id)

    if material_id:
        levantamentos = levantamentos.filter(material_id=material_id)

    if projeto_id:
        levantamentos = levantamentos.filter(projeto_id=projeto_id)

    if data_inicio:
        levantamentos = levantamentos.filter(data__gte=parse_date(data_inicio))

    if data_fim:
        levantamentos = levantamentos.filter(data__lte=parse_date(data_fim))

    empregados = Empregados.objects.all().order_by('nome')
    materiais = Material.objects.all().order_by('nome')
    projetos = Projeto.objects.all().order_by('nome')

    return render(request, "projetos/levantamento_material_admin_list.html", {
        "levantamentos": levantamentos,
        "empregados": empregados,
        "materiais": materiais,
        "projetos": projetos,
        "filtros": {
            "empregado": empregado_id or "",
            "material": material_id or "",
            "projeto": projeto_id or "",
            "data_inicio": data_inicio or "",
            "data_fim": data_fim or "",
        }
    })

# ----------- Devolução MAteriais -----------------------#

@login_required
@empregado_required
def devolucao_material_create(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = DevolucaoMaterialForm(request.POST, empregado=empregado)
        if form.is_valid():
            devolucao = form.save(commit=False)
            devolucao.empregado = empregado
            devolucao.save()

            material = devolucao.material
            material.quantidade = material.quantidade + devolucao.quantidade
            material.save(update_fields=['quantidade'])

            messages.success(request, "Devolução de material registada com sucesso.")
            return redirect('projetos:devolucao_material_list')
        else:
            messages.error(request, "Erro ao registar a devolução. Verifique os dados.")
    else:
        form = DevolucaoMaterialForm(
            empregado=empregado,
            initial={'data': timezone.now().date()}
        )

    return render(request, "projetos/devolucao_material_form.html", {
        "form": form,
        "titulo": "Devolver Material"
    })


@login_required
@empregado_required
def devolucao_material_list(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    devolucoes = empregado.devolucoes_materiais.select_related(
        'material', 'projeto', 'furo'
    ).all()

    return render(request, "projetos/devolucao_material_list.html", {
        "devolucoes": devolucoes
    })

@login_required
@admin_required
def devolucao_material_admin_list(request):
    devolucoes = DevolucaoMaterial.objects.select_related(
        'empregado', 'material', 'projeto', 'furo'
    ).all().order_by('-data', '-criado_em')

    return render(request, "projetos/devolucao_material_admin_list.html", {
        "devolucoes": devolucoes
    })


# ----------------- Globo ------------------------------ #
@login_required
@admin_required
def globo_projetos(request):
    projetos = Projeto.objects.exclude(
        localizacao_lat__isnull=True
    ).exclude(
        localizacao_lon__isnull=True
    )

    lats = [p.localizacao_lat for p in projetos]
    lons = [p.localizacao_lon for p in projetos]
    nomes = [p.nome for p in projetos]

    fig = go.Figure(data=[go.Scattergeo(
        lat=lats,
        lon=lons,
        text=nomes,
        mode='markers'
    )])

    graph = fig.to_html(full_html=False)

    return render(request, "projetos/globo.html", {"graph": graph})


#-------------- MEDICOAO -----------------------

# Listar medições
@login_required
@admin_required
def medicao_list(request):
    medicoes = Medicao.objects.all()
    return render(request, 'projetos/medicao_list.html', {'medicoes': medicoes})

# Criar medição (somente campos obrigatórios)
@login_required
@admin_required
def medicao_create(request, furo_id):
    furo = get_object_or_404(Furo, pk=furo_id)

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES, furo=furo)
        if form.is_valid():
            medicao = form.save(commit=False)
            medicao.furo = furo
            medicao.nome_furo = furo.nome

            if medicao.latitude is None:
                medicao.latitude = furo.latitude
            if medicao.longitude is None:
                medicao.longitude = furo.longitude
            if medicao.altitude is None:
                medicao.altitude = furo.altitude

            medicao.save()

            profundidade = medicao.profundidade or 0.0
            furo.profundidade_atual = profundidade

            if profundidade > (furo.profundidade_final or 0.0):
                furo.profundidade_final = profundidade

            if medicao.inclinacao is not None:
                furo.inclinacao = medicao.inclinacao
            if medicao.azimute is not None:
                furo.azimute = medicao.azimute
            if medicao.magnetismo is not None:
                furo.magnetismo = medicao.magnetismo

            furo.save()

            messages.success(request, "Medição criada com sucesso.")
            return redirect('projetos:furo_detail', pk=furo.pk)
        else:
            messages.error(request, "Erro ao criar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(furo=furo)

    return render(request, 'projetos/medicao_form.html', {
        'form': form,
        'titulo': f'Nova Medição - {furo.nome}',
        'furo': furo,
    })

# Editar medição (todos os campos)
@login_required
@admin_required
def medicao_update(request, pk):
    medicao = get_object_or_404(Medicao, pk=pk)

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES, instance=medicao, furo=medicao.furo)
        if form.is_valid():
            medicao = form.save()

            furo = medicao.furo
            furo.profundidade_atual = max(
                [m.profundidade or 0.0 for m in furo.medicoes.all()],
                default=0.0
            )
            furo.profundidade_final = furo.profundidade_atual

            if medicao.inclinacao is not None:
                furo.inclinacao = medicao.inclinacao
            if medicao.azimute is not None:
                furo.azimute = medicao.azimute
            if medicao.magnetismo is not None:
                furo.magnetismo = medicao.magnetismo

            furo.save()

            messages.success(request, "Medição atualizada com sucesso.")
            return redirect('projetos:medicao_list')
        else:
            messages.error(request, "Erro ao atualizar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(instance=medicao, furo=medicao.furo)

    return render(request, 'projetos/medicao_form.html', {
        'form': form,
        'titulo': f'Editar Medição #{medicao.id}',
        'furo': medicao.furo,
    })

# Apagar medição
@login_required
@admin_required
def medicao_delete(request, pk):
    medicao = get_object_or_404(Medicao, pk=pk)
    if request.method == "POST":
        medicao.delete()
        return redirect('projetos:medicao_list')
    return render(request, 'projetos/medicao_confirm_delete.html', {'medicao': medicao})

# ---------------- JSON ----------------
@login_required
@admin_required
def medicoes_json(request, furo_id):
    furo = get_object_or_404(Furo, id=furo_id)

    data = [
        {
            "profundidade": m.profundidade,
            "rocha": m.tipo_rocha,
            "dureza": m.dureza
        }
        for m in furo.medicoes.all()
    ]

    return JsonResponse(data, safe=False)


#--------- corversor de latitude e longitude -----------
def obter_coordenadas_por_cidade_pais(cidade, pais):
    if not cidade or not pais:
        return None, None

    query = f"{cidade}, {pais}"
    url = f"https://nominatim.openstreetmap.org/search?q={quote(query)}&format=json&limit=1"

    headers = {
        "User-Agent": "SistemaFuracao/1.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    except Exception as e:
        print("Erro ao obter coordenadas:", e)

    return None, None


# ----------- GRAFICOS ---------------------

@login_required
@admin_required
def graficos_dashboard(request):
    hoje = timezone.now().date()

    periodo = request.GET.get('periodo', '30_dias')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # -------- DEFINIR INTERVALO --------
    inicio = None
    fim = hoje

    if periodo == 'hoje':
        inicio = hoje
    elif periodo == '7_dias':
        inicio = hoje - timedelta(days=6)
    elif periodo == '30_dias':
        inicio = hoje - timedelta(days=29)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
    elif periodo == 'personalizado':
        inicio = parse_date(data_inicio) if data_inicio else None
        fim = parse_date(data_fim) if data_fim else hoje

    # -------- TOTAIS GERAIS --------
    total_projetos = Projeto.objects.count()
    total_furos = Furo.objects.count()
    total_empregados = Empregados.objects.count()
    total_maquinas = Maquina.objects.count()
    total_materiais = Material.objects.count()

    materiais_stock_baixo = Material.objects.filter(
        ativo=True,
        quantidade__lte=F('stock_minimo')
    ).order_by('quantidade')

    maquinas_alerta = Maquina.objects.filter(
        estado__in=['avariada', 'reparacao', 'parada']
    ).order_by('nome')

    # -------- REGISTOS FILTRADOS --------
    registos = RegistoDiarioEmpregado.objects.select_related(
        'empregado', 'projeto', 'furo'
    ).order_by('data')

    if inicio:
        registos = registos.filter(data__gte=inicio)
    if fim:
        registos = registos.filter(data__lte=fim)

    agregados_dia = OrderedDict()

    for registo in registos:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados_dia:
            agregados_dia[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados_dia[chave]["metros"] += registo.metros_furados or 0
        agregados_dia[chave]["horas"] += registo.horas_trabalhadas or 0

    labels_dia = []
    metros_dia = []
    horas_dia = []
    produtividade_dia = []

    for data_label, valores in agregados_dia.items():
        labels_dia.append(data_label)
        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = metros / horas if horas > 0 else 0

        metros_dia.append(round(metros, 2))
        horas_dia.append(round(horas, 2))
        produtividade_dia.append(round(produtividade, 2))

    # -------- TOP EMPREGADOS FILTRADOS --------
    empregados_stats = Empregados.objects.all()
    empregados_labels = []
    empregados_metros = []

    for empregado in empregados_stats:
        regs = empregado.registos_diarios.all()

        if inicio:
            regs = regs.filter(data__gte=inicio)
        if fim:
            regs = regs.filter(data__lte=fim)

        total = regs.aggregate(total=Sum('metros_furados'))['total'] or 0

        if total > 0:
            empregados_labels.append(empregado.nome)
            empregados_metros.append(round(total, 2))

    top_empregados = sorted(
        zip(empregados_labels, empregados_metros),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    labels_empregados = [x[0] for x in top_empregados]
    metros_empregados = [x[1] for x in top_empregados]

    # -------- TOP PROJETOS FILTRADOS --------
    projetos_stats = Projeto.objects.all()
    projetos_labels = []
    projetos_metros = []

    for projeto in projetos_stats:
        regs = projeto.registos_empregados.all()
        if inicio:
            regs = regs.filter(data__gte=inicio)
        if fim:
            regs = regs.filter(data__lte=fim)

        total = regs.aggregate(total=Sum('metros_furados'))['total'] or 0
        if total > 0:
            projetos_labels.append(projeto.nome)
            projetos_metros.append(round(total, 2))

    top_projetos = sorted(zip(projetos_labels, projetos_metros), key=lambda x: x[1], reverse=True)[:10]
    labels_projetos = [x[0] for x in top_projetos]
    metros_projetos = [x[1] for x in top_projetos]

    # -------- TOP FUROS FILTRADOS --------
    furos_stats = Furo.objects.all()
    furos_labels = []
    furos_metros = []

    for furo in furos_stats:
        regs = furo.registos_empregados.all()
        if inicio:
            regs = regs.filter(data__gte=inicio)
        if fim:
            regs = regs.filter(data__lte=fim)

        total = regs.aggregate(total=Sum('metros_furados'))['total'] or 0
        if total > 0:
            furos_labels.append(furo.nome)
            furos_metros.append(round(total, 2))

    top_furos = sorted(zip(furos_labels, furos_metros), key=lambda x: x[1], reverse=True)[:10]
    labels_furos = [x[0] for x in top_furos]
    metros_furos = [x[1] for x in top_furos]

    return render(request, "projetos/graficos_dashboard.html", {
        "total_projetos": total_projetos,
        "total_furos": total_furos,
        "total_empregados": total_empregados,
        "total_maquinas": total_maquinas,
        "total_materiais": total_materiais,

        "materiais_stock_baixo": materiais_stock_baixo,
        "maquinas_alerta": maquinas_alerta,

        "labels_dia": labels_dia,
        "metros_dia": metros_dia,
        "horas_dia": horas_dia,
        "produtividade_dia": produtividade_dia,

        "labels_empregados": labels_empregados,
        "metros_empregados": metros_empregados,

        "labels_projetos": labels_projetos,
        "metros_projetos": metros_projetos,

        "labels_furos": labels_furos,
        "metros_furos": metros_furos,

        "filtros": {
            "periodo": periodo,
            "data_inicio": data_inicio or "",
            "data_fim": data_fim or "",
        }
    })

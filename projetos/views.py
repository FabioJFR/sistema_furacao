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


# -------------- DASHBOARD ---------------
def dashboard(request):
    projetos = list(
        Projeto.objects.all().values(
            "id",
            "nome",
            "cidade",
            "pais",
            "status",
            "localizacao_lat",
            "localizacao_lon"
        )
    )

    context = {
        "total_projetos": Projeto.objects.count(),
        "total_furos": Furo.objects.count(),
        "total_maquinas": Maquina.objects.count(),
        "total_empregados": Empregados.objects.count(),
        "projetos": projetos,
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
def projeto_list(request):
    projetos_qs = Projeto.objects.all()
    projetos_serializaveis = list(projetos_qs.values(
        'id', 'pk', 'nome', 'cliente', 'cidade', 'pais', 'localizacao_lat', 'localizacao_lon'
    ))
    context = {'projetos': projetos_serializaveis}
    return render(request, 'projetos/projeto_list.html', context)

def projeto_detail(request, pk):  # ✅ usar pk
    projeto = get_object_or_404(Projeto, pk=pk)
    return render(request, "projetos/projeto_detail.html", {"projeto": projeto})


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


def projeto_delete(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)

    if request.method == "POST":
        projeto.delete()
        return redirect('projetos:projeto_list')

    return render(request, 'projetos/projeto_confirm_delete.html', {
        'projeto': projeto
    })


# ---------------- FUROS ----------------

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


def furo_detail(request, pk):
    furo = get_object_or_404(Furo, pk=pk)

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
    }
    return render(request, 'projetos/furo_detail.html', context)


def furo_list(request):
    furos = Furo.objects.all()
    return render(request, 'projetos/furo_list.html', {'furos': furos})

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

def furo_delete(request, pk):
    furo = get_object_or_404(Furo, pk=pk)
    if request.method == 'POST':
        furo.delete()
        return redirect('projetos:furo_list')
    return render(request, 'projetos/furo_confirm_delete.html', {'furo': furo})


# ---------------- 3D ----------------
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


def furo_3d_geologico(request, furo_id):
    furo = get_object_or_404(Furo, id=furo_id)
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
                len=0.6,        # 👈 altura (0 a 1)
                thickness=12,   # 👈 largura
                x=1.08,         # 👈 posição horizontal (mais à direita)
                y=0.45,         # 👈 posição vertical (baixa)
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


# ---------------- JSON ----------------
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


# ---------------- MAQUINAS ----------------
def maquina_list(request):
    return render(request, "projetos/maquina_list.html", {
        "maquinas": Maquina.objects.all()
    })


def maquina_detail(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    return render(request, "projetos/maquina_detail.html", {"maquina": maquina})



# Criar
def maquina_create(request):
    form = MaquinaCreateForm(request.POST or None)
    if form.is_valid():
        maquina = form.save()
        return redirect('projetos:maquina_detail', maquina_id=maquina.id)
    return render(request, 'projetos/maquina_form.html', {'form': form, 'titulo': 'Nova Máquina'})

# Editar
def maquina_update(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    form = MaquinaUpdateForm(request.POST or None, instance=maquina)
    if form.is_valid():
        form.save()
        return redirect('projetos:maquina_detail', maquina_id=maquina.id)
    return render(request, 'projetos/maquina_form.html', {'form': form, 'titulo': 'Editar Máquina'})

# Apagar
def maquina_delete(request, maquina_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    maquina.delete()
    return redirect('projetos:maquina_list')



# ---------------- EMPREGADOS ----------------
def empregado_list(request):
    empregados = Empregados.objects.all().order_by('nome')
    return render(request, "projetos/empregado_list.html", {
        "empregados": empregados
    })

def empregado_create(request):
    if request.method == "POST":
        form = EmpregadoCreateForm(request.POST, request.FILES)
        if form.is_valid():
            empregado = form.save()
            messages.success(request, "Empregado criado com sucesso.")
            return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao criar empregado. Verifique os dados.")
    else:
        form = EmpregadoCreateForm()

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Novo Empregado"
    })

def empregado_detail(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    return render(request, "projetos/empregado_detail.html", {
        "empregado": empregado
    })

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

def empregado_delete(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        empregado.delete()
        messages.success(request, "Empregado apagado com sucesso.")
        return redirect("projetos:empregado_list")

    return render(request, "projetos/empregado_confirm_delete.html", {
        "empregado": empregado
    })

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

# ---------------- MATERIAIS ----------------
def material_list(request):
    materiais = Material.objects.all()
    return render(request, 'projetos/material_list.html', {'materiais': materiais})

def material_create(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        valor = request.POST.get("valor")
        quantidade = request.POST.get("quantidade")

        Material.objects.create(
            nome=nome,
            valor=valor,
            quantidade=quantidade
        )
        return redirect('material_list')

    return render(request, "projetos/material_form.html", {
        "titulo": "Novo Material"
    })

def material_edit(request, pk):
    material = get_object_or_404(Material, pk=pk)
    return HttpResponse(f"Editar Material {pk} - em construção")

def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk)
    return HttpResponse(f"Deletar Material {pk} - em construção")



# ----------------- Globo ------------------------------ #
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
def medicao_list(request):
    medicoes = Medicao.objects.all()
    return render(request, 'projetos/medicao_list.html', {'medicoes': medicoes})

# Criar medição (somente campos obrigatórios)
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
def medicao_delete(request, pk):
    medicao = get_object_or_404(Medicao, pk=pk)
    if request.method == "POST":
        medicao.delete()
        return redirect('projetos:medicao_list')
    return render(request, 'projetos/medicao_confirm_delete.html', {'medicao': medicao})


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

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import Projeto, Furo, Empregados, Maquina, Material, Medicao
from .forms import *
import plotly.graph_objs as go
from plotly.offline import plot
from .utils import calcular_trajetoria_min_curv
from django.contrib import messages
import math


# -------------- DASHBOARD ---------------

def dashboard(request):
    context = {
        "total_projetos": Projeto.objects.count(),
        "total_furos": Furo.objects.count(),
        "total_medicoes": Medicao.objects.count(),
        "total_empregados": Empregados.objects.count(),
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
            form.save()
            return redirect('projetos:projeto_list')
    else:
        form = ProjetoForm()

    return render(request, 'projetos/projeto_form.html', {'form': form})


def projeto_update(request, pk):  # ✅ usar pk
    projeto = get_object_or_404(Projeto, pk=pk)
    form = ProjetoForm(request.POST or None, instance=projeto)

    if form.is_valid():
        form.save()
        return redirect("projetos:projeto_detail", pk=projeto.pk)  # ✅ corrigido

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
            form.save()
            return redirect('projetos:furo_list')
    else:
        form = FuroCreateForm()
    return render(request, 'projetos/form.html', {'form': form, 'titulo': 'Criar Novo Furo'})


def furo_detail(request, pk):
    furo = get_object_or_404(Furo, pk=pk)

    if request.method == "POST":
        form = MedicaoForm(request.POST, request.FILES)
        if form.is_valid():
            medicao = form.save(commit=False)
            medicao.furo = furo
            medicao.save()
            messages.success(request, "Medição registrada com sucesso!")
            return redirect('projetos:furo_detail', pk=furo.pk)
        else:
            messages.error(request, "Erro ao registrar medição. Verifique os dados.")
    else:
        form = MedicaoForm()

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
            form.save()
            return redirect('projetos:furo_detail', pk=furo.pk)
    else:
        form = FuroForm(instance=furo)

    return render(request, 'projetos/furo_update.html', {'form': form, 'furo': furo})

def furo_delete(request, pk):
    furo = get_object_or_404(Furo, pk=pk)
    if request.method == 'POST':
        furo.delete()
        return redirect('projetos:furo_list')
    return render(request, 'projetos/furo_confirm_delete.html', {'furo': furo})


# ---------------- 3D ----------------
def projeto_3d(request, projeto_id):
    projeto = get_object_or_404(Projeto, id=projeto_id)
    fig = go.Figure()

    for furo in projeto.furos.all():
        x = [m.profundidade for m in furo.medicoes.all()]
        y = [m.inclinacao for m in furo.medicoes.all()]
        z = [m.azimute for m in furo.medicoes.all()]

        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='lines+markers',
            name=furo.nome
        ))

    graph = plot(fig, output_type='div')
    return render(request, "projetos/projeto_3d.html", {
        "projeto": projeto,
        "graph": graph
    })


def furo_3d_geologico(request, furo_id):
    furo = get_object_or_404(Furo, id=furo_id)
    medicoes = list(furo.medicoes.all().order_by("profundidade"))

    profundidade_inicial = furo.profundidade_inicial or 0.0
    pontos, doglegs, alertas = calcular_trajetoria_min_curv(
        medicoes,
        profundidade_inicial=profundidade_inicial
    )

    x, y, z = [], [], []
    customdata = []

    total_pontos = min(len(pontos), len(medicoes))

    for i in range(total_pontos):
        x_coord, y_coord, z_coord = pontos[i]
        med = medicoes[i]

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

    # cones menos densos e menores
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

    scatter = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='lines+markers',
        line=dict(width=4, color='blue'),
        marker=dict(
            size=6,
            color=doglegs[:len(x)],
            colorscale=[
                [0, "green"],
                [0.5, "yellow"],
                [1, "red"]
            ],
            colorbar=dict(title='Dogleg (°/30m)'),
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
            width=12,
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
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, t=0, b=0),
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
    return render(request, "projetos/empregado_list.html", {
        "empregados": Empregados.objects.all()
    })


def empregado_create(request):
    form = EmpregadoCreateForm(request.POST or None)
    if form.is_valid():
        empregado = form.save()
        return redirect("projetos:empregado_detail", empregado_id=empregado.id)
    return render(request, "projetos/empregado_form.html", {"form": form, "titulo": "Novo Empregado"})



def empregado_detail(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    return render(request, "projetos/empregado_detail.html", {"empregado": empregado})


# Atualizar empregado
def empregado_update(request, empregado_id):
    empregado = get_object_or_404(Empregados, id=empregado_id)
    form = EmpregadoUpdateForm(request.POST or None, instance=empregado)
    if form.is_valid():
        form.save()
        return redirect("projetos:empregado_detail", empregado_id=empregado.id)
    return render(request, "projetos/empregado_form.html", {"form": form, "titulo": "Editar Empregado"})


# Apagar empregado
def empregado_delete(request, empregado_id):
    empregado = get_object_or_404(Empregados, id=empregado_id)
    if request.method == "POST":
        empregado.delete()
        return redirect("projetos:empregado_list")
    return render(request, "projetos/empregado_confirm_delete.html", {"empregado": empregado})


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
    projetos = Projeto.objects.all()

    lats = [p.localizacao_lat for p in projetos]
    lons = [p.localizacao_lon for p in projetos]
    nomes = [p.nome for p in projetos]

    import plotly.graph_objs as go

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
def medicao_create(request):
    if request.method == "POST":
        form = MedicaoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('projetos:medicao_list')
    else:
        form = MedicaoForm()
    return render(request, 'projetos/medicao_form.html', {'form': form, 'titulo': 'Criar Nova Medição'})

# Editar medição (todos os campos)
def medicao_update(request, pk):
    medicao = get_object_or_404(Medicao, pk=pk)
    if request.method == "POST":
        form = MedicaoForm(request.POST, instance=medicao)
        if form.is_valid():
            form.save()
            return redirect('projetos:medicao_list')
    else:
        form = MedicaoForm(instance=medicao)
    return render(request, 'projetos/medicao_form.html', {'form': form, 'titulo': f'Editar Medição #{medicao.id}'})

# Apagar medição
def medicao_delete(request, pk):
    medicao = get_object_or_404(Medicao, pk=pk)
    if request.method == "POST":
        medicao.delete()
        return redirect('projetos:medicao_list')
    return render(request, 'projetos/medicao_confirm_delete.html', {'medicao': medicao})

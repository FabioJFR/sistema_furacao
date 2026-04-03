import uuid
from django.db import models
from django.contrib.postgres.fields import JSONField  # Para PostgreSQL; se usar SQLite >=3.9, use models.JSONField


import uuid
from django.db import models

# ------------------------
# Projeto
# ------------------------
class Projeto(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    cliente = models.CharField(max_length=200, blank=True)

    # 🔥 localização (mantive ambos: cidade + coords)
    cidade = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    localizacao_lat = models.FloatField(null=True, blank=True)
    localizacao_lon = models.FloatField(null=True, blank=True)

    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    notas = models.TextField(blank=True)

    def __str__(self):
        return self.nome


# ------------------------
# Furo
# ------------------------
class Furo(models.Model):
    TIPO_CHOICES = [
        ('fundo', 'Fundo'),
        ('superficie', 'Superfície')
    ]

    ESTADO_CHOICES = [
        ('ativo', 'Ativo'),
        ('parado', 'Parado'),
        ('concluido', 'Concluído'),
        ('pausado', 'Pausado')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 🔥 RELAÇÃO CORRETA
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='furos'
    )

    nome = models.CharField(max_length=200, default="Furo")

    # 📏 profundidades
    profundidade_alvo = models.FloatField(default=0.0)
    profundidade_atual = models.FloatField(default=0.0)
    profundidade_final = models.FloatField(default=0.0)
    profundidade_inicial = models.FloatField(default=0.0)

    # 📐 orientação
    inclinacao = models.FloatField(default=0.0)
    azimute = models.FloatField(default=0.0)
    magnetismo = models.FloatField(default=0.0)

    # 🌍 localização
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    altitude = models.FloatField(null=True, blank=True)
    localizacao = models.CharField(max_length=200, blank=True)
    local_sondagem = models.CharField(max_length=200, blank=True)

    # 📊 estado
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='fundo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ativo')

    # 📄 info extra
    detalhes = models.TextField(blank=True)
    metros_furados = models.FloatField(default=0.0)

    # 🔥 JSONs (ok por agora)
    medicoes_json = models.JSONField(default=list, blank=True)
    relatorios = models.JSONField(default=list, blank=True)
    imagens = models.JSONField(default=list, blank=True)
    planeamento = models.JSONField(default=list, blank=True)
    ficheiros = models.JSONField(default=list, blank=True)
    trabalhadores = models.JSONField(default=list, blank=True)
    metros_furados_diario = models.JSONField(default=list, blank=True)

    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.projeto.nome}"
    

# ------------------------
# Empregado
# ------------------------
class Empregados(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='empregados')
    furos = models.ManyToManyField(Furo, blank=True, related_name='empregados')
    nome = models.CharField(max_length=200, blank=True, null=True)
    funcao = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, null=True)
    data_admissao = models.DateField(null=True, blank=True)
    numero = models.IntegerField(blank=True, null=True)
    data_inicio_contrato = models.DateField(blank=True, null=True)
    data_fim_contrato = models.DateField(blank=True, null=True)
    idade = models.IntegerField(blank=True, null=True)
    doc_id = models.BigIntegerField(blank=True, null=True)
    nib = models.CharField(max_length=50, blank=True, null=True)
    morada = models.CharField(max_length=200, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    nif = models.BigIntegerField(blank=True, null=True)
    curriculo = models.TextField(blank=True, null=True)
    contrato = models.TextField(blank=True, null=True)
    salario = models.FloatField(default=0.0)
    horas_diarias = models.IntegerField(default=0)
    horas_mensais = models.IntegerField(default=0)
    horas_extra = models.IntegerField(default=0)
    horas_trabalhadas_mes = models.IntegerField(default=0)
    projetos_ativos = models.JSONField(default=list, blank=True)  # lista de IDs de projetos
    alertas = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.nome


# ------------------------
# Maquina
# ------------------------
class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operacional', 'Operacional'),
        ('avariada', 'Avariada'),
        ('reparacao', 'Reparação'),
        ('sucata', 'Sucata'),
        ('parada', 'Parada')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projetos = models.ManyToManyField(Projeto, blank=True, related_name='maquinas')
    projeto_atual = models.CharField(max_length=20, null=True, blank=True)
    furos = models.ManyToManyField(Furo, blank=True, related_name='maquinas')
    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    data_compra = models.DateField(null=True, blank=True)
    data_registo = models.DateField(null=True, blank=True)
    data_revisao = models.DateField(null=True, blank=True)
    matricula = models.CharField(max_length=20, null=True, blank=True)
    seguro = models.CharField(max_length=200, blank=True)
    data_seguro = models.DateField(null=True, blank=True)
    data_iuc = models.DateField(null=True, blank=True)
    km = models.BigIntegerField(default=0)
    ano_registo = models.IntegerField(default=0)
    valor = models.FloatField(default=0.0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='operacional')
    despesas = models.JSONField(default=list, blank=True)  # imagens ou ficheiros

    def __str__(self):
        return self.nome


# ------------------------
# Material
# ------------------------
class Material(models.Model):
    ESTADO_CHOICES = [
        ('em_estoque', 'Em estoque'),
        ('sem_stock', 'Sem stock'),
        ('recebido', 'Recebido'),
        ('encomendado', 'Encomendado')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='materiais')
    furo = models.ForeignKey(Furo, on_delete=models.CASCADE, related_name='materiais', null=True, blank=True)
    nome = models.CharField(max_length=200)
    valor = models.FloatField(default=0.0)
    quantidade = models.IntegerField(default=0)
    diametro = models.FloatField(default=0.0)
    tipo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='em_estoque')
    data_compra = models.DateField(null=True, blank=True)
    faturas = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.nome


# ------------------------
# Medicao
# ------------------------
class Medicao(models.Model):
    furo = models.ForeignKey(Furo, on_delete=models.CASCADE, related_name="medicoes")
    imagem = models.ImageField(upload_to="rochas/", blank=True, null=True)
    profundidade = models.FloatField(blank=True, null=True)
    inclinacao = models.FloatField(blank=True, null=True)
    azimute = models.FloatField(blank=True, null=True)
    tipo_rocha = models.CharField(max_length=100, blank=True)
    cor = models.CharField(max_length=20, default="gray")
    dureza = models.FloatField(default=0)
    observacoes = models.TextField(blank=True)
    data = models.DateTimeField(auto_now_add=True)
    nome_furo = models.CharField(max_length=100, blank=True)
    magnetismo = models.FloatField(blank=True, null=True)
    altitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.furo.nome} - {self.profundidade}m"
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

# models.py


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
    SISTEMA_COORDENADAS_CHOICES = [
        ('local', 'Local'),
        ('utm', 'UTM'),
        ('wgs84', 'WGS84'),
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

    origem_este = models.FloatField(default=0.0)
    origem_norte = models.FloatField(default=0.0)
    origem_tvd = models.FloatField(default=0.0)

    # opcional (futuro)
    sistema_coordenadas = models.CharField(
        max_length=50,
        choices=SISTEMA_COORDENADAS_CHOICES,
        default='local'
    )

    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.projeto.nome}"
    

# ------------------------
# Empregado
# ------------------------
class Empregados(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empregado'
    )
    furos = models.ManyToManyField(Furo, blank=True, related_name='empregados')

    nome = models.CharField(max_length=200, blank=True, default="Empregado")
    funcao = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, null=True)
    data_admissao = models.DateField(null=True, blank=True)
    numero = models.IntegerField(blank=True, null=True)
    data_inicio_contrato = models.DateField(blank=True, null=True)
    data_fim_contrato = models.DateField(blank=True, null=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    idade = models.IntegerField(blank=True, null=True)
    doc_id = models.BigIntegerField(blank=True, null=True)
    nib = models.CharField(max_length=50, blank=True, null=True)
    morada = models.CharField(max_length=200, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    nif = models.BigIntegerField(blank=True, null=True)
    curriculo = models.FileField(upload_to='empregados/curriculos/', blank=True, null=True)
    contrato = models.FileField(upload_to='empregados/contratos/', blank=True, null=True)
    salario = models.FloatField(default=0.0)
    horas_diarias = models.IntegerField(default=0, blank=True)
    horas_mensais = models.IntegerField(default=0, blank=True)
    horas_extra = models.IntegerField(default=0, blank=True)
    horas_trabalhadas_mes = models.IntegerField(default=0, blank=True)
    horas_total = models.IntegerField(default=0, blank=True)
    alertas = models.JSONField(default=list, blank=True)
    total_metros_furados = models.FloatField(default=0.0)
    metros_furados_mes = models.FloatField(default=0.0)
    metros_furados_hoje = models.FloatField(default=0.0)
    total_furos_trabalhados = models.IntegerField(default=0)
    media_metros_por_hora = models.FloatField(default=0.0)
    media_metros_por_dia = models.FloatField(default=0.0)

    total_levantamentos = models.IntegerField(default=0)
    total_devolucoes = models.IntegerField(default=0)
    aprovado = models.BooleanField(default=False)
    data_registo = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome if self.nome else "Empregado sem nome"

    @property
    def projetos_atuais(self):
        return Projeto.objects.filter(
            empregado_projetos__empregado=self,
            empregado_projetos__ativo=True
        ).distinct()

    @property
    def projetos_historico(self):
        return Projeto.objects.filter(
            empregado_projetos__empregado=self
        ).distinct()
    

class EmpregadoProjeto(models.Model):
    empregado = models.ForeignKey(Empregados, on_delete=models.CASCADE, related_name='ligacoes_projetos')
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='empregado_projetos')

    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('empregado', 'projeto', 'data_inicio')
        ordering = ['-ativo', '-data_inicio']

    def __str__(self):
        return f"{self.empregado.nome} - {self.projeto.nome}"


class EmpregadoFicheiro(models.Model):
    TIPO_CHOICES = [
        ('foto', 'Foto'),
        ('bi', 'BI / Cartão de Cidadão'),
        ('nib', 'NIB / IBAN'),
        ('contrato', 'Contrato'),
        ('curriculo', 'Currículo'),
        ('outro', 'Outro'),
    ]

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='ficheiros'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro')
    titulo = models.CharField(max_length=200, blank=True, default="")
    ficheiro = models.FileField(upload_to='empregados/ficheiros/')
    data_upload = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.empregado.nome} - {self.get_tipo_display()}"


class RegistoDiarioEmpregado(models.Model):
    TIPO_PARAGEM_CHOICES = [
        ('', '---------'),
        ('cliente', 'Cliente'),
        ('empresa', 'Empresa'),
    ]

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='registos_diarios'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registos_empregados'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registos_empregados'
    )

    data = models.DateField(null=True, blank=True)

    hora_inicio = models.TimeField(null=True, blank=True)
    hora_inicio_pausa = models.TimeField(null=True, blank=True)
    hora_fim_pausa = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    horas_trabalhadas = models.FloatField(default=0.0)
    horas_paragem = models.FloatField(default=0.0)
    tipo_paragem = models.CharField(
        max_length=20,
        choices=TIPO_PARAGEM_CHOICES,
        blank=True,
        default=''
    )

    metros_furados = models.FloatField(default=0.0)
    observacoes = models.TextField(blank=True)

    relatorio_foto = models.ImageField(
        upload_to='registos_diarios/relatorios/',
        blank=True,
        null=True
    )

    editado_por_empregado = models.BooleanField(default=False)
    editado_em = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Registo Diário do Empregado"
        verbose_name_plural = "Registos Diários dos Empregados"

    def __str__(self):
        return f"{self.empregado.nome} - {self.data}"

    def clean(self):
        if self.furo and self.projeto and self.furo.projeto_id != self.projeto.id:
            raise ValidationError("O furo selecionado não pertence ao projeto escolhido.")

        if self.hora_inicio and self.hora_inicio_pausa and self.hora_inicio_pausa <= self.hora_inicio:
            raise ValidationError("A hora de início da pausa deve ser posterior à hora de início.")

        if self.hora_inicio_pausa and self.hora_fim_pausa and self.hora_fim_pausa <= self.hora_inicio_pausa:
            raise ValidationError("A hora de fim da pausa deve ser posterior à hora de início da pausa.")

        if self.hora_fim_pausa and self.hora_fim and self.hora_fim <= self.hora_fim_pausa:
            raise ValidationError("A hora de fim deve ser posterior à hora de fim da pausa.")

        if self.metros_furados is not None and self.metros_furados < 0:
            raise ValidationError("Os metros furados não podem ser negativos.")

        if self.horas_paragem is not None and self.horas_paragem < 0:
            raise ValidationError("As horas de paragem não podem ser negativas.")

    def calcular_horas_trabalhadas(self):
        if not all([self.data, self.hora_inicio, self.hora_inicio_pausa, self.hora_fim_pausa, self.hora_fim]):
            return 0

        dt_inicio = datetime.combine(self.data, self.hora_inicio)
        dt_inicio_pausa = datetime.combine(self.data, self.hora_inicio_pausa)
        dt_fim_pausa = datetime.combine(self.data, self.hora_fim_pausa)
        dt_fim = datetime.combine(self.data, self.hora_fim)

        periodo_total = (dt_fim - dt_inicio).total_seconds()
        pausa = (dt_fim_pausa - dt_inicio_pausa).total_seconds()

        # horas_paragem NÃO desconta nas horas trabalhadas
        horas = (periodo_total - pausa) / 3600
        return max(round(horas, 2), 0)

    def save(self, *args, **kwargs):
        self.horas_trabalhadas = self.calcular_horas_trabalhadas()
        super().save(*args, **kwargs)


# ------------------------
# Maquina
# ------------------------
class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operacional', 'Operacional'),
        ('avariada', 'Avariada'),
        ('reparacao', 'Reparação'),
        ('sucata', 'Sucata'),
        ('parada', 'Parada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    projetos = models.ManyToManyField(
        Projeto,
        blank=True,
        related_name='maquinas'
    )
    projeto_atual = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maquinas_atuais'
    )

    furos = models.ManyToManyField(
        Furo,
        blank=True,
        related_name='maquinas'
    )

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)

    data_compra = models.DateField(null=True, blank=True)
    data_registo = models.DateField(null=True, blank=True)
    data_revisao = models.DateField(null=True, blank=True)

    matricula = models.CharField(max_length=20, null=True, blank=True)
    seguro = models.CharField(max_length=200, blank=True)
    data_seguro = models.DateField(null=True, blank=True)
    data_iuc = models.DateField(null=True, blank=True)

    km = models.BigIntegerField(default=0, blank=True)
    horimetro = models.FloatField(default=0.0, blank=True)
    ano_registo = models.IntegerField(default=0, blank=True)
    valor = models.FloatField(default=0.0, blank=True)

    localizacao_atual = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='operacional'
    )

    ativo = models.BooleanField(default=True)

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
        ('encomendado', 'Encomendado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materiais'
    )

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    stock_minimo = models.IntegerField(default=5)
    quantidade = models.IntegerField(default=0)
    unidade = models.CharField(max_length=50, blank=True, default='un')
    diametro = models.FloatField(default=0.0, blank=True)

    valor = models.FloatField(default=0.0)
    fornecedor = models.CharField(max_length=200, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='em_estoque'
    )

    localizacao = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    data_compra = models.DateField(null=True, blank=True)

    ativo = models.BooleanField(default=True)

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
    

###############################
##### DESPESAS ###########
####################
class Despesa(models.Model):
    TIPO_CHOICES = [
        ('maquina', 'Máquina'),
        ('projeto', 'Projeto'),
        ('furo', 'Furo'),
        ('geral', 'Geral'),
    ]
    CATEGORIA_CHOICES = [
        ('combustivel', 'Combustível'),
        ('manutencao', 'Manutenção'),
        ('pecas', 'Peças'),
        ('salarios', 'Salários'),
        ('outros', 'Outros'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    maquina = models.ForeignKey(
        'Maquina',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    projeto = models.ForeignKey(
        'Projeto',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    furo = models.ForeignKey(
        'Furo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    descricao = models.CharField(max_length=255)
    valor = models.FloatField(default=0.0)

    data = models.DateField()
    observacoes = models.TextField(blank=True)

    comprovativo = models.FileField(
        upload_to='despesas/comprovativos/',
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descricao} - {self.valor}€"
    
    def clean(self):
        ligados = [self.maquina, self.projeto, self.furo]
        preenchidos = [x for x in ligados if x]

        if len(preenchidos) > 1:
            raise ValidationError("A despesa deve estar associada a apenas um: máquina, projeto ou furo.")

        if len(preenchidos) == 0:
            raise ValidationError("A despesa deve estar associada a pelo menos um elemento.")
        


##################################
######### LEVANTAMENTO MATERIAL ##
##################################
class LevantamentoMaterial(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='levantamentos_materiais'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='levantamentos'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )

    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Levantamento de Material"
        verbose_name_plural = "Levantamentos de Materiais"

    def __str__(self):
        return f"{self.empregado.nome} - {self.material.nome} ({self.quantidade})"
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='levantamentos_materiais'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='levantamentos'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='levantamentos_materiais'
    )

    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.empregado.nome} - {self.material.nome} ({self.quantidade})"



####################################
##### DEVOLUÇÂO DE MATERIAL ########
####################################
class DevolucaoMaterial(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name='devolucoes_materiais'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='devolucoes'
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devolucoes_materiais'
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devolucoes_materiais'
    )

    quantidade = models.IntegerField(default=1)
    data = models.DateField()
    observacoes = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Devolução de Material"
        verbose_name_plural = "Devoluções de Materiais"

    def __str__(self):
        return f"{self.empregado.nome} devolveu {self.quantidade} x {self.material.nome}"
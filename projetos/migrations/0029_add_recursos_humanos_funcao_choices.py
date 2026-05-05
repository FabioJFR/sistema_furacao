from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projetos", "0028_salariobasefuncao"),
    ]

    operations = [
        migrations.AlterField(
            model_name="empregados",
            name="funcao",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Perfurador1a", "Perfurador 1ª"),
                    ("Perfurador2a", "Perfurador 2ª"),
                    ("Perfurador3a", "Perfurador 3ª"),
                    ("ajudante_perfurador1", "Ajudante de Perfurador 1"),
                    ("ajudante_perfurador2", "Ajudante de Perfurador 2"),
                    ("ajudante_perfurador", "Ajudante de Perfurador"),
                    ("mecanico", "Mecânico"),
                    ("ajudante_mecanico", "Ajudante Mecânico"),
                    ("recursos_humanos", "Recursos Humanos"),
                    ("administrador", "Administrador"),
                    ("encarregado_obra", "Encarregado de Obra"),
                    ("chefe_turno", "Chefe de Turno"),
                    ("geologo", "Geólogo"),
                    ("operador_raiseboaring_1a", "Operador RaiseBoaring 1ª"),
                    ("operador_raiseboaring_2a", "Operador RaiseBoaring 2ª"),
                    ("operador_raiseboaring_3a", "Operador RaiseBoaring 3ª"),
                    ("ajudante_operador_raiseboaring_1a", "Ajudante Operador Raiseboaring 1ª"),
                    ("ajudante_operador_raiseboaring_2a", "Ajudante Operador Raiseboaring 2ª"),
                    ("ajudante_operador_raiseboaring_3a", "Ajudante Operador Raiseboaring 3ª"),
                    ("supervisor", "Supervisor"),
                    ("tecnico_seguranca", "Técnico de Segurança"),
                    ("almoxarife", "Almoxarife"),
                    ("manobrador", "Manobrador"),
                    ("outro", "Outro"),
                ],
                max_length=100,
                null=True,
                verbose_name="Função",
            ),
        ),
        migrations.AlterField(
            model_name="empregadofuro",
            name="funcao",
            field=models.CharField(
                choices=[
                    ("sondador", "Sondador"),
                    ("sondador_1", "Sondador 1ª"),
                    ("sondador_2", "Sondador 2ª"),
                    ("sondador_3", "Sondador 3ª"),
                    ("ajudante_sondador", "Ajudante de Sondador"),
                    ("ajudante_sondador_1", "Ajudante Sondador 1ª"),
                    ("ajudante_sondador_2", "Ajudante Sondador 2ª"),
                    ("ajudante_sondador_3", "Ajudante Sondador 3ª"),
                    ("mecanico", "Mecânico"),
                    ("ajudante_mecanico", "Ajudante Mecânico"),
                    ("recursos_humanos", "Recursos Humanos"),
                    ("administrador", "Administrador"),
                    ("encarregado_obra", "Encarregado de Obra"),
                    ("chefe_turno", "Chefe de Turno"),
                    ("geologo", "Geólogo"),
                    ("operador_raiseboaring_1a", "Operador RaiseBoaring 1ª"),
                    ("operador_raiseboaring_2a", "Operador RaiseBoaring 2ª"),
                    ("operador_raiseboaring_3a", "Operador RaiseBoaring 3ª"),
                    ("ajudante_operador_raiseboaring_1a", "Ajudante Operador Raiseboaring 1ª"),
                    ("ajudante_operador_raiseboaring_2a", "Ajudante Operador Raiseboaring 2ª"),
                    ("ajudante_operador_raiseboaring_3a", "Ajudante Operador Raiseboaring 3ª"),
                    ("supervisor", "Supervisor"),
                    ("fiscal_cliente", "Fiscal do Cliente"),
                    ("tecnico_seguranca", "Técnico de Segurança"),
                    ("almoxarife", "Almoxarife"),
                    ("manobrador", "Manobrador"),
                    ("outro", "Outro"),
                ],
                default="ajudante_sondador",
                max_length=50,
            ),
        ),
    ]


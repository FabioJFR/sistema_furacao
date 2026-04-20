from projetos.models import Furo

def executar():
    erros = []

    for obj in Furo.objects.select_related("projeto", "empresa"):
        if obj.projeto_id and obj.projeto and obj.projeto.empresa_id != obj.empresa_id:
            erros.append(
                f"Furo inconsistente: furo={obj.nome} "
                f"(empresa={obj.empresa_id}) / projeto={obj.projeto.nome} "
                f"(empresa={obj.projeto.empresa_id})"
            )

    print("Total:", len(erros))
    for erro in erros:
        print("-", erro)
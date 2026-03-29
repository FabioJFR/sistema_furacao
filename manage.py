from core.app import app
import core.routes

# Importar callbacks
import projetos.novo_callbacks
import projetos.listar_callbacks
import furos.novo_callbacks
import furos.listar_callbacks
import maquinas.novo_callbacks
import maquinas.listar_callbacks
import empregados.novo_callbacks
import empregados.listar_callbacks
import materiais.novo_callbacks
import materiais.listar_callbacks

if __name__ == "__main__":
    app.run_server(debug=True)
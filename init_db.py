from db.database import criar_tabelas, atualizar_colunas_furos

if __name__ == "__main__":
    criar_tabelas()
    atualizar_colunas_furos()
    print("Base de dados inicializada e colunas verificadas com sucesso!")
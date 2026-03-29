# db/database.py
import sqlite3
import os

DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "app.db")

# Cria a pasta database se não existir
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def get_connection():
    """Retorna uma conexão com o SQLite"""
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    """Cria todas as tabelas principais do projeto se não existirem"""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de projetos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            data_criacao TEXT
        )
    """)

    # Tabela de furos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS furos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER,
            nome TEXT,
            profundidade REAL,
            profundidade_alvo REAL,
            inc REAL,
            azi REAL,
            lat REAL,
            lon REAL,
            FOREIGN KEY(projeto_id) REFERENCES projetos(id)
        )
    """)

    # Tabela de medições (exemplo inicial, pode expandir)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furo_id INTEGER,
            profundidade REAL,
            valor REAL,
            timestamp TEXT,
            FOREIGN KEY(furo_id) REFERENCES furos(id)
        )
    """)

    conn.commit()
    conn.close()

def adicionar_coluna_se_nao_existe(tabela, coluna, tipo):
    """Adiciona coluna à tabela se não existir"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [info[1] for info in cursor.fetchall()]
    if coluna not in colunas_existentes:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        conn.commit()
    conn.close()

def atualizar_colunas():
    """Garante que todas as colunas necessárias existem (furos, medicoes, etc)"""
    colunas_furos = {
        "projeto_id": "INTEGER",
        "nome": "TEXT",
        "profundidade": "REAL",
        "profundidade_alvo": "REAL",
        "inc": "REAL",
        "azi": "REAL",
        "lat": "REAL",
        "lon": "REAL"
    }
    for coluna, tipo in colunas_furos.items():
        adicionar_coluna_se_nao_existe("furos", coluna, tipo)

    colunas_medicoes = {
        "furo_id": "INTEGER",
        "profundidade": "REAL",
        "valor": "REAL",
        "timestamp": "TEXT"
    }
    for coluna, tipo in colunas_medicoes.items():
        adicionar_coluna_se_nao_existe("medicoes", coluna, tipo)

# Inicialização automática
criar_tabelas()
atualizar_colunas()

def init_db():
    """Função padrão para inicializar a base de dados"""
    criar_tabelas()
    atualizar_colunas()
# CREATE
# furos/services.py
import uuid
import sqlite3
from db.database import get_connection
from furos.models import Furo
from datetime import datetime

def criar_furo(furo: Furo):
    """Cria um novo furo no banco de dados com os campos obrigatórios preenchidos."""
    conn = get_connection()
    cursor = conn.cursor()

    # Criação da tabela se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS furos (
            id TEXT PRIMARY KEY,
            projeto TEXT NOT NULL,
            nome TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            local_sondagem TEXT NOT NULL,
            inclinacao REAL NOT NULL,
            azimute REAL NOT NULL,
            profundidade_alvo REAL NOT NULL,
            profundidade_atual REAL DEFAULT 0.0,
            estado TEXT DEFAULT 'ativo'
        )
    """)

    cursor.execute("""
        INSERT INTO furos (
            id, projeto, nome, lat, lon, local_sondagem, inclinacao, azimute, profundidade_alvo, profundidade_atual, estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        furo._id,
        furo.projeto,
        furo._nome,
        furo._localizacao[0],
        furo._localizacao[1],
        furo.local_sondagem,
        furo._inclinacao,
        furo._azimute,
        furo._profundidade_alvo,
        furo._profundidade_atual,
        furo._estado
    ))

    conn.commit()
    conn.close()

# READ
def listar_furos(projeto):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM furos WHERE projeto = ?", (projeto,))
    rows = cursor.fetchall()
    furos = []
    for r in rows:
        f = Furo(
            id=r["id"],
            nome=r["nome"],
            localizacao=(r["localizacao_lat"], r["localizacao_lon"]),
            estado=r["estado"],
            profundidade_alvo=r["profundidade_alvo"]
        )
        f._profundidade_final = r["profundidade_final"]
        f._profundidade_atual = r["profundidade_atual"]
        f._metros_furados = r["metros_furados"]
        furos.append(f)
    conn.close()
    return furos

# UPDATE
def atualizar_profundidade(furo_id, profundidade_atual, metros_diario):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE furos
    SET profundidade_atual = ?, metros_furados = ?
    WHERE id = ?
    """, (profundidade_atual, metros_diario, furo_id))
    
    cursor.execute("""
    INSERT INTO furos_diario (furo_id, data, metros_furados)
    VALUES (?, ?, ?)
    """, (furo_id, datetime.now().strftime("%Y-%m-%d"), metros_diario))

    conn.commit()
    conn.close()

# DELETE
def deletar_furo(furo_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM furos WHERE id = ?", (furo_id,))
    cursor.execute("DELETE FROM furos_diario WHERE furo_id = ?", (furo_id,))
    conn.commit()
    conn.close()
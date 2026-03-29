import uuid
from db.database import get_connection

def criar_projeto(nome, cliente, lat, lon):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO projetos (id, nome, cliente, lat, lon)
        VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), nome, cliente, lat, lon))

    conn.commit()
    conn.close()


def listar_projetos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome, cliente, lat, lon FROM projetos")
    rows = cursor.fetchall()

    conn.close()

    return rows


def obter_projeto(proj_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, cliente, lat, lon
        FROM projetos WHERE id=?
    """, (proj_id,))

    row = cursor.fetchone()
    conn.close()

    return row
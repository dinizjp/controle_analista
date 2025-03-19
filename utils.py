# utils.py
import streamlit as st
import psycopg2
import pandas as pd
import datetime as dt

# Função para obter conexão com o banco de dados
def get_db_connection():
    conn = psycopg2.connect(
        host=st.secrets["connections"]["postgresql"]["host"],
        port=st.secrets["connections"]["postgresql"].get("port", "5432"),
        database=st.secrets["connections"]["postgresql"]["database"],
        user=st.secrets["connections"]["postgresql"]["username"],
        password=st.secrets["connections"]["postgresql"]["password"]
    )
    return conn

# Função para buscar lista de lojas (com cache)
@st.cache_data(ttl=600)  # Cache por 10 minutos
def get_lojas():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM lojas ORDER BY nome")
            lojas = cursor.fetchall()
    return lojas

# Função para buscar lista de produtos (com cache)
@st.cache_data(ttl=600)
def get_produtos():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome, categoria, unidade_medida, valor 
                FROM produtos 
                ORDER BY nome
            """)
            produtos = cursor.fetchall()
    return produtos

# Função para buscar estoque de uma loja específica
def get_estoque_loja(loja_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT e.produto_id, p.nome, e.quantidade
                FROM estoque e
                JOIN produtos p ON e.produto_id = p.id
                WHERE e.loja_id = %s
            """
            cursor.execute(query, (loja_id,))
            estoque = cursor.fetchall()
    return estoque

# Função para buscar estoque geral ou filtrado por loja
def get_estoque_all(loja_id=None):
    query = """
        SELECT e.loja_id, p.id AS produto_id, p.nome, e.quantidade, e.data_atualizacao 
        FROM estoque e
        JOIN produtos p ON e.produto_id = p.id
    """
    params = []
    if loja_id and loja_id != "Todas":
        query += " WHERE e.loja_id = %s"
        params.append(loja_id)
    query += " ORDER BY p.nome"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    if not df.empty:
        df['produto_id'] = df['produto_id'].astype(int)
        df['loja_id'] = df['loja_id'].astype(int)
    return df

# Função para buscar movimentações de estoque
def get_movimentacoes(loja_id, start_date, end_date):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT id, tipo, produto_id, loja_id, quantidade, data, motivo 
        FROM movimentacoes_estoque
        WHERE data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id != "Todas":
        query += " AND loja_id = %s"
        params.append(loja_id)
    query += " ORDER BY data"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    if not df.empty:
        df['produto_id'] = df['produto_id'].astype(int)
        df['loja_id'] = df['loja_id'].astype(int)
    return df

# Função para adicionar nova loja
def add_loja(nome):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO lojas (nome) VALUES (%s)", (nome,))
        conn.commit()

# Função para atualizar nome de uma loja
def update_loja(loja_id, novo_nome):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE lojas SET nome = %s WHERE id = %s", (novo_nome, loja_id))
        conn.commit()

# Funções para correções de estoque
def corrigir_acrescentar(loja_id, produto_id, quantidade, observacao=""):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (loja_id, produto_id)
                DO UPDATE SET quantidade = estoque.quantidade + %s, data_atualizacao = CURRENT_TIMESTAMP
            """, (loja_id, produto_id, quantidade, quantidade))
            motivo = "Manutenção: Acrescentar"
            if observacao.strip():
                motivo += f" ({observacao.strip()})"
            cursor.execute("""
                INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                VALUES ('entrada', %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (produto_id, loja_id, quantidade, motivo))
        conn.commit()

def corrigir_remover(loja_id, produto_id, quantidade, observacao=""):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s, %s, -%s, CURRENT_TIMESTAMP)
                ON CONFLICT (loja_id, produto_id)
                DO UPDATE SET quantidade = estoque.quantidade - %s, data_atualizacao = CURRENT_TIMESTAMP
            """, (loja_id, produto_id, quantidade, quantidade))
            motivo = "Manutenção: Remover"
            if observacao.strip():
                motivo += f" ({observacao.strip()})"
            cursor.execute("""
                INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                VALUES ('saida', %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (produto_id, loja_id, quantidade, motivo))
        conn.commit()

def corrigir_transferir(loja_origem, loja_destino, produto_id, quantidade):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s, %s, -%s, CURRENT_TIMESTAMP)
                ON CONFLICT (loja_id, produto_id)
                DO UPDATE SET quantidade = estoque.quantidade - %s, data_atualizacao = CURRENT_TIMESTAMP
            """, (loja_origem, produto_id, quantidade, quantidade))
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (loja_id, produto_id)
                DO UPDATE SET quantidade = estoque.quantidade + %s, data_atualizacao = CURRENT_TIMESTAMP
            """, (loja_destino, produto_id, quantidade, quantidade))
            motivo_saida = f"Manutenção: Transferência (saída para loja {loja_destino})"
            motivo_entrada = f"Manutenção: Transferência (entrada recebida da loja {loja_origem})"
            cursor.execute("""
                INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                VALUES ('saida', %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (produto_id, loja_origem, quantidade, motivo_saida))
            cursor.execute("""
                INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                VALUES ('entrada', %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (produto_id, loja_destino, quantidade, motivo_entrada))
        conn.commit()

# Função para registrar entrada via XML
import datetime as dt  # Certifique-se de que isso está no topo do arquivo

def registrar_entrada_xml(loja_id, itens):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for item in itens:
                try:
                    produto_id = int(item['id'])
                except Exception:
                    produto_id = item['id']
                try:
                    quantidade = int(float(item['quantidade']))
                except Exception:
                    quantidade = 0
                motivo = item['motivo'] if item['motivo'] else "Entrada via XML"
                data_entry = item.get("data")
                if isinstance(data_entry, dt.datetime):  # Correção aplicada aqui
                    pass
                elif isinstance(data_entry, str) and data_entry.strip():
                    try:
                        data_entry = dt.datetime.fromisoformat(data_entry)
                    except Exception:
                        data_entry = dt.datetime.now()
                else:
                    data_entry = dt.datetime.now()
                cursor.execute("""
                    INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                    VALUES ('entrada', %s, %s, %s, %s, %s)
                """, (produto_id, loja_id, quantidade, motivo, data_entry))
                cursor.execute("""
                    INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (loja_id, produto_id)
                    DO UPDATE SET quantidade = estoque.quantidade + %s, data_atualizacao = CURRENT_TIMESTAMP
                """, (loja_id, produto_id, quantidade, quantidade))
        conn.commit()
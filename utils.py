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
@st.cache_data(ttl=600)
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

# Função para buscar categorias únicas
@st.cache_data(ttl=600)
def get_categorias():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT categoria FROM produtos ORDER BY categoria")
            categorias = cursor.fetchall()
    return [cat[0] for cat in categorias]

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
        SELECT e.loja_id, p.id AS produto_id, p.nome, e.quantidade, e.data_atualizacao, e.data_contagem
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

# Função para buscar saídas no período (otimizada para uma única consulta)
def get_saidas_periodo(start_date, end_date, loja_id):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT m.produto_id, DATE(m.data) AS dia, SUM(m.quantidade) AS total_saidas
        FROM movimentacoes_estoque m
        WHERE m.tipo = 'saida' AND m.data BETWEEN %s AND %s AND m.loja_id = %s
        GROUP BY m.produto_id, DATE(m.data)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (start_datetime, end_datetime, loja_id))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    return df

# Função para calcular o estoque em uma data específica usando data_contagem
def get_estoque_at_date(date, loja_id=None):
    date = dt.datetime.combine(date, dt.time.max)
    query = """
        SELECT e.produto_id, p.nome, e.quantidade, e.data_contagem,
               COALESCE(SUM(CASE WHEN m.tipo = 'entrada' THEN m.quantidade ELSE 0 END), 0) -
               COALESCE(SUM(CASE WHEN m.tipo = 'saida' THEN m.quantidade ELSE 0 END), 0) AS ajuste_movimentacoes
        FROM estoque e
        JOIN produtos p ON e.produto_id = p.id
        LEFT JOIN movimentacoes_estoque m ON e.produto_id = m.produto_id 
            AND m.loja_id = e.loja_id 
            AND m.data > COALESCE(e.data_contagem, e.data_atualizacao) 
            AND m.data <= %s
    """
    params = [date]
    if loja_id and loja_id != "Todas":
        query += " WHERE e.loja_id = %s"
        params.append(loja_id)
    else:
        query += " WHERE 1=1"
    query += " GROUP BY e.produto_id, p.nome, e.quantidade, e.data_contagem"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    df['quantidade_ajustada'] = df['quantidade'] + df['ajuste_movimentacoes']
    return df[['produto_id', 'nome', 'quantidade_ajustada']]

# Função para buscar compras no período
def get_compras_periodo(start_date, end_date, loja_id=None):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT m.produto_id, SUM(m.quantidade) as total_compras
        FROM movimentacoes_estoque m
        WHERE m.tipo = 'entrada' AND m.data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id and loja_id != "Todas":
        query += " AND m.loja_id = %s"
        params.append(loja_id)
    query += " GROUP BY m.produto_id"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
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
                if isinstance(data_entry, dt.datetime):
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

# Função para registrar contagem de inventário com data específica
def registrar_contagem(loja_id, produto_id, quantidade, data_contagem=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            data_contagem = data_contagem if data_contagem else dt.datetime.now()
            cursor.execute("""
                INSERT INTO movimentacoes_estoque (tipo, produto_id, loja_id, quantidade, motivo, data)
                VALUES ('ajuste', %s, %s, %s, 'Contagem de Inventário', %s)
            """, (produto_id, loja_id, quantidade, data_contagem))
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao, data_contagem)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (loja_id, produto_id)
                DO UPDATE SET quantidade = %s, data_atualizacao = %s, data_contagem = %s
            """, (loja_id, produto_id, quantidade, data_contagem, data_contagem, quantidade, data_contagem, data_contagem))
        conn.commit()

def get_movimentacoes(loja_id, start_date, end_date):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT m.id, m.tipo, m.produto_id, m.loja_id, m.quantidade, m.data, m.motivo, p.nome
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id != "Todas":
        query += " AND m.loja_id = %s"
        params.append(loja_id)
    query += " ORDER BY m.data"
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

# Função para buscar entradas e saídas no período
def get_entradas_saidas(start_date, end_date, loja_id=None, categoria=None):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT p.nome, m.tipo, SUM(m.quantidade) as total
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id and loja_id != "Todas":
        query += " AND m.loja_id = %s"
        params.append(loja_id)
    if categoria and categoria != "Todas":
        query += " AND p.categoria = %s"
        params.append(categoria)
    query += " GROUP BY p.nome, m.tipo ORDER BY p.nome, m.tipo"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    if not df.empty:
        df['total'] = df['total'].astype(int)
    return df
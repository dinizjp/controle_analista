# utils.py
import streamlit as st
import psycopg2
import pandas as pd
import datetime as dt
import math
from dateutil.relativedelta import relativedelta


CONVERSION_FACTORS = {
    586:  2,
    447: 25, 446: 25, 448: 25, 1217: 25,
    1856: 24, 3233: 24,
    1243: 25, 449: 25,
    3248:  6, 3250:  6
}

# ——————————————
# Conexão
# ——————————————
def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["connections"]["postgresql"]["host"],
        port=st.secrets["connections"]["postgresql"].get("port", "5432"),
        database=st.secrets["connections"]["postgresql"]["database"],
        user=st.secrets["connections"]["postgresql"]["username"],
        password=st.secrets["connections"]["postgresql"]["password"]
    )

# ——————————————
# Lojas, Produtos, Categorias
# ——————————————
@st.cache_data(ttl=600)
def get_lojas():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM lojas ORDER BY id")
            return cursor.fetchall()

@st.cache_data(ttl=600)
def get_produtos():
    """
    Retorna DataFrame com colunas:
    produto_id, nome, categoria, un_saida, un_entrada, conversao
    """
    sql = """
        SELECT id    AS produto_id,
               nome,
               categoria,
               un_saida,
               un_entrada,
               conversao
          FROM produtos
    """
    with get_db_connection() as conn:
        return pd.read_sql(sql, conn)

def add_loja(loja_id: int, nome: str):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO lojas (id, nome) VALUES (%s, %s)",
                (loja_id, nome)
            )
        conn.commit()

def update_loja(loja_id: int, novo_nome: str):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE lojas SET nome = %s WHERE id = %s",
                (novo_nome, loja_id)
            )
        conn.commit()

# ——————————————
# Estoque por loja e geral
# ——————————————
def get_estoque_loja(loja_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.produto_id, p.nome, e.quantidade
                  FROM estoque e
                  JOIN produtos p ON e.produto_id = p.id
                 WHERE e.loja_id = %s
                """,
                (loja_id,)
            )
            return cursor.fetchall()

def get_estoque_all(loja_id=None) -> pd.DataFrame:
    sql = """
        SELECT e.loja_id,
               p.id   AS produto_id,
               p.nome,
               e.quantidade,
               e.data_atualizacao,
               e.data_contagem
          FROM estoque e
          JOIN produtos p ON e.produto_id = p.id
    """
    params = []
    if loja_id and loja_id != "Todas":
        sql += " WHERE e.loja_id = %s"
        params.append(loja_id)
    sql += " ORDER BY p.nome"
    with get_db_connection() as conn:
        df = pd.read_sql(sql, conn, params=params)
    if not df.empty:
        df['produto_id'] = df['produto_id'].astype(int)
        df['loja_id']    = df['loja_id'].astype(int)
    return df

# ——————————————
# Movimentações e relatórios
# ——————————————
def get_movimentacoes(loja_id, start_date, end_date) -> pd.DataFrame:
    start_dt = dt.datetime.combine(start_date, dt.time.min)
    end_dt   = dt.datetime.combine(end_date,   dt.time.max)
    sql = """
        SELECT m.id, m.tipo, m.produto_id, m.loja_id,
               m.quantidade, m.data, m.motivo, p.nome
          FROM movimentacoes_estoque m
          JOIN produtos p ON m.produto_id = p.id
         WHERE m.data BETWEEN %s AND %s
    """
    params = [start_dt, end_dt]
    if loja_id != "Todas":
        sql += " AND m.loja_id = %s"
        params.append(loja_id)
    sql += " ORDER BY m.data"
    with get_db_connection() as conn:
        df = pd.read_sql(sql, conn, params=params)
    if not df.empty:
        df['produto_id'] = df['produto_id'].astype(int)
        df['loja_id']    = df['loja_id'].astype(int)
    return df

def get_entradas_saidas(start_date, end_date, loja_id=None, categoria=None) -> pd.DataFrame:
    start_dt = dt.datetime.combine(start_date, dt.time.min)
    end_dt   = dt.datetime.combine(end_date, dt.time.max)
    sql = """
        SELECT p.nome, m.tipo, SUM(m.quantidade) AS total
          FROM movimentacoes_estoque m
          JOIN produtos p ON m.produto_id = p.id
         WHERE m.data BETWEEN %s AND %s
    """
    params = [start_dt, end_dt]
    if loja_id and loja_id != "Todas":
        sql += " AND m.loja_id = %s"
        params.append(loja_id)
    if categoria and categoria != "Todas":
        sql += " AND p.categoria = %s"
        params.append(categoria)
    sql += " GROUP BY p.nome, m.tipo ORDER BY p.nome, m.tipo"
    with get_db_connection() as conn:
        df = pd.read_sql(sql, conn, params=params)
    df['total'] = df['total'].astype(int)
    return df

def get_compras_periodo(start_date, end_date, loja_id=None) -> pd.DataFrame:
    start_dt = dt.datetime.combine(start_date, dt.time.min)
    end_dt   = dt.datetime.combine(end_date, dt.time.max)
    sql = """
        SELECT m.produto_id, SUM(m.quantidade) AS total_compras
          FROM movimentacoes_estoque m
         WHERE m.tipo = 'entrada'
           AND m.data BETWEEN %s AND %s
    """
    params = [start_dt, end_dt]
    if loja_id and loja_id != "Todas":
        sql += " AND m.loja_id = %s"
        params.append(loja_id)
    sql += " GROUP BY m.produto_id"
    with get_db_connection() as conn:
        return pd.read_sql(sql, conn, params=params)

def get_historico_produtos(loja_id: int, start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    start_dt = dt.datetime.combine(start_date, dt.time.min)
    end_dt   = dt.datetime.combine(end_date,   dt.time.max)
    sql = """
    WITH mov AS (
      SELECT produto_id,
             SUM(CASE WHEN tipo='entrada' THEN quantidade ELSE 0 END) AS total_entradas,
             SUM(CASE WHEN tipo='saida'   THEN quantidade ELSE 0 END) AS total_saidas
        FROM movimentacoes_estoque
       WHERE loja_id = %s AND data BETWEEN %s AND %s
       GROUP BY produto_id
    ), stock AS (
      SELECT produto_id,
             quantidade    AS estoque_atual,
             data_contagem AS ultima_contagem
        FROM estoque
       WHERE loja_id = %s
    )
    SELECT
      p.id                AS produto_id,
      p.nome              AS produto,
      COALESCE(m.total_entradas,0) AS total_entradas,
      COALESCE(m.total_saidas,0)   AS total_saidas,
      COALESCE(s.estoque_atual,0)   AS estoque_atual,
      s.ultima_contagem,
      (COALESCE(s.estoque_atual,0)
       + COALESCE(m.total_saidas,0)
       - COALESCE(m.total_entradas,0)
      )                           AS estoque_inicial
    FROM produtos p
    LEFT JOIN mov   m ON p.id = m.produto_id
    LEFT JOIN stock s ON p.id = s.produto_id
    ORDER BY p.nome
    """
    with get_db_connection() as conn:
        return pd.read_sql(sql, conn, params=(loja_id, start_dt, end_dt, loja_id))

# ——————————————
# Manutenção de estoque
# ——————————————
def corrigir_acrescentar(loja_id, produto_id, quantidade, observacao=""):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s,%s,%s,CURRENT_TIMESTAMP)
                ON CONFLICT(loja_id,produto_id)
                  DO UPDATE SET quantidade=estoque.quantidade+%s,
                                data_atualizacao=CURRENT_TIMESTAMP
            """, (loja_id, produto_id, quantidade, quantidade))
            motivo = "Manutenção: Acrescentar" + (f" ({observacao})" if observacao else "")
            cursor.execute("""
                INSERT INTO movimentacoes_estoque
                  (tipo,produto_id,loja_id,quantidade,motivo,data)
                VALUES ('entrada',%s,%s,%s,%s,CURRENT_TIMESTAMP)
            """, (produto_id, loja_id, quantidade, motivo))
        conn.commit()

def corrigir_remover(loja_id, produto_id, quantidade, observacao=""):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s,%s,-%s,CURRENT_TIMESTAMP)
                ON CONFLICT(loja_id,produto_id)
                  DO UPDATE SET quantidade=estoque.quantidade-%s,
                                data_atualizacao=CURRENT_TIMESTAMP
            """, (loja_id, produto_id, quantidade, quantidade))
            motivo = "Manutenção: Remover" + (f" ({observacao})" if observacao else "")
            cursor.execute("""
                INSERT INTO movimentacoes_estoque
                  (tipo,produto_id,loja_id,quantidade,motivo,data)
                VALUES ('saida',%s,%s,%s,%s,CURRENT_TIMESTAMP)
            """, (produto_id, loja_id, quantidade, motivo))
        conn.commit()

def corrigir_transferir(loja_origem, loja_destino, produto_id, quantidade):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s,%s,-%s,CURRENT_TIMESTAMP)
                ON CONFLICT(loja_id,produto_id)
                  DO UPDATE SET quantidade=estoque.quantidade-%s,
                                data_atualizacao=CURRENT_TIMESTAMP
            """, (loja_origem, produto_id, quantidade, quantidade))
            cursor.execute("""
                INSERT INTO estoque (loja_id, produto_id, quantidade, data_atualizacao)
                VALUES (%s,%s,%s,CURRENT_TIMESTAMP)
                ON CONFLICT(loja_id,produto_id)
                  DO UPDATE SET quantidade=estoque.quantidade+%s,
                                data_atualizacao=CURRENT_TIMESTAMP
            """, (loja_destino, produto_id, quantidade, quantidade))
            m_out = f"Manutenção: Transferência (saída p/ loja {loja_destino})"
            m_in  = f"Manutenção: Transferência (entrada da loja {loja_origem})"
            cursor.execute("""
                INSERT INTO movimentacoes_estoque
                  (tipo,produto_id,loja_id,quantidade,motivo,data)
                VALUES ('saida',%s,%s,%s,%s,CURRENT_TIMESTAMP)
            """, (produto_id, loja_origem, quantidade, m_out))
            cursor.execute("""
                INSERT INTO movimentacoes_estoque
                  (tipo,produto_id,loja_id,quantidade,motivo,data)
                VALUES ('entrada',%s,%s,%s,%s,CURRENT_TIMESTAMP)
            """, (produto_id, loja_destino, quantidade, m_in))
        conn.commit()

# ——————————————
# XML e contagem manual
# ——————————————
def registrar_entrada_xml(loja_id, itens):
    """
    Recebe itens de NF (lista de dicts com 'id' e 'quantidade' em caixas)
    Converte para unidades de loja usando CONVERSION_FACTORS e atualiza movimentacoes_estoque e estoque.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for item in itens:
                # ID do produto e quantidade de caixas na NF
                pid = int(item.get('id', 0)) if str(item.get('id','')).isdigit() else item['id']
                qtd_nf = int(float(item.get('quantidade', 0))) if item.get('quantidade') else 0
                # fator de conversão (caixas → unidades de loja)
                fator = CONVERSION_FACTORS.get(pid, 1)
                qtd_loja = qtd_nf * fator

                motivo = item.get('motivo') or 'Entrada via XML'
                data_entry = item.get('data')
                if not isinstance(data_entry, dt.datetime):
                    try:
                        data_entry = dt.datetime.fromisoformat(data_entry)
                    except:
                        data_entry = dt.datetime.now()

                # registra movimentação de entrada (unidades de loja)
                cursor.execute("""
                    INSERT INTO movimentacoes_estoque
                      (tipo,produto_id,loja_id,quantidade,motivo,data)
                    VALUES ('entrada', %s, %s, %s, %s, %s)
                """, (pid, loja_id, qtd_loja, motivo, data_entry))

                # atualiza estoque (em unidades de loja)
                cursor.execute("""
                    INSERT INTO estoque(loja_id,produto_id,quantidade,data_atualizacao)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(loja_id,produto_id)
                      DO UPDATE SET quantidade = estoque.quantidade + %s,
                                    data_atualizacao = CURRENT_TIMESTAMP
                """, (loja_id, pid, qtd_loja, qtd_loja))
        conn.commit()

def registrar_contagem(loja_id, produto_id, quantidade, data_contagem=None):
    data_cont = data_contagem or dt.datetime.now()
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO movimentacoes_estoque
                  (tipo,produto_id,loja_id,quantidade,motivo,data)
                VALUES ('ajuste',%s,%s,%s,'Contagem de Inventário',%s)
            """, (produto_id, loja_id, quantidade, data_cont))
            cursor.execute("""
                INSERT INTO estoque
                  (loja_id,produto_id,quantidade,data_atualizacao,data_contagem)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(loja_id,produto_id)
                  DO UPDATE SET quantidade=%s,
                                data_atualizacao=%s,
                                data_contagem=%s
            """, (loja_id, produto_id, quantidade, data_cont, data_cont,
                  quantidade, data_cont, data_cont))
        conn.commit()

# ——————————————
# Sugestão de Compra
# ——————————————
def get_saidas_periodo(start_date, end_date, loja_id):
    return pd.read_sql(
        """
        SELECT produto_id, SUM(quantidade) AS total_saidas
          FROM movimentacoes_estoque
         WHERE tipo='saida'
           AND data BETWEEN %s AND %s
           AND loja_id = %s
         GROUP BY produto_id
        """,
        get_db_connection(),
        params=(
            dt.datetime.combine(start_date, dt.time.min),
            dt.datetime.combine(end_date,   dt.time.max),
            loja_id
        )
    )

def get_estoque_at_date(date, loja_id):
    return pd.read_sql(
        """
        SELECT produto_id, quantidade AS estoque_atual
          FROM estoque
         WHERE loja_id = %s
        """,
        get_db_connection(),
        params=(loja_id,)
    )

def calc_sugestao_compra(loja_id, data_inicial, data_final, data_caminhao, periodicidade_rota):
    dias = (data_final - data_inicial).days
    if dias <= 0:
        raise ValueError("Data Final deve ser posterior à Data Inicial.")
    df_est = get_estoque_at_date(data_final, loja_id)
    df_sai = get_saidas_periodo(data_inicial, data_final, loja_id)
    df_prod = get_produtos()

    df = (
        df_prod[["produto_id","nome","categoria","conversao"]]
        .merge(df_est, on="produto_id", how="left")
        .merge(df_sai, on="produto_id", how="left")
    )
    df["estoque_atual"]  = df["estoque_atual"].fillna(0)
    df["total_saidas"]   = df["total_saidas"].fillna(0)
    df["consumo_diario"] = df["total_saidas"] / dias

    gap = (data_caminhao - data_final).days
    if gap < 0:
        raise ValueError("Data de chegada do caminhão deve ser ≥ Data Final.")
    df["estoque_ideal_total"] = df["consumo_diario"] * (periodicidade_rota + gap)

    df["sugestao_compra"] = (
        df["estoque_ideal_total"] - df["estoque_atual"]
    ).apply(lambda x: math.ceil(x) if x > 0 else 0)

    df["sugestao_unidade_compra"] = (
        df["sugestao_compra"] / df["conversao"]
    ).apply(lambda x: math.ceil(x) if x > 0 else 0)

    return df[[
        "produto_id",
        "nome",
        "categoria",
        "estoque_atual",
        "consumo_diario",
        "estoque_ideal_total",
        "sugestao_compra",
        "sugestao_unidade_compra"
    ]]

# ——————————————
# Histórico mensal para Sugestão
# ——————————————
def get_historico_mensal(loja_id: int, meses: int = 3) -> pd.DataFrame:
    hoje = dt.date.today()
    dfs = []
    for i in range(meses, 0, -1):
        ref = hoje - relativedelta(months=i)
        start = ref.replace(day=1)
        end   = (start + relativedelta(months=1)) - dt.timedelta(days=1)

        inv = get_estoque_at_date(start, loja_id)
        inv.rename(columns={'estoque_atual': f'inv_{start:%Y_%m}'}, inplace=True)

        ent = pd.read_sql(
            """
            SELECT produto_id, SUM(quantidade) AS entradas
              FROM movimentacoes_estoque
             WHERE tipo='entrada' AND data BETWEEN %s AND %s AND loja_id=%s
             GROUP BY produto_id
            """,
            get_db_connection(),
            params=(start, dt.datetime.combine(end, dt.time.max), loja_id)
        )
        ent.rename(columns={'entradas': f'ent_{start:%Y_%m}'}, inplace=True)

        sai = pd.read_sql(
            """
            SELECT produto_id, SUM(quantidade) AS saidas
              FROM movimentacoes_estoque
             WHERE tipo='saida' AND data BETWEEN %s AND %s AND loja_id=%s
             GROUP BY produto_id
            """,
            get_db_connection(),
            params=(start, dt.datetime.combine(end, dt.time.max), loja_id)
        )
        sai.rename(columns={'saidas': f'sai_{start:%Y_%m}'}, inplace=True)

        dfp = inv.merge(ent, on='produto_id', how='outer') \
                 .merge(sai, on='produto_id', how='outer')
        dfs.append(dfp)

    df_hist = dfs[0]
    for dfp in dfs[1:]:
        df_hist = df_hist.merge(dfp, on='produto_id', how='outer')
    prod = get_produtos()[['produto_id','nome']]
    return prod.merge(df_hist, on='produto_id', how='left').fillna(0)

# ——————————————
# Pedido de Compra
# ——————————————
def create_purchase_order(loja_id, itens):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO purchase_orders(loja_id,data_criacao) VALUES(%s,CURRENT_TIMESTAMP) RETURNING id",
                (loja_id,)
            )
            oid = cursor.fetchone()[0]
            for i in itens:
                cursor.execute(
                    "INSERT INTO purchase_order_items(order_id,produto_id,quantidade) VALUES(%s,%s,%s)",
                    (oid, i["produto_id"], i["quantidade"])
                )
        conn.commit()
    return oid

def get_purchase_orders(loja_id: int = None) -> pd.DataFrame:
    sql = "SELECT id, loja_id, data_criacao FROM purchase_orders"
    params = []
    if loja_id:
        sql += " WHERE loja_id = %s"
        params.append(loja_id)
    sql += " ORDER BY data_criacao DESC"
    return pd.read_sql(sql, get_db_connection(), params=params)

@st.cache_data(ttl=600)
def get_purchase_order_items(order_id):
    return pd.read_sql(
        """
        SELECT poi.produto_id,
               p.nome    AS produto,
               poi.quantidade
          FROM purchase_order_items poi
          JOIN produtos p ON poi.produto_id = p.id
         WHERE poi.order_id = %s
         ORDER BY p.nome
        """,
        get_db_connection(),
        params=(order_id,)
    )
@st.cache_data(ttl=600)
def get_categorias():
    """
    Retorna a lista de categorias únicas dos produtos,
    ordenadas alfabeticamente.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT categoria FROM produtos ORDER BY categoria"
            )
            rows = cursor.fetchall()
    return [row[0] for row in rows]
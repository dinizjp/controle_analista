import streamlit as st
import pandas as pd
import datetime as dt
from utils import get_lojas, get_db_connection

st.set_page_config(page_title="Histórico Mensal", layout="wide")

def page_historico():
    st.title("Histórico Mensal de Movimentações por Produto")

    # 1) Seleção de loja
    lojas = get_lojas()
    if not lojas:
        st.warning("Nenhuma loja cadastrada.")
        return
    lojas_dict = {f"{id_} – {nome}": id_ for id_, nome in lojas}
    sel = st.selectbox("Selecione a loja", list(lojas_dict.keys()))
    loja_id = lojas_dict[sel]

    # 2) Filtro de período
    ano = st.number_input("Ano", 2000, 2100, value=dt.date.today().year)
    mes = st.selectbox("Mês", list(range(1,13)), index=dt.date.today().month-1)
    primeiro_dia = dt.date(ano, mes, 1)
    ultimo_dia   = (primeiro_dia + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)

    # 3) Consulta por produto (mesma lógica SQL)
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
             quantidade      AS estoque_atual,
             data_contagem   AS ultima_contagem
      FROM estoque
      WHERE loja_id = %s
    )
    SELECT
      p.id         AS produto_id,
      p.nome       AS produto,
      COALESCE(m.total_entradas,0) AS total_entradas,
      COALESCE(m.total_saidas,0)   AS total_saidas,
      COALESCE(s.estoque_atual,0)   AS estoque_atual,
      s.ultima_contagem,
      (COALESCE(s.estoque_atual,0)
       + COALESCE(m.total_saidas,0)
       - COALESCE(m.total_entradas,0)
      ) AS estoque_inicial
    FROM produtos p
    LEFT JOIN mov AS m ON p.id = m.produto_id
    LEFT JOIN stock AS s ON p.id = s.produto_id
    ORDER BY p.nome
    """

    with get_db_connection() as conn:
        df = pd.read_sql(sql, conn, params=(loja_id, primeiro_dia, ultimo_dia, loja_id))

    # 4) Exibição
    st.subheader(f"{sel} — {primeiro_dia.strftime('%B/%Y')}")
    st.dataframe(df, use_container_width=True)
    

if __name__ == "__main__":
    page_historico()

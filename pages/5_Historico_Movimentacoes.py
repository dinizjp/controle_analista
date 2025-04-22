import streamlit as st
import pandas as pd
import datetime as dt
from utils import get_lojas, get_db_connection

st.set_page_config(page_title="Histórico Mensal", layout="wide")

def page_historico():
    st.title("Histórico Mensal de Movimentações")

    # 1) Seleção de loja
    lojas = get_lojas()
    if not lojas:
        st.warning("Nenhuma loja cadastrada.")
        return
    lojas_dict = {f"{id_} – {nome}": id_ for id_, nome in lojas}
    loja_sel = st.selectbox("Selecione a loja", list(lojas_dict.keys()))
    loja_id = lojas_dict[loja_sel]

    # 2) Filtro de período
    col1, col2 = st.columns(2)
    with col1:
        ano = st.number_input("Ano", 2000, 2100, value=dt.date.today().year)
    with col2:
        mes = st.selectbox("Mês", list(range(1,13)), index=dt.date.today().month-1)

    primeiro_dia = dt.date(ano, mes, 1)
    ultimo_dia   = (primeiro_dia + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)

    # 3) Consultas
    conn = get_db_connection()
    df_mov = pd.read_sql(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tipo='entrada' THEN quantidade END),0) AS total_entradas,
            COALESCE(SUM(CASE WHEN tipo='saida'   THEN quantidade END),0) AS total_saidas
        FROM movimentacoes_estoque
        WHERE loja_id=%s AND data BETWEEN %s AND %s
        """, 
        conn, params=(loja_id, primeiro_dia, ultimo_dia)
    )
    entradas = int(df_mov.loc[0, 'total_entradas'])
    saidas   = int(df_mov.loc[0, 'total_saidas'])

    df_stock = pd.read_sql(
        "SELECT quantidade FROM estoque WHERE loja_id=%s", 
        conn, params=(loja_id,)
    )
    estoque_atual = int(df_stock['quantidade'].sum())

    df_cont = pd.read_sql(
        "SELECT MAX(data_contagem) AS ultima_contagem FROM estoque WHERE loja_id=%s",
        conn, params=(loja_id,)
    )
    ultima_contagem = df_cont.loc[0, 'ultima_contagem']

    # 4) Cálculo de estoque inicial
    estoque_inicial = estoque_atual + saidas - entradas

    # 5) Resumo e exibição
    resumo = pd.DataFrame([{
        'Estoque Inicial': estoque_inicial,
        'Total Entradas':   entradas,
        'Total Saídas':     saidas,
        'Estoque Atual':    estoque_atual
    }])
    st.subheader(f"Resumo de {primeiro_dia.strftime('%B/%Y')}")
    st.table(resumo)
    st.markdown(f"**Última contagem realizada em:** {ultima_contagem}")

if __name__ == "__main__":
    page_historico()

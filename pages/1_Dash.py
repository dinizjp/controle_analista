import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px

from utils import (
    get_lojas,
    get_db_connection,
    get_entradas_saidas,
    get_estoque_all,
    get_produtos,
    get_historico_produtos,
    get_categorias
)

st.set_page_config(page_title='Dash', layout='wide')

def get_period_sales(start_date, end_date, loja_id=None):
    start_dt = dt.datetime.combine(start_date, dt.time.min)
    end_dt   = dt.datetime.combine(end_date,   dt.time.max)
    sql = """
        SELECT m.produto_id, p.nome, p.categoria, SUM(m.quantidade) AS total_vendido
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.tipo='saida' AND m.data BETWEEN %s AND %s
    """
    params = [start_dt, end_dt]
    if loja_id and loja_id != "Todas":
        sql += " AND m.loja_id = %s"
        params.append(loja_id)
    sql += " GROUP BY m.produto_id, p.nome, p.categoria ORDER BY total_vendido DESC"
    with get_db_connection() as conn:
        return pd.read_sql(sql, conn, params=params)

def page_dash():
    st.title("Dashboard de Controle de Estoque - Analista de Suprimentos")

    # 1) Filtros de Data e Loja
    col1, col2, col3 = st.columns(3)
    hoje = dt.date.today()
    inicio_mes = hoje.replace(day=1)

    with col1:
        start_date = st.date_input("Data Inicial", inicio_mes, key="start_date")
    with col2:
        end_date   = st.date_input("Data Final", hoje,     key="end_date")
    with col3:
        lojas_opts = {f"{lid} – {nome}": lid for lid, nome in get_lojas()}
        sel_loja   = st.selectbox("Selecione a loja", list(lojas_opts.keys()), key="store_select")
        loja_id    = lojas_opts[sel_loja]

    if start_date > end_date:
        st.error("A Data Inicial deve ser anterior ou igual à Data Final.")
        return

    # 2) Lista fixa de categorias (filtrada)
    order        = ["Açaí", "Sorvetes", "Polpa", "Complementos",
                    "Embalagens Distribuidora", "Uso e Consumo"]
    todas_cats   = get_categorias()
    ordered_cats = [c for c in order if c in todas_cats]

    # --- 3) Estoque Atual por Produto ---
    st.subheader("Estoque Atual por Produto")
    stock_cats = st.multiselect("Categorias (Estoque)",
                                ordered_cats,
                                default=ordered_cats,
                                key="stock_cats")

    # Puxa estoque e remove a coluna 'nome' e 'loja_id' duplicadas
    estoque_df = get_estoque_all(loja_id).drop(columns=['nome','loja_id'], errors='ignore')

    # Puxa produtos e renomeia 'nome' para evitar duplicata
    prod_df = pd.DataFrame(
        get_produtos(),
        columns=["produto_id", "nome", "categoria", "unidade_medida", "valor"]
    ).rename(columns={"nome": "prod_nome"})

    df_stock = (
        estoque_df
        .merge(prod_df[["produto_id", "prod_nome", "categoria"]],
               on="produto_id", how="left")
        .query("categoria in @stock_cats")
    )
    df_stock["categoria"] = pd.Categorical(df_stock["categoria"],
                                           categories=ordered_cats,
                                           ordered=True)
    df_stock = (
        df_stock
        .sort_values(["categoria", "prod_nome"])
        .rename(columns={"prod_nome": "nome"})
    )
    st.dataframe(df_stock, use_container_width=True)

    # --- 4) Histórico de Movimentações por Produto ---
    st.subheader("Histórico de Movimentações por Produto")
    hist_cats = st.multiselect("Categorias (Histórico)",
                               ordered_cats,
                               default=ordered_cats,
                               key="hist_cats")

    df_hist = get_historico_produtos(loja_id, start_date, end_date)
    st.dataframe(df_hist, use_container_width=True)

    # --- 5) Gráfico: Entradas e Saídas ---
    st.subheader("Entradas e Saídas no Período")
    entries_cats = st.multiselect("Categorias (Entradas/Saídas)",
                                  ordered_cats,
                                  default=ordered_cats,
                                  key="entries_cats")

    entradas_saidas = get_entradas_saidas(start_date, end_date, loja_id)
    entradas_saidas = (
        entradas_saidas
        .merge(prod_df[["prod_nome", "categoria"]],
               left_on="nome", right_on="prod_nome",
               how="left")
        .drop(columns=["nome"])                  # descarta a coluna 'nome' original
        .rename(columns={"prod_nome": "nome"})   # renomeia prod_nome para nome
    )
    entradas_saidas = entradas_saidas[entradas_saidas["categoria"].isin(entries_cats)]

    if not entradas_saidas.empty:
        fig1 = px.bar(
            entradas_saidas,
            x="nome",
            y="total",
            color="tipo",
            barmode="group",
            text="total",
            height=800,
            color_discrete_map={'entrada': '#00CC96', 'saida': '#EF553B'}
        )
        fig1.update_traces(textposition='outside')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.write("Nenhuma movimentação para as categorias selecionadas.")

    # --- 6) Gráfico: Produtos Mais Vendidos ---
    st.subheader("Produtos Mais Vendidos no Período")
    sales_cats = st.multiselect("Categorias (Mais Vendidos)",
                                ordered_cats,
                                default=ordered_cats,
                                key="sales_cats")
    period_sales = get_period_sales(start_date, end_date, loja_id)
    period_sales = period_sales[period_sales["categoria"].isin(sales_cats)]

    if not period_sales.empty:
        fig2 = px.bar(period_sales,
                      x="nome",
                      y="total_vendido",
                      color="categoria",
                      text="total_vendido",
                      height=800)
        fig2.update_traces(textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("Nenhum produto vendido nas categorias selecionadas.")

if __name__ == "__main__":
    page_dash()

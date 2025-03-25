# Dash.py
import streamlit as st
import plotly.express as px
import pandas as pd
import datetime
import io
from utils import get_lojas, get_db_connection, get_categorias, get_entradas_saidas, get_movimentacoes, get_estoque_all

st.set_page_config(page_title='Dash', layout='wide')

# Função para buscar os 20 produtos mais vendidos de todos os tempos
def get_all_time_sales(categoria=None):
    query = """
        SELECT m.produto_id, p.nome, p.categoria, SUM(m.quantidade) as total_vendido
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.tipo = 'saida'
    """
    params = []
    if categoria and categoria != "Todas":
        query += " AND p.categoria = %s"
        params.append(categoria)
    query += " GROUP BY m.produto_id, p.nome, p.categoria ORDER BY total_vendido DESC LIMIT 20"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para buscar vendas no período selecionado
def get_period_sales(start_date, end_date, loja_id=None, categoria=None):
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
    query = """
        SELECT m.produto_id, p.nome, p.categoria, SUM(m.quantidade) as total_vendido
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.tipo = 'saida' AND m.data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id and loja_id != "Todas":
        query += " AND m.loja_id = %s"
        params.append(loja_id)
    if categoria and categoria != "Todas":
        query += " AND p.categoria = %s"
        params.append(categoria)
    query += " GROUP BY m.produto_id, p.nome, p.categoria ORDER BY total_vendido DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para converter DataFrame em Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Função principal do dashboard
def page_dash():
    st.title("Dashboard de Controle de Estoque - Analista de Suprimentos")

    # Filtros
    st.markdown("### Filtros")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        default_start = datetime.date.today() - datetime.timedelta(days=30)
        start_date = st.date_input("Data Inicial", default_start)
    with col2:
        default_end = datetime.date.today()
        end_date = st.date_input("Data Final", default_end)
    if start_date > end_date:
        st.error("A data inicial deve ser menor ou igual à data final.")
        return

    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    loja_options["Todas"] = "Todas"
    with col3:
        selected_loja_str = st.selectbox("Selecione a loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]

    categorias = get_categorias()
    with col4:
        selected_categoria = st.selectbox("Selecione a categoria", ["Todas"] + categorias)

    # Ajustar a categoria selecionada
    if selected_categoria == "Todas":
        selected_categoria = None

    # Buscar dados
    all_time_sales_df = get_all_time_sales(selected_categoria)
    period_sales_df = get_period_sales(start_date, end_date, selected_loja_id, selected_categoria)
    estoque_df = get_estoque_all(selected_loja_id)
    movimentacoes_df = get_movimentacoes(selected_loja_id, start_date, end_date)

    # Gráfico 1: Entradas e Saídas no Período
    st.subheader("Entradas e Saídas no Período")
    entradas_saidas_df = get_entradas_saidas(start_date, end_date, selected_loja_id, selected_categoria)
    if not entradas_saidas_df.empty:
        fig1 = px.bar(entradas_saidas_df, 
                      x="nome", 
                      y="total", 
                      color="tipo", 
                      barmode="group", 
                      height=700, 
                      text="total",
                      color_discrete_map={'entrada': '#00CC96', 'saida': '#EF553B'})
        fig1.update_traces(textposition='outside')
        st.plotly_chart(fig1, use_container_width=True, key="fig1")
    else:
        st.write("Nenhuma movimentação no período selecionado.")

    # Tabela de Estoque
    st.subheader("Tabela de Estoque")
    if selected_categoria:
        estoque_df = estoque_df[estoque_df['nome'].isin(
            get_period_sales(start_date, end_date, selected_loja_id, selected_categoria)['nome']
        )]
    st.dataframe(estoque_df, use_container_width=True)
    excel_estoque = to_excel(estoque_df)
    st.download_button(
        label="Baixar Tabela de Estoque em Excel",
        data=excel_estoque,
        file_name="estoque.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Tabela de Movimentações
    st.subheader("Tabela de Movimentações")
    if selected_categoria:
        movimentacoes_df = movimentacoes_df[movimentacoes_df['nome'].isin(
            get_period_sales(start_date, end_date, selected_loja_id, selected_categoria)['nome']
        )]
    st.dataframe(movimentacoes_df, use_container_width=True)
    excel_movimentacoes = to_excel(movimentacoes_df)
    st.download_button(
        label="Baixar Tabela de Movimentações em Excel",
        data=excel_movimentacoes,
        file_name="movimentacoes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Gráfico 2: Produtos Mais Vendidos no Período Selecionado
    st.subheader("Produtos Mais Vendidos no Período")
    fig2 = px.bar(period_sales_df,
                  x="nome", 
                  y="total_vendido", 
                  color="categoria",
                  height=700, 
                  text="total_vendido")
    fig2.update_traces(textposition='outside')
    st.plotly_chart(fig2, use_container_width=True, key="fig2")

    # Gráfico 3: 20 Produtos Mais Vendidos ao Longo do Tempo
    st.subheader("20 Produtos Mais Vendidos ao Longo do Tempo")
    fig3 = px.bar(all_time_sales_df, 
                  x="nome", 
                  y="total_vendido", 
                  color="categoria",
                  height=700,
                  text="total_vendido")
    fig3.update_traces(textposition='outside')
    st.plotly_chart(fig3, use_container_width=True, key="fig3")

# Executar o dashboard
page_dash()
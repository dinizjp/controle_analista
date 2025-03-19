import streamlit as st
import plotly.express as px
import pandas as pd
import datetime
import io
from utils import get_lojas, get_db_connection

st.set_page_config(page_title='Dash', layout='wide')

# Função para buscar os 20 produtos mais vendidos de todos os tempos
def get_all_time_sales():
    query = """
        SELECT m.produto_id, p.nome, p.categoria, SUM(m.quantidade) as total_vendido
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.tipo = 'saida'
        GROUP BY m.produto_id, p.nome, p.categoria
        ORDER BY total_vendido DESC
        LIMIT 20
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para buscar vendas no período selecionado
def get_period_sales(start_date, end_date, loja_id=None):
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
    query += " GROUP BY m.produto_id, p.nome, p.categoria ORDER BY total_vendido DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para calcular o estoque em uma data específica
def get_estoque_at_date(date, loja_id=None):
    date = datetime.datetime.combine(date, datetime.time.max)
    query = """
        SELECT p.id AS produto_id, p.nome,
               COALESCE(SUM(CASE WHEN m.tipo = 'entrada' THEN m.quantidade ELSE 0 END), 0) -
               COALESCE(SUM(CASE WHEN m.tipo = 'saida' THEN m.quantidade ELSE 0 END), 0) AS quantidade
        FROM produtos p
        LEFT JOIN movimentacoes_estoque m ON p.id = m.produto_id
        WHERE (m.data <= %s OR m.data IS NULL)
    """
    params = [date]
    if loja_id and loja_id != "Todas":
        query += " AND (m.loja_id = %s OR m.loja_id IS NULL)"
        params.append(loja_id)
    query += " GROUP BY p.id, p.nome"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para buscar compras no período
def get_compras_periodo(start_date, end_date, loja_id=None):
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
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
    return pd.DataFrame(data, columns=columns)

# Função para buscar o estoque atual
def get_estoque(loja_id=None):
    query = """
        SELECT e.loja_id, p.nome, e.quantidade, e.data_atualizacao
        FROM estoque e
        JOIN produtos p ON e.produto_id = p.id
    """
    if loja_id and loja_id != "Todas":
        query += " WHERE e.loja_id = %s"
        params = [loja_id]
    else:
        params = []
    query += " ORDER BY p.nome"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
    return pd.DataFrame(data, columns=columns)

# Função para buscar movimentações no período
def get_movimentacoes(start_date, end_date, loja_id=None):
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
    query = """
        SELECT m.id, m.tipo, p.nome, m.loja_id, m.quantidade, m.data, m.motivo
        FROM movimentacoes_estoque m
        JOIN produtos p ON m.produto_id = p.id
        WHERE m.data BETWEEN %s AND %s
    """
    params = [start_datetime, end_datetime]
    if loja_id and loja_id != "Todas":
        query += " AND m.loja_id = %s"
        params.append(loja_id)
    query += " ORDER BY m.data"
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
    st.title("Dashboard de Controle de Estoque")

    # Filtros
    st.markdown("### Filtros")
    col1, col2, col3 = st.columns(3)
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

    # Buscar dados
    all_time_sales_df = get_all_time_sales()
    period_sales_df = get_period_sales(start_date, end_date, selected_loja_id)
    estoque_inicial_df = get_estoque_at_date(start_date - datetime.timedelta(days=1), selected_loja_id)
    estoque_final_df = get_estoque_at_date(end_date, selected_loja_id)
    compras_df = get_compras_periodo(start_date, end_date, selected_loja_id)

    # Gráfico 1: 20 Produtos Mais Vendidos de Todos os Tempos
    st.subheader("20 Produtos mais vendidos ao longo do tempo")
    fig1 = px.bar(all_time_sales_df, 
                  x="nome", 
                  y="total_vendido", 
                  color="categoria",
                  height=700,
                  text="total_vendido"                 
                   )
    
    fig1.update_traces(textposition='outside')

    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2: Produtos Mais Vendidos no Período Selecionado
    st.subheader("Produtos mais vendidos do período")
    fig2 = px.bar(period_sales_df,
                   x="nome", 
                   y="total_vendido", 
                   color="categoria",
                   height=700, 
                   text="total_vendido"
                  )
    
    fig2.update_traces(textposition='outside')

    st.plotly_chart(fig2, use_container_width=True)

    # Tabela de Sugestão de Compra baseada no consumo
    st.subheader("Sugestão de Compra")
    
    # Realiza a junção dos dados de estoque inicial, estoque final e compras
    estoque_merge = pd.merge(
         estoque_inicial_df[['produto_id', 'nome', 'quantidade']].rename(columns={'quantidade': 'estoque_inicial'}),
         estoque_final_df[['produto_id', 'nome', 'quantidade']].rename(columns={'quantidade': 'estoque_final'}),
         on=['produto_id', 'nome'],
         how='outer'
    )
    sugestao_df = pd.merge(estoque_merge, compras_df, on='produto_id', how='outer')
    sugestao_df = sugestao_df.fillna(0)
    
    # Calcular o consumo total para cada produto
    sugestao_df['consumo_total'] = (sugestao_df['estoque_inicial'] + sugestao_df['total_compras']) - sugestao_df['estoque_final']
    # Garantir que o consumo total não seja negativo
    sugestao_df['consumo_total'] = sugestao_df['consumo_total'].apply(lambda x: max(x, 0))
    
    # Número de dias do período analisado
    dias_periodo = (end_date - start_date).days or 1
    
    # Calcular o consumo diário (arredondado para inteiro)
    sugestao_df['consumo_diario'] = (sugestao_df['consumo_total'] / dias_periodo).round().astype(int)
    
    # Inputs para definir o período futuro
    col1, col2 = st.columns(2)
    with col1:
        data_proxima_rota = st.date_input("Data da Próxima Rota", datetime.date.today() + datetime.timedelta(days=7))
    with col2:
        data_chegada_caminhao = st.date_input("Data da Chegada do Caminhão", datetime.date.today() + datetime.timedelta(days=14))
    
    # Validação das datas e cálculo da sugestão
    if data_proxima_rota >= data_chegada_caminhao:
        st.error("A Data da Próxima Rota deve ser anterior à Data da Chegada do Caminhão.")
    else:
        dias_futuro = (data_chegada_caminhao - data_proxima_rota).days
        sugestao_df['sugestao'] = (sugestao_df['consumo_diario'] * dias_futuro).astype(int)
        st.dataframe(sugestao_df[['nome', 'estoque_inicial', 'total_compras', 'estoque_final', 'consumo_total', 'consumo_diario', 'sugestao']], use_container_width=True)

    # Tabela de Estoque
    st.subheader("Tabela de Estoque")
    estoque_df = get_estoque(selected_loja_id)
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
    movimentacoes_df = get_movimentacoes(start_date, end_date, selected_loja_id)
    st.dataframe(movimentacoes_df, use_container_width=True)
    excel_movimentacoes = to_excel(movimentacoes_df)
    st.download_button(
        label="Baixar Tabela de Movimentações em Excel",
        data=excel_movimentacoes,
        file_name="movimentacoes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Executar o dashboard
page_dash()
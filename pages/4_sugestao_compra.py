# sugestao_compras.py
import streamlit as st
import pandas as pd
import datetime
import math
import io
from utils import get_lojas, get_produtos

# Configuração da página
st.set_page_config(page_title="Sugestão de Compra", layout="wide")

# Função para buscar saídas no período (otimizada para uma única consulta)
def get_saidas_periodo(start_date, end_date, loja_id):
    start_datetime = dt.datetime.combine(start_date, dt.time.min)
    end_datetime = dt.datetime.combine(end_date, dt.time.max)
    query = """
        SELECT m.produto_id, SUM(m.quantidade) AS total_saidas
        FROM movimentacoes_estoque m
        WHERE m.tipo = 'saida' 
          AND m.data BETWEEN %s AND %s 
          AND m.loja_id = %s
        GROUP BY m.produto_id
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
        SELECT e.produto_id, p.nome, e.quantidade as estoque_atual
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
    return df

def page_sugestao_compra():
    # Reinicializa a variável de cálculo para evitar persistência de dados antigos
    if 'df_calculado' in st.session_state:
        del st.session_state.df_calculado
    st.session_state.df_calculado = None

    st.title("Sugestão de Compra")
    
    st.markdown("""
    ### Instruções para a utilização da ferramenta de Sugestão de Compra
    
    Este módulo tem como objetivo auxiliar na definição do pedido de compra dos produtos, garantindo que o estoque seja suficiente para suprir a demanda da loja até a chegada do caminhão de reposição.
    
    1. **Período de Consumo:**  
       Selecione um período (Data Inicial e Data Final) para calcular a média diária de consumo de cada produto.
       
    2. **Estoque Atual:**  
       A "foto" do estoque é obtida na **Data Final**, representando o último registro do estoque.
       
    3. **Data de Chegada do Caminhão:**  
       Informe a data prevista para a chegada do caminhão de reposição. Esse valor define o gap de dias entre a foto do estoque e a chegada do caminhão.
       
    4. **Cálculo da Sugestão de Compra:**  
       - **Consumo Diário:** Total de saídas no período dividido pelo número de dias do período.
       - **Estoque Ideal para 30 Dias:** Consumo diário multiplicado por 30 (pois as rotas são de 30 em 30 dias).
       - **Consumo Extra (Gap):** Consumo diário multiplicado pelo número de dias entre a foto do estoque e a chegada do caminhão.
       - **Estoque Ideal Total:** Soma do estoque ideal para 30 dias com o consumo extra do gap.
       - **Sugestão de Compra:** Diferença entre o Estoque Ideal Total e o Estoque Atual (se positivo, arredondado para cima).
       
    #### Dica:
    - Utilize o filtro para exibir apenas os produtos com sugestão > 0.
    - Após o cálculo, é possível baixar a tabela em Excel para facilitar a análise.
    """)
    
    # Seleção da loja
    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    selected_loja_str = st.selectbox("Selecione a Loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]
    
    # Inputs de datas
    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicial = st.date_input("Data Inicial do Período", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        data_final = st.date_input("Data Final do Período (Foto do Estoque)", datetime.date.today())
    with col3:
        data_caminhao = st.date_input("Data de Chegada do Caminhão", datetime.date.today() + datetime.timedelta(days=5))
        
    if st.button("Calcular Sugestão de Compra"):
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return
        
        # Obter estoque atual com base na Data Final
        estoque_atual_df = get_estoque_at_date(data_final, selected_loja_id).rename(columns={"quantidade_ajustada": "estoque_atual"})
        produtos_df = pd.DataFrame(get_produtos(), columns=["id", "nome", "categoria", "unidade_medida", "valor"])
        produtos_df = produtos_df[["id", "categoria", "nome"]].rename(columns={"id": "produto_id"})
        
        # Mesclar produtos com estoque atual
        df = pd.merge(produtos_df, estoque_atual_df[["produto_id", "estoque_atual"]], on="produto_id", how="left")
        df["estoque_atual"].fillna(0, inplace=True)
        df["estoque_atual"] = df["estoque_atual"].astype(float)
        
        # Obter e agregar as saídas do período para cada produto
        saidas_df = get_saidas_periodo(data_inicial, data_final, selected_loja_id)
        if not saidas_df.empty:
            saidas_df = saidas_df.groupby("produto_id", as_index=False)["total_saidas"].sum()
        df = pd.merge(df, saidas_df, on="produto_id", how="left")
        df["total_saidas"].fillna(0, inplace=True)
        
        # Exibe dados de saídas para depuração
        st.write("Dados de saídas retornados:", saidas_df)
        
        # Calcular a média de consumo diário
        df["consumo_diario"] = df["total_saidas"] / dias_consumo
        
        # Calcular o gap: dias entre a foto do estoque (data_final) e a chegada do caminhão
        gap = (data_caminhao - data_final).days
        if gap < 0:
            st.error("A Data de Chegada do Caminhão deve ser posterior à Data Final.")
            return
        
        # Estoque ideal para 30 dias de consumo
        estoque_ideal_mes = df["consumo_diario"] * 30
        
        # Consumo extra no gap
        consumo_gap = df["consumo_diario"] * gap
        
        # Estoque ideal total: para 30 dias + consumo extra do gap
        df["estoque_ideal_total"] = estoque_ideal_mes + consumo_gap
        
        # Sugestão de compra: se o estoque atual for menor que o estoque ideal total
        df["sugestao_compra"] = (df["estoque_ideal_total"] - df["estoque_atual"]).apply(lambda x: math.ceil(x) if x > 0 else 0)
        
        st.session_state.df_calculado = df
        
    if st.session_state.df_calculado is not None:
        st.subheader("Tabela de Sugestão de Compra")
        filtrar = st.checkbox("Exibir apenas produtos com sugestão de compra > 0", value=False)
        df_exibicao = st.session_state.df_calculado.copy()
        if filtrar:
            df_exibicao = df_exibicao[df_exibicao["sugestao_compra"] > 0]
            
        st.dataframe(
            df_exibicao[["produto_id", "nome", "estoque_atual", "consumo_diario", "estoque_ideal_total", "sugestao_compra"]],
            use_container_width=True
        )
        
        # Gerar arquivo Excel para download
        towrite = io.BytesIO()
        df_exibicao.to_excel(towrite, index=False, sheet_name="SugestaoCompra")
        towrite.seek(0)
        
        st.download_button(
            label="Download Tabela em Excel",
            data=towrite,
            file_name="sugestao_compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
if __name__ == "__main__":
    page_sugestao_compra()
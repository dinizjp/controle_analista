# sugestao_compra.py
import streamlit as st
import pandas as pd
import datetime as dt
import math
import io
from utils import get_lojas, get_produtos, get_db_connection

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
    if 'df_calculado' not in st.session_state:
        st.session_state.df_calculado = None

    st.title("Sugestão de Compra")
    
    st.markdown("""
    1. **Período de Consumo:**  
       Escolha um período (Data Inicial e Data Final) para calcular a média diária de consumo de cada produto com base nas saídas registradas.

    2. **Estoque Atual:**  
       O estoque mostrado é a "foto" do estoque na **Data Final**, ou seja, o último registro disponível até essa data.

    3. **Data de Chegada do Caminhão:**  
       Informe a data prevista para a chegada do próximo caminhão de reposição. Isso define o "gap" (dias entre a foto do estoque e a chegada do caminhão).

    4. **Periodicidade da Rota:**  
       Digite quantos dias a rota normalmente leva entre uma entrega e outra (ex.: 15, 30, 45 dias). Esse valor define o estoque ideal para o período entre rotas.

    5. **Cálculo da Sugestão de Compra:**  
       - **Consumo Diário:** Total de saídas no período dividido pelo número de dias do período.  
       - **Estoque Ideal para a Rota:** Consumo diário multiplicado pela periodicidade da rota que você informou (arredondado para cima).  
       - **Consumo Extra (Gap):** Consumo diário multiplicado pelo número de dias entre a foto do estoque e a chegada do caminhão.  
       - **Estoque Ideal Total:** Estoque ideal para a rota + consumo extra do gap (arredondado para cima).  
       - **Sugestão de Compra:** Diferença entre o Estoque Ideal Total e o Estoque Atual (se positivo, arredondado para cima; se não, zero).

    #### Dica:
    - Use o filtro para exibir apenas os produtos com sugestão > 0.  
    - Após calcular, você pode baixar a tabela em Excel para analisar ou compartilhar.
    """)
    
    # Seleção da loja
    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    selected_loja_str = st.selectbox("Selecione a Loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]
    
    # Inputs de datas e periodicidade
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_inicial = st.date_input("Data Inicial do Período", dt.date.today() - dt.timedelta(days=30))
    with col2:
        data_final = st.date_input("Data Final do Período (Foto do Estoque)", dt.date.today())
    with col3:
        data_caminhao = st.date_input("Data de Chegada do Caminhão", dt.date.today() + dt.timedelta(days=5))
    with col4:
        periodicidade_rota = st.number_input("Qual a periodicidade da rota (dias)?", min_value=1, value=30, step=1)

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
        
        # Estoque ideal para a periodicidade da rota informada
        estoque_ideal_rota = df["consumo_diario"] * periodicidade_rota
        
        # Consumo extra no gap
        consumo_gap = df["consumo_diario"] * gap
        
        # Estoque ideal total: para a periodicidade da rota + consumo extra do gap
        df["estoque_ideal_total"] = estoque_ideal_rota + consumo_gap
        
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
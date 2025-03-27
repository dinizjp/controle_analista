# sugestao_compras.py
import streamlit as st
import pandas as pd
import datetime
import math
import io
from utils import get_lojas, get_estoque_at_date, get_produtos, get_saidas_periodo

# Configuração da página
st.set_page_config(page_title="Sugestão de Compra", layout="wide")

# Inicializar o session_state para armazenar o DataFrame calculado
if 'df_calculado' not in st.session_state:
    st.session_state.df_calculado = None

def page_sugestao_compra():
    st.title("Sugestão de Compra")
    
    # Explicação detalhada para a analista
    st.markdown("""

    #### Como funciona o cálculo:
    1. **Período de Consumo:**  
       Selecione um período (Data Inicial e Data Final) para que possamos calcular a média diária de consumo de cada produto.
       
    2. **Estoque Atual:**  
       A "foto" do estoque é obtida na **Data Final**, que representa o último momento em que o estoque foi atualizado.
       
    3. **Data de Chegada do Caminhão:**  
       Informe a data prevista para a chegada do caminhão de reposição. Essa data define quantos dias o estoque atual deverá atender (incluindo o gap desde a foto do estoque até a chegada do caminhão).
       
    4. **Cálculo do Estoque Ideal:**  
       - **Consumo Diário:** Calculado como o total de saídas no período dividido pelo número de dias do período.
       - **Consumo Até Chegada:** Multiplica-se o consumo diário pelo número de dias entre a Data Final (foto do estoque) e a Data de Chegada do Caminhão.
       - **Estoque de Segurança:** Acrescenta 10% do consumo até chegada, para cobrir imprevistos.
       - **Estoque Ideal:** Soma do consumo até chegada com o estoque de segurança.
       
    5. **Sugestão de Compra:**  
       Se o estoque atual for inferior ao estoque ideal, a ferramenta sugere a quantidade a ser comprada para atingir esse estoque ideal. Caso contrário, a sugestão é zero.

    #### Dica:
    - Utilize o filtro para exibir apenas os produtos que possuem sugestão de compra (valor maior que 0).  
    - Após o cálculo, você pode baixar a tabela em formato Excel para facilitar a análise e o envio dos pedidos.
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
        data_chegada = st.date_input("Data de Chegada do Caminhão", datetime.date.today() + datetime.timedelta(days=10))

    if st.button("Calcular Sugestão de Compra"):
        # Validação do período
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return

        # Obter estoque atual com base na Data Final (foto do estoque)
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

        # Calcular a média de consumo diário (valor exato, em float)
        df["consumo_diario"] = df["total_saidas"] / dias_consumo

        # Calcular quantos dias se passarão entre a foto do estoque e a chegada do caminhão
        dias_ate_chegada = (data_chegada - data_final).days
        if dias_ate_chegada < 0:
            st.error("A Data de Chegada deve ser posterior à Data Final (foto do estoque).")
            return

        # Consumo esperado total até a chegada do caminhão
        df["consumo_ate_chegada"] = df["consumo_diario"] * dias_ate_chegada

        # Estoque de segurança: 10% do consumo esperado até a chegada
        df["estoque_seguranca"] = df["consumo_ate_chegada"] * 0.1

        # Estoque ideal que deve estar disponível na chegada do caminhão
        df["estoque_ideal"] = df["consumo_ate_chegada"] + df["estoque_seguranca"]

        # Sugestão de compra: diferença entre o estoque ideal e o estoque atual (arredondada para cima)
        df["sugestao_compra"] = (df["estoque_ideal"] - df["estoque_atual"]).apply(lambda x: math.ceil(x) if x > 0 else 0)

        # Armazenar o resultado no session_state
        st.session_state.df_calculado = df

    if st.session_state.df_calculado is not None:
        st.subheader("Tabela de Sugestão de Compra")
        
        # Opção de filtro: exibir somente os produtos com sugestão de compra maior que 0
        filtrar = st.checkbox("Exibir apenas produtos com sugestão de compra > 0", value=False)
        df_exibicao = st.session_state.df_calculado.copy()
        if filtrar:
            df_exibicao = df_exibicao[df_exibicao["sugestao_compra"] > 0]

        st.dataframe(
            df_exibicao[["produto_id", "nome", "estoque_atual", "consumo_diario", "estoque_ideal", "sugestao_compra"]],
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

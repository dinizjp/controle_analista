# sugestao_compra.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import math
from utils import get_lojas, get_estoque_at_date, get_categorias, get_produtos, get_saidas_periodo  # Removido get_saidas_diarias

# Configuração da página
st.set_page_config(page_title="Sugestão de Compra", layout="wide")

# Inicializar o session_state para armazenar o DataFrame
if 'df_calculado' not in st.session_state:
    st.session_state.df_calculado = None

# Função principal da página
def page_sugestao_compra():
    """Página de sugestão de compra integrada com as funções do utils.py."""
    st.title("Sugestão de Compra")

    # Explicação detalhada das técnicas utilizadas
    st.markdown("""
        ### Como Funciona a Sugestão de Compra

        #### 1. Consumo Diário
        - **O que é**: É a quantidade média de um produto que sai do estoque por dia.
        - **Como calculamos**: Pegamos o total de saídas (vendas ou retiradas) do produto no período que você escolheu e dividimos pelo número de dias desse período. 
        
        #### 2. Ponto de Reordenamento (ROP)
        - **O que é**: É o estoque mínimo que você precisa ter para cobrir o consumo até a próxima entrega chegar.
        - **Como calculamos**: Multiplicamos o consumo diário médio pelo número de dias até a próxima entrega (o chamado "lead time") e somamos uma reserva extra, chamada "estoque de segurança".
        - **Lead Time**: É o tempo total até o produto chegar, contando a data da próxima rota mais o tempo de viagem.
        - **Estoque de Segurança**: Uma quantidade extra para imprevistos, como atrasos ou picos de demanda. Calculamos como 10% do consumo projetado para o lead time, arredondado para cima.
        - **Exemplo**: Se o consumo diário é 3 unidades, o lead time é 10 dias, e o estoque de segurança é 10% de (3 × 10) = 3 unidades, o ROP fica assim: (3 × 10) + 3 = 33 unidades.
        - **Por que usamos**: O ROP evita que o estoque acabe antes da próxima entrega, te dando uma margem de segurança.

        #### 3. Sugestão de Compra
        - **Como calculamos**: Se o estoque atual estiver abaixo do ROP, subtraímos o estoque atual do ROP e arredondamos para cima. Se o estoque atual já for igual ou maior que o ROP, a sugestão é zero.
        - **Exemplo**: Se o ROP é 33 e o estoque atual é 10, a sugestão é 33 - 10 = 23 unidades. Se o estoque atual for 35, a sugestão é 0.

""")

    # Seleção da loja
    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    selected_loja_str = st.selectbox("Selecione a loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]

    # Inputs de datas e parâmetros
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_inicial = st.date_input("Data Inicial", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        data_final = st.date_input("Data Final", datetime.date.today())
    with col3:
        data_proxima_rota = st.date_input("Data Próxima Rota", datetime.date.today() + datetime.timedelta(days=7))
    with col4:
        tempo_viagem = st.number_input("Tempo de Viagem (dias)", min_value=1, value=3)

    if st.button("Calcular Sugestão de Compra"):
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return

        # Obter estoque atual com base na data final
        estoque_atual_df = get_estoque_at_date(data_final, selected_loja_id).rename(columns={"quantidade_ajustada": "estoque_atual"})
        produtos_df = pd.DataFrame(get_produtos(), columns=["id", "nome", "categoria", "unidade_medida", "valor"])
        produtos_df = produtos_df[["id", "categoria", "nome"]].rename(columns={"id": "produto_id"})

        # Mesclar produtos com estoque atual
        df = pd.merge(produtos_df, estoque_atual_df[["produto_id", "estoque_atual"]], on="produto_id", how="left")
        df["estoque_atual"].fillna(0, inplace=True)
        df["estoque_atual"] = df["estoque_atual"].astype(int)  # Garantir que estoque_atual seja inteiro

        # Calcular consumo diário com base nas saídas do período
        saidas_df = get_saidas_periodo(data_inicial, data_final, selected_loja_id)
        df = pd.merge(df, saidas_df[["produto_id", "total_saidas"]], on="produto_id", how="left")
        df["total_saidas"].fillna(0, inplace=True)
        df["consumo_diario_mm"] = df["total_saidas"].apply(lambda x: math.ceil(x / dias_consumo) if dias_consumo > 0 else 0)

        # Calcular dias até a próxima entrega
        dias_proxima_entrega = (data_proxima_rota - data_final).days + tempo_viagem
        if dias_proxima_entrega < 0:
            st.error("A Data Próxima Rota deve ser posterior à Data Final.")
            return

        # Calcular estoque de segurança e ponto de recompra (ROP), arredondando para inteiro
        df["estoque_seguranca"] = df["consumo_diario_mm"].apply(lambda x: math.ceil(0.1 * x * dias_proxima_entrega))
        df["rop"] = (df["consumo_diario_mm"] * dias_proxima_entrega) + df["estoque_seguranca"]

        # Calcular sugestão de compra, garantindo inteiro
        df["sugestao_compra"] = df.apply(
            lambda row: math.ceil(row["rop"] - row["estoque_atual"]) if row["estoque_atual"] < row["rop"] else 0,
            axis=1
        )

        # Armazenar o resultado no session_state
        st.session_state.df_calculado = df

        # Exibir tabela de sugestão de compra
        st.subheader("Tabela de Sugestão de Compra")
        st.dataframe(
            df[["produto_id", "nome", "estoque_atual", "consumo_diario_mm", "rop", "sugestao_compra"]],
            use_container_width=True
        )


if __name__ == "__main__":
    page_sugestao_compra()
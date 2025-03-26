# sugestao_compra.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import math
from utils import get_lojas, get_estoque_at_date, get_categorias, get_produtos, get_saidas_periodo

# Configuração da página
st.set_page_config(page_title="Sugestão de Compra", layout="wide")

# Inicializar o session_state para armazenar o DataFrame
if 'df_calculado' not in st.session_state:
    st.session_state.df_calculado = None

# Função principal da página
def page_sugestao_compra():
    st.title("Sugestão de Compra")

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
    
    janela_media_movel = st.number_input("Janela da Média Móvel (dias)", min_value=1, value=7)

    if st.button("Calcular Sugestão de Compra"):
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return

        # Obter estoque atual ajustado com base em data_contagem
        estoque_atual_df = get_estoque_at_date(data_final, selected_loja_id).rename(columns={"quantidade_ajustada": "estoque_atual"})
        produtos_df = pd.DataFrame(get_produtos(), columns=["id", "nome", "categoria", "unidade_medida", "valor"])
        produtos_df = produtos_df[["id", "categoria", "nome"]].rename(columns={"id": "produto_id"})

        # Mesclar produtos com estoque atual
        df = pd.merge(produtos_df, estoque_atual_df[["produto_id", "estoque_atual"]], on="produto_id", how="left")
        df["estoque_atual"].fillna(0, inplace=True)

        # Obter todas as saídas do período em uma única consulta
        saidas_df = get_saidas_periodo(data_inicial, data_final, selected_loja_id)
        if not saidas_df.empty:
            # Pivotar os dados para ter produtos como colunas e dias como linhas
            saidas_pivot = saidas_df.pivot(index="dia", columns="produto_id", values="total_saidas").fillna(0)
            # Reindexar para garantir todos os dias no período
            saidas_pivot = saidas_pivot.reindex(pd.date_range(data_inicial, data_final), fill_value=0)
            # Calcular média móvel para todos os produtos de uma vez
            media_movel = saidas_pivot.rolling(window=janela_media_movel, min_periods=1).mean().iloc[-1]
            # Mapear a média móvel para o DataFrame principal
            df["consumo_diario_mm"] = df["produto_id"].map(media_movel).fillna(0)
        else:
            df["consumo_diario_mm"] = 0

        # Calcular dias até a próxima entrega
        dias_proxima_entrega = (data_proxima_rota - data_final).days + tempo_viagem
        if dias_proxima_entrega < 0:
            st.error("A Data Próxima Rota deve ser posterior à Data Final.")
            return

        # Calcular estoque de segurança e ROP
        estoque_seguranca = 0.1 * df["consumo_diario_mm"] * dias_proxima_entrega
        df["rop"] = (df["consumo_diario_mm"] * dias_proxima_entrega) + estoque_seguranca

        # Calcular sugestão de compra e arredondar para inteiro
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

    # Exibir gráfico se houver dados calculados
    if st.session_state.df_calculado is not None:
        df = st.session_state.df_calculado
        st.subheader("Gráfico de Sugestão de Compra")
        categorias = get_categorias()
        selected_categoria = st.selectbox("Selecione a categoria", ["Todas"] + categorias, key="categoria_grafico")
        if selected_categoria != "Todas":
            df_grafico = df[df["categoria"] == selected_categoria]
        else:
            df_grafico = df
        fig = px.bar(
            df_grafico,
            x="nome",
            y="sugestao_compra",
            labels={"nome": "Produto", "sugestao_compra": "Quantidade a Comprar"},
            title=f"Sugestão de Compra - Loja {selected_loja_str} (Categoria: {selected_categoria})"
            height=800
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    page_sugestao_compra()
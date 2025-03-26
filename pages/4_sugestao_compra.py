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
    Esta página ajuda a decidir quanto comprar de cada produto com base no consumo real e na previsão de necessidade até a próxima entrega. Veja as técnicas que usamos:

    1. **Consumo Diário**  
       - Calculamos o consumo diário usando as *saídas reais* registradas no sistema (não o CMV).  
       - Fórmula: Total de saídas no período ÷ Número de dias no período (arredondado para cima).  
       - Exemplo: 50 unidades saíram em 30 dias → \( 50 \div 30 = 1,67 \), arredondado para 2 unidades por dia.

    2. **Ponto de Reordenamento (ROP)**  
       - O ROP é o estoque mínimo necessário até a próxima entrega.  
       - Fórmula: (Consumo Diário Médio × Lead Time) + Estoque de Segurança (arredondado para cima).  
       - *Lead Time*: Dias até a próxima entrega (data da rota + tempo de viagem).  
       - *Estoque de Segurança*: 10% do consumo diário × lead time (arredondado para cima).  
       - Exemplo: Consumo = 3, Lead Time = 10 dias, Estoque de Segurança = \( 0,1 \times 3 \times 10 = 3 \) → ROP = \( 3 \times 10 + 3 = 33 \).

    3. **Sugestão de Compra**  
       - Quantidade a comprar para atingir o ROP.  
       - Fórmula: Se Estoque Atual < ROP, então ROP - Estoque Atual (arredondado para cima); senão, 0.  
       - Exemplo: ROP = 33, Estoque Atual = 10 → Sugestão = \( 33 - 10 = 23 \).

    Todos os valores são arredondados para cima para garantir quantidades inteiras e evitar faltas. Note que não usamos média móvel aqui, apenas o consumo médio do período selecionado.
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
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    page_sugestao_compra()
# sugestao_compra.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io
from utils import get_lojas, get_estoque_at_date, get_compras_periodo, get_estoque_all, get_categorias, get_produtos

# Configuração da página
st.set_page_config(page_title="Sugestão de Compra", layout="wide")

# Inicializar o session_state para armazenar o DataFrame
if 'df_calculado' not in st.session_state:
    st.session_state.df_calculado = None

# Função para converter DataFrame em Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sugestao_Compra')
    return output.getvalue()

# Função principal da página
def page_sugestao_compra():
    """Página de sugestão de compra integrada com as funções do utils.py."""
    st.title("Sugestão de Compra")

    # Introdução e explicação das fórmulas
    st.markdown("""
    ### Como Funciona a Sugestão de Compra
    Esta página calcula quanto comprar de cada produto com base no consumo passado e na previsão de necessidade até a próxima entrega. Aqui estão as fórmulas usadas:
    
    1. **CMV (Custo de Mercadoria Vendida)**: Estoque Inicial + Compras - Estoque Final
    2. **Dias de Consumo**: Data Final - Data Inicial
    3. **Consumo Diário**: CMV / Dias de Consumo
    4. **Estoque Necessário**: Consumo Diário × (Dias até Próxima Rota + Tempo de Viagem)
    5. **Falta ou Sobra**: Estoque Atual - Estoque Necessário
    6. **Sugestão de Compra**: Se houver falta (Falta ou Sobra < 0), comprar a quantidade faltante; caso contrário, 0.
    """)

    # Seleção da loja
    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    st.write("**Selecione a Loja**: Escolha a loja para a qual você quer calcular a sugestão de compra.")
    selected_loja_str = st.selectbox("Selecione a loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]

    # Inputs de datas e tempo de viagem com legendas
    st.markdown("### Filtros de Data e Viagem")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.write("**Último Inventário**: Estoque contado pela última vez (usado como referência inicial).")
        data_ultimo_inventario = st.date_input(
            "Data Último Inventário",
            datetime.date.today() - datetime.timedelta(days=5),
            help="Data do último inventário físico ou ajuste de estoque. Pode ser anterior ao período de análise."
        )
    
    with col2:
        st.write("**Data Inicial**: Início do período para calcular o consumo.")
        data_inicial = st.date_input(
            "Data Inicial",
            datetime.date.today() - datetime.timedelta(days=60),
            help="Data a partir da qual o consumo será analisado."
        )
    
    with col3:
        st.write("**Data Final**: Fim do período para calcular o consumo.")
        data_final = st.date_input(
            "Data Final",
            datetime.date.today(),
            help="Data até a qual o consumo será considerado (normalmente hoje)."
        )
    
    with col4:
        st.write("**Data Próxima Rota**: Quando o próximo pedido será entregue.")
        data_proxima_rota = st.date_input(
            "Data Próxima Rota",
            datetime.date.today() + datetime.timedelta(days=7),
            help="Data prevista para a próxima entrega de produtos."
        )
    
    with col5:
        st.write("**Tempo de Viagem (dias)**: Quantos dias o pedido leva para chegar após a rota.")
        tempo_viagem = st.number_input(
            "Tempo de Viagem (dias)",
            min_value=1,
            value=3,
            help="Tempo em dias entre o pedido e a chegada do estoque."
        )

    # Botão para calcular a sugestão
    st.write("Clique abaixo para calcular a sugestão de compra com base nos dados inseridos.")
    if st.button("Calcular Sugestão de Compra"):
        # Validação de datas: garantir que data_final seja posterior a data_inicial
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return

        # Obter dados de estoque e compras usando utils.py
        estoque_inicial_df = get_estoque_at_date(data_inicial, selected_loja_id).rename(
            columns={"quantidade": "quantidade_inicial"}
        )
        estoque_final_df = get_estoque_at_date(data_final, selected_loja_id).rename(
            columns={"quantidade": "quantidade_final"}
        )
        compras_df = get_compras_periodo(data_inicial, data_final, selected_loja_id)
        estoque_atual_df = get_estoque_all(selected_loja_id).rename(
            columns={"quantidade": "estoque_atual"}
        )

        # Adicionar categorias ao DataFrame
        produtos_df = pd.DataFrame(get_produtos(), columns=["id", "nome", "categoria", "unidade_medida", "valor"])
        produtos_df = produtos_df[["id", "categoria"]].rename(columns={"id": "produto_id"})

        # Mesclar os dados em um único DataFrame
        df = pd.merge(estoque_inicial_df, estoque_final_df, on=["produto_id", "nome"], how="outer")
        df = pd.merge(df, compras_df, on="produto_id", how="outer")
        df = pd.merge(df, estoque_atual_df[["produto_id", "estoque_atual"]], on="produto_id", how="outer")
        df = pd.merge(df, produtos_df, on="produto_id", how="outer")

        # Preencher valores nulos com 0 para cálculos
        df.fillna(0, inplace=True)

        # Calcular CMV (Custo de Mercadoria Vendida)
        df["cmv"] = df["quantidade_inicial"] + df["total_compras"] - df["quantidade_final"]

        # Calcular Consumo Diário usando o período entre data_inicial e data_final
        df["consumo_diario"] = df["cmv"] / dias_consumo

        # Calcular dias até a próxima entrega
        dias_proxima_entrega = (data_proxima_rota - data_final).days + tempo_viagem
        if dias_proxima_entrega < 0:
            st.error("A Data Próxima Rota deve ser posterior à Data Final.")
            return

        # Calcular Estoque Necessário
        df["estoque_necessario"] = df["consumo_diario"] * dias_proxima_entrega

        # Calcular Falta ou Sobra
        df["falta_sobra"] = df["estoque_atual"] - df["estoque_necessario"]

        # Calcular Sugestão de Compra (somente se houver falta)
        df["sugestao_compra"] = df["falta_sobra"].apply(lambda x: -x if x < 0 else 0)

        # Armazenar o DataFrame no session_state
        st.session_state.df_calculado = df

        # Exibir tabela com os resultados (todos os produtos)
        st.subheader("Tabela de Sugestão de Compra")
        st.write("""
        Aqui estão os resultados para todos os produtos:
        - **Produto ID**: Identificador único do produto.
        - **Nome**: Nome do produto.
        - **Estoque Atual**: Quantidade disponível hoje.
        - **Estoque Necessário**: Quantidade estimada até a próxima entrega.
        - **Falta/Sobra**: Diferença entre atual e necessário (positivo = sobra, negativo = falta).
        - **Sugestão de Compra**: Quantidade a comprar (se houver falta).
        """)
        st.dataframe(
            df[["produto_id", "nome", "estoque_atual", "estoque_necessario", "falta_sobra", "sugestao_compra"]],
            use_container_width=True
        )

        # Botão para baixar a tabela em Excel
        excel_data = to_excel(df[["produto_id", "nome", "estoque_atual", "estoque_necessario", "falta_sobra", "sugestao_compra"]])
        st.download_button(
            label="Baixar Tabela em Excel",
            data=excel_data,
            file_name=f"sugestao_compra_{selected_loja_str}_{data_final.strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Exibir o gráfico apenas se o cálculo já foi feito
    if st.session_state.df_calculado is not None:
        df = st.session_state.df_calculado

        # Filtro de categorias para o gráfico
        st.subheader("Gráfico de Sugestão de Compra")
        st.write("Escolha uma categoria para visualizar a sugestão de compra no gráfico:")
        categorias = get_categorias()
        selected_categoria = st.selectbox("Selecione a categoria", ["Todas"] + categorias, key="categoria_grafico")
        
        # Filtrar o DataFrame para o gráfico
        if selected_categoria != "Todas":
            df_grafico = df[df["categoria"] == selected_categoria]
        else:
            df_grafico = df

        st.write("Este gráfico mostra a quantidade sugerida para compra dos produtos da categoria selecionada.")
        fig = px.bar(
            df_grafico,
            x="nome",
            y="sugestao_compra",
            labels={"nome": "Produto", "sugestao_compra": "Quantidade a Comprar"},
            title=f"Sugestão de Compra - Loja {selected_loja_str} (Categoria: {selected_categoria})",
            height=800
        )
        st.plotly_chart(fig, use_container_width=True)

# Execução da página (se standalone, senão remova essa parte)
if __name__ == "__main__":
    page_sugestao_compra()
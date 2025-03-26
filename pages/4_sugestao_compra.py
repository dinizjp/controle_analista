# sugestao_compra.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from utils import get_lojas, get_estoque_at_date, get_compras_periodo, get_estoque_all, get_categorias, get_produtos, get_saidas_periodo

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
       - Fórmula: Total de saídas no período ÷ Número de dias no período.  
       - Isso reflete o que foi realmente consumido ou vendido.

    2. **Média Móvel Simples**  
       - Usamos o pandas para suavizar o consumo diário com uma média móvel.  
       - Exemplo: Se você escolher uma janela de 7 dias, a média considera os últimos 7 dias de consumo para reduzir variações bruscas.  
       - Isso ajuda a prever o consumo futuro de forma mais estável.

    3. **Ponto de Reordenamento (ROP)**  
       - O ROP é o estoque mínimo que você precisa para evitar faltas até a próxima entrega.  
       - Fórmula: (Consumo Diário Médio × Lead Time) + Estoque de Segurança.  
       - *Lead Time*: Dias até a próxima entrega (data da rota + tempo de viagem).  
       - *Estoque de Segurança*: Uma reserva extra (10% do consumo diário × lead time) para imprevistos.

    4. **Sugestão de Compra**  
       - Se o estoque atual for menor que o ROP, sugerimos comprar o que falta (ROP - Estoque Atual).  
       - Se o estoque atual for suficiente, a sugestão é 0.

    Essas técnicas garantem que você tenha estoque suficiente sem exagerar nas compras!
    """)

    # Seleção da loja
    lojas = get_lojas()
    loja_options = {f"{l[0]} - {l[1]}": l[0] for l in lojas}
    st.write("**Selecione a Loja**: Escolha a loja para a qual você quer calcular a sugestão de compra.")
    selected_loja_str = st.selectbox("Selecione a loja", list(loja_options.keys()))
    selected_loja_id = loja_options[selected_loja_str]

    # Inputs de datas e parâmetros
    st.markdown("### Filtros de Data e Configuração")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.write("**Data Inicial**: Início do período para analisar o consumo.")
        data_inicial = st.date_input(
            "Data Inicial",
            datetime.date.today() - datetime.timedelta(days=30)
        )
    
    with col2:
        st.write("**Data Final**: Fim do período (geralmente hoje).")
        data_final = st.date_input(
            "Data Final",
            datetime.date.today()
        )
    
    with col3:
        st.write("**Data Próxima Rota**: Quando o próximo pedido chega.")
        data_proxima_rota = st.date_input(
            "Data Próxima Rota",
            datetime.date.today() + datetime.timedelta(days=7)
        )
    
    with col4:
        st.write("**Tempo de Viagem (dias)**: Dias até o estoque chegar após a rota.")
        tempo_viagem = st.number_input(
            "Tempo de Viagem (dias)",
            min_value=1,
            value=3
        )
    
    with col5:
        st.write("**Janela da Média Móvel (dias)**: Período para suavizar o consumo.")
        janela_media_movel = st.number_input(
            "Janela da Média Móvel (dias)",
            min_value=1,
            value=7
        )

    # Botão para calcular
    if st.button("Calcular Sugestão de Compra"):
        # Validar datas
        dias_consumo = (data_final - data_inicial).days
        if dias_consumo <= 0:
            st.error("A Data Final deve ser posterior à Data Inicial.")
            return

        # Obter saídas e estoque atual
        saidas_df = get_saidas_periodo(data_inicial, data_final, selected_loja_id)
        estoque_atual_df = get_estoque_all(selected_loja_id).rename(
            columns={"quantidade": "estoque_atual"}
        )

        # Dados dos produtos (com categoria e nome)
        produtos_df = pd.DataFrame(get_produtos(), columns=["id", "nome", "categoria", "unidade_medida", "valor"])
        produtos_df = produtos_df[["id", "categoria", "nome"]].rename(columns={"id": "produto_id"})

        # Mesclar dados
        df = pd.merge(produtos_df, saidas_df, on="produto_id", how="left")
        df = pd.merge(df, estoque_atual_df[["produto_id", "estoque_atual"]], on="produto_id", how="left")
        df.fillna(0, inplace=True)

        # Calcular consumo diário com base nas saídas reais
        df["consumo_diario"] = df["total_saidas"] / dias_consumo

        # Aplicar média móvel simples com pandas
        if janela_media_movel > 0 and dias_consumo >= janela_media_movel:
            df["consumo_diario_mm"] = df["consumo_diario"].rolling(
                window=janela_media_movel, min_periods=1
            ).mean()
        else:
            df["consumo_diario_mm"] = df["consumo_diario"]

        # Calcular lead time (dias até a próxima entrega)
        dias_proxima_entrega = (data_proxima_rota - data_final).days + tempo_viagem
        if dias_proxima_entrega < 0:
            st.error("A Data Próxima Rota deve ser posterior à Data Final.")
            return

        # Calcular estoque de segurança (10% do consumo diário médio × lead time)
        estoque_seguranca = 0.1 * df["consumo_diario_mm"] * dias_proxima_entrega

        # Calcular Ponto de Reordenamento (ROP)
        df["rop"] = (df["consumo_diario_mm"] * dias_proxima_entrega) + estoque_seguranca

        # Calcular sugestão de compra
        df["sugestao_compra"] = df.apply(
            lambda row: row["rop"] - row["estoque_atual"] if row["estoque_atual"] < row["rop"] else 0,
            axis=1
        )

        # Armazenar no session_state
        st.session_state.df_calculado = df

        # Exibir resultados
        st.subheader("Tabela de Sugestão de Compra")
        st.write("Aqui está a sugestão de compra para todos os produtos:")
        st.dataframe(
            df[["produto_id", "nome", "estoque_atual", "consumo_diario_mm", "rop", "sugestao_compra"]],
            use_container_width=True
        )

    # Gráfico (se já calculado)
    if st.session_state.df_calculado is not None:
        df = st.session_state.df_calculado
        st.subheader("Gráfico de Sugestão de Compra")
        categorias = get_categorias()
        selected_categoria = st.selectbox("Selecione a categoria", ["Todas"] + categorias, key="categoria_grafico")
        
        # Filtrar por categoria
        if selected_categoria != "Todas":
            df_grafico = df[df["categoria"] == selected_categoria]
        else:
            df_grafico = df

        fig = px.bar(
            df_grafico,
            x="nome",
            y="sugestao_compra",
            labels={"nome": "Produto", "sugestao_compra": "Quantidade a Comprar"},
            title=f"Sugestão de Compra - Loja {selected_loja_str} (Categoria: {selected_categoria})",
            height=800
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    page_sugestao_compra()
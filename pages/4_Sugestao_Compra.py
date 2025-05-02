import streamlit as st
import datetime as dt
import io
import math
import pandas as pd

from utils import  get_lojas, calc_sugestao_compra

st.set_page_config(page_title="Sugestão de Compra", layout="wide")

def to_excel(df: pd.DataFrame) -> bytes:
    """Converte DataFrame para bytes Excel."""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sugestao")
    return out.getvalue()


def page_sugestao_compra():
    st.title("Sugestão de Compra")
    
    st.markdown("""
    **1.** Selecione o período de consumo  
    **2.** Informe a Data de Chegada do Caminhão  
    **3.** Defina a periodicidade da rota (em dias)  
    **4.** Clique em **Calcular Sugestão de Compra**
    """)
    
    # 1) Seleção da loja
    lojas = get_lojas()
    loja_opts = {f"{lid} – {nome}": lid for lid, nome in lojas}
    sel_loja = st.selectbox("Selecione a Loja", list(loja_opts.keys()))
    loja_id = loja_opts[sel_loja]
    
    # 2) Datas e periodicidade
    col1, col2, col3, col4 = st.columns(4)
    hoje = dt.date.today()
    with col1:
        data_inicial = st.date_input("Período Início", hoje - dt.timedelta(days=30))
    with col2:
        data_final = st.date_input("Período Fim (Foto do Estoque)", hoje)
    with col3:
        data_caminhao = st.date_input("Data Chegada Caminhão", hoje + dt.timedelta(days=5))
    with col4:
        periodicidade = st.number_input("Periodicidade da Rota (dias)", min_value=1, value=30)
    
    if st.button("🔢 Calcular Sugestão de Compra"):
        # chama a função única que já retorna todas as colunas necessárias
        try:
            df = calc_sugestao_compra(
                loja_id,
                data_inicial,
                data_final,
                data_caminhao,
                periodicidade
            )
        except ValueError as e:
            st.error(str(e))
            return
        
        if df["sugestao_unidade_compra"].sum() == 0:
            st.warning("Não há produtos com sugestão de compra maior que zero.")
            st.dataframe(df, use_container_width=True)
            return
        
        # opçã o para filtrar apenas >0
        if st.checkbox("Mostrar somente itens com sugestão > 0", value=True):
            df = df[df["sugestao_unidade_compra"] > 0]
        
        st.subheader("Tabela de Sugestão de Compra")
        st.dataframe(df, use_container_width=True)
        
        excel_bytes = to_excel(df)
        st.download_button(
            "📥 Baixar Sugestão em Excel",
            data=excel_bytes,
            file_name="sugestao_compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


if __name__ == "__main__":
    page_sugestao_compra()

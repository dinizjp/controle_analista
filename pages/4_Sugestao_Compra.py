import streamlit as st
import datetime as dt
import io
import pandas as pd

from utils import get_lojas, calc_sugestao_compra

st.set_page_config(page_title="Sugestão de Compra", layout="wide")

def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sugestao")
    return buf.getvalue()

def page_sugestao_compra():
    st.title("Sugestão de Compra")
    # 1) Loja
    lojas = get_lojas()
    opts  = {f"{lid} – {nome}": lid for lid,nome in lojas}
    sel   = st.selectbox("Selecione a Loja", list(opts.keys()))
    loja_id = opts[sel]

    # 2) Datas e periodicidade
    col1, col2, col3, col4 = st.columns(4)
    hoje = dt.date.today()
    with col1:
        data_inicial = st.date_input("Período Início", hoje - dt.timedelta(days=30))
    with col2:
        data_final = st.date_input("Período Fim (Foto do Estoque)", hoje)
    with col3:
        data_caminhao = st.date_input("Chegada do Caminhão", hoje + dt.timedelta(days=5))
    with col4:
        periodicidade = st.number_input("Periodicidade (dias)", min_value=1, value=30)

    if st.button("🔢 Calcular Sugestão de Compra"):
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

        # se não houver nada para comprar em unidade de compra
        if df["sugestao_unidade_compra"].sum() == 0:
            st.warning("Nenhum item com sugestão de compra > 0.")
            st.dataframe(df, use_container_width=True)
            return

        # filtro opcional
        if st.checkbox("Mostrar só sugestões > 0", value=True):
            df = df[df["sugestao_unidade_compra"] > 0]

        st.subheader("Tabela de Sugestão de Compra")
        st.dataframe(df, use_container_width=True)

        excel = to_excel(df)
        st.download_button(
            "📥 Baixar Sugestão (Excel)",
            data=excel,
            file_name="sugestao_compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    page_sugestao_compra()

# 4_Sugestao_Compra.py
import streamlit as st
import datetime as dt
import io
import pandas as pd
from dateutil.relativedelta import relativedelta
from utils import get_lojas, calc_sugestao_compra, get_historico_mensal, create_purchase_order, get_purchase_orders, get_purchase_order_items
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.set_page_config(page_title="Sugestão de Compra", layout="wide")

def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sugestao")
    return buf.getvalue()

def to_excel_items(df: pd.DataFrame, pedido_id: int) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=f"Itens_Pedido_{pedido_id}")
    return buf.getvalue()

def page_sugestao_compra():
    st.title("Sugestão e Pedido de Compra")

    # 1) Seleção de loja
    lojas = get_lojas()
    opts  = {f"{lid} – {nome}": lid for lid,nome in lojas}
    sel   = st.selectbox("Selecione a Loja", list(opts.keys()))
    loja_id = opts[sel]

    # 2) Datas e periodicidade
    col1, col2, col3, col4 = st.columns(4)
    hoje = dt.date.today()
    with col1:
        data_inicial  = st.date_input("Período Início", hoje - dt.timedelta(days=30))
    with col2:
        data_final    = st.date_input("Período Fim", hoje)
    with col3:
        data_caminhao = st.date_input("Chegada do Caminhão", hoje + dt.timedelta(days=5))
    with col4:
        periodicidade = st.number_input("Periodicidade (dias)", min_value=1, value=30)

    # 3) Gerar sugestão
    if st.button("🔢 Gerar Sugestão"):
        try:
            df_sug = calc_sugestao_compra(loja_id, data_inicial, data_final, data_caminhao, periodicidade)
        except ValueError as e:
            st.error(str(e))
            return

        df_sug = df_sug[df_sug["sugestao_unidade_compra"] > 0]
        if df_sug.empty:
            st.warning("Nenhum item com sugestão > 0.")
            return

        # Histórico mensal 3 meses
        df_hist = get_historico_mensal(loja_id, meses=3)

        # Merge evitando duplicatas
        df = df_sug.merge(df_hist, on="produto_id", how="left", suffixes=("", "_hist"))

        # Definir colunas de histórico para o mês anterior
        ultimo = hoje - relativedelta(months=1)
        inv_col = f"inv_{ultimo:%Y_%m}"
        sai_col = f"sai_{ultimo:%Y_%m}"
        ent_col = f"ent_{ultimo:%Y_%m}"

        # Selecionar e renomear colunas
        df_sel = df[[
            "produto_id", "nome", "categoria",
            "sugestao_unidade_compra",
            inv_col, sai_col, ent_col
        ]].copy()

        df_sel.rename(columns={
            "sugestao_unidade_compra": "Sugestão de Compra",
            inv_col: f"Inventário {ultimo:%m/%Y}",
            sai_col: f"Saídas {ultimo:%m/%Y}",
            ent_col: f"Entradas {ultimo:%m/%Y}"
        }, inplace=True)

        # Ordenar por categoria personalizada
        cat_order = [
            "Açaí",
            "Sorvetes",
            "Polpa",
            "Complementos",
            "Embalagens Distribuidora",
            "Uso e Consumo"
        ]
        df_sel["categoria"] = pd.Categorical(df_sel["categoria"], categories=cat_order, ordered=True)
        df_sel.sort_values(["categoria", "nome"], inplace=True)

        st.subheader("Tabela de Sugestão de Compra")

        # Configurar AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_sel)
        gb.configure_default_column(resizable=True, filter=True, sortable=True, editable=False)
        gb.configure_column("Sugestão de Compra", editable=True)
        grid_opts = gb.build()

        grid_response = AgGrid(
            df_sel,
            gridOptions=grid_opts,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False
        )
        df_edit = pd.DataFrame(grid_response["data"])

        # 4) Salvar pedido
        if st.button("💾 Salvar como Pedido"):
            itens = [
                {"produto_id": int(row["produto_id"]), "quantidade": int(row["Sugestão de Compra"])}
                for _, row in df_edit.iterrows()
            ]
            order_id = create_purchase_order(loja_id, itens)
            st.success(f"Pedido {order_id} criado com sucesso!")
            st.experimental_rerun()

        # 5) Download Excel da sugestão
        excel = to_excel(df_sel)
        st.download_button(
            "📥 Baixar Sugestão (Excel)",
            data=excel,
            file_name="sugestao_compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")

    # 6) Consultar pedidos existentes
    st.subheader("Consultar Pedidos Existentes")
    df_orders = get_purchase_orders(loja_id)
    if df_orders.empty:
        st.info("Nenhum pedido para esta loja.")
        return

    sel_id = st.selectbox("Selecione o Pedido", df_orders["id"].astype(str))
    criado_em = df_orders.set_index("id").loc[int(sel_id), "data_criacao"]
    st.write("Criado em:", criado_em)

    df_items = get_purchase_order_items(int(sel_id))
    st.dataframe(df_items, use_container_width=True)
    excel_itens = to_excel_items(df_items, int(sel_id))
    st.download_button(
        "📥 Baixar Itens do Pedido",
        data=excel_itens,
        file_name=f"itens_pedido_{sel_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet"
    )

if __name__ == "__main__":
    page_sugestao_compra()

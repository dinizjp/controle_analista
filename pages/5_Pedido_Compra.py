import streamlit as st
import pandas as pd
import datetime as dt
import io

from utils import get_lojas, calc_sugestao_compra, create_purchase_order, get_purchase_orders, get_purchase_order_items


def to_excel(df: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Pedido")
    return out.getvalue()

def page_pedido_compra():
    st.title("Gerar e Consultar Pedidos de Compra")

    # --- seleção de loja e período ---
    lojas = get_lojas()
    opts = {f"{lid} – {nome}": lid for lid, nome in lojas}
    sel = st.selectbox("Selecione a loja", list(opts.keys()), key="pc_loja")
    loja_id = opts[sel]

    col1, col2, col3 = st.columns(3)
    hoje = dt.date.today()
    with col1:
        data_inicio = st.date_input("Início do Período", hoje - dt.timedelta(days=30))
    with col2:
        data_fim = st.date_input("Fim do Período", hoje)
    with col3:
        periodicidade = st.number_input("Periodicidade (dias)", min_value=1, value=30)

    # --- gerar pedido ---
    if st.button("Gerar Pedido de Compra Consolidado"):
        try:
            df_sug = calc_sugestao_compra(
                loja_id,
                data_inicio,
                data_fim,
                data_fim + dt.timedelta(days=periodicidade),
                periodicidade
            )
        except ValueError as e:
            st.error(str(e))
            return

        # monta itens apenas com unidades de saída > 0
        itens = [
            {"produto_id": row["produto_id"],
             "quantidade": int(row["sugestao_unidade_compra"])}
            for _, row in df_sug.iterrows()
            if row["sugestao_unidade_compra"] > 0
        ]

        if not itens:
            st.warning("Nenhum item com sugestão de compra > 0.")
        else:
            order_id = create_purchase_order(loja_id, itens)
            st.success(f"Pedido #{order_id} criado com sucesso!")

            # prepara tabela para download
            df_order = df_sug.loc[
                df_sug["sugestao_unidade_compra"] > 0,
                ["produto_id", "nome", "sugestao_compra", "sugestao_unidade_compra"]
            ].rename(columns={
                "sugestao_compra": "faltante_un_entrada",
                "sugestao_unidade_compra": "quantidade_comprar_un_saida"
            })

            excel = to_excel(df_order)
            st.download_button(
                "📥 Baixar Pedido (Excel)",
                data=excel,
                file_name=f"pedido_{order_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")

    # --- consulta de pedidos existentes ---
    st.subheader("Consultar Pedidos Existentes")
    df_orders = get_purchase_orders(loja_id)
    if df_orders.empty:
        st.info("Nenhum pedido para esta loja.")
        return

    sel_id = st.selectbox("Selecione o Pedido", df_orders["id"].astype(str))
    st.write("Criado em:", df_orders.set_index("id").loc[int(sel_id), "data_criacao"])

    df_items = get_purchase_order_items(int(sel_id))
    st.dataframe(df_items, use_container_width=True)
    excel_itens = to_excel(df_items)
    st.download_button(
        "📥 Baixar Itens do Pedido",
        data=excel_itens,
        file_name=f"itens_pedido_{sel_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    page_pedido_compra()

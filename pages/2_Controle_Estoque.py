# pages/2_Correções_Estoque.py
import streamlit as st
from utils import (
    get_lojas,
    get_produtos,
    get_estoque_loja,
    corrigir_acrescentar,
    corrigir_remover,
    corrigir_transferir,
)

st.set_page_config(page_title="Correções de Estoque - Analista", layout="wide")

def page_correcoes_estoque():
    st.title("Correções de Estoque - Manutenção")
    st.write("Utilize esta página para corrigir erros no lançamento do estoque.")

    # 1) Operação
    operacao = st.radio(
        "Selecione o tipo de operação",
        ["Acrescentar", "Remover", "Transferir"],
        horizontal=True
    )

    # 2) Carrega lojas e produtos
    lojas = get_lojas()  # [(id, nome), ...]
    lojas_dict = {f"{lid} - {nome}": lid for lid, nome in lojas}

    produtos_df = get_produtos()  # DataFrame com colunas produto_id, nome, categoria, un_saida, un_entrada, conversao
    # Monta lista de opções "id - nome" e um dicionário de mapeamento pra trás
    prod_options = [
        f"{int(row.produto_id)} - {row.nome}"
        for row in produtos_df.itertuples()
    ]
    prod_map = {
        opt: int(opt.split(" - ")[0])
        for opt in prod_options
    }

    # --- Acrescentar / Remover ---
    if operacao in ["Acrescentar", "Remover"]:
        st.subheader(f"{operacao} estoque")

        # Seleção de loja
        loja_sel = st.selectbox("Selecione a loja", list(lojas_dict.keys()))
        loja_id = lojas_dict[loja_sel]

        # Seleção de produto
        produto_sel = st.selectbox("Selecione o produto", prod_options)
        produto_id = prod_map[produto_sel]

        # Quantidade disponível (no estoque atual)
        estoque = get_estoque_loja(loja_id)  # [(produto_id, nome, quantidade), ...]
        qtd_disp = {item[0]: item[2] for item in estoque}.get(produto_id, 0)
        st.info(f"Quantidade disponível: {qtd_disp}")

        # Entradas do usuário
        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
        observacao = st.text_input("Observação (opcional)")

        if st.button("Executar Operação"):
            if operacao == "Acrescentar":
                corrigir_acrescentar(loja_id, produto_id, quantidade, observacao)
                st.success("Estoque corrigido (acréscimo) com sucesso!")
            else:
                corrigir_remover(loja_id, produto_id, quantidade, observacao)
                st.success("Estoque corrigido (remoção) com sucesso!")

    # --- Transferir ---
    else:
        st.subheader("Transferir estoque entre lojas")

        # Seleção de loja de origem e destino
        origem_sel = st.selectbox("Selecione a loja de ORIGEM", list(lojas_dict.keys()), key="origem")
        loja_origem = lojas_dict[origem_sel]
        dest_sel = st.selectbox("Selecione a loja de DESTINO", list(lojas_dict.keys()), key="destino")
        loja_destino = lojas_dict[dest_sel]

        # Seleção de produto
        produto_sel = st.selectbox("Selecione o produto", prod_options, key="transf_produto")
        produto_id = prod_map[produto_sel]

        # Quantidade disponível na loja de origem
        estoque_origem = get_estoque_loja(loja_origem)
        qtd_disp = {item[0]: item[2] for item in estoque_origem}.get(produto_id, 0)
        st.info(f"Quantidade disponível na loja de origem: {qtd_disp}")

        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)

        if st.button("Executar Transferência"):
            if loja_origem == loja_destino:
                st.error("A loja de origem e a loja de destino devem ser diferentes!")
            else:
                corrigir_transferir(loja_origem, loja_destino, produto_id, quantidade)
                st.success("Transferência registrada com sucesso!")

if __name__ == "__main__":
    page_correcoes_estoque()

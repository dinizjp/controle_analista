# pages/2_Correções_Estoque.py
import streamlit as st
from utils import get_lojas, get_produtos, get_estoque_loja, corrigir_acrescentar, corrigir_remover, corrigir_transferir

st.set_page_config(page_title='Correções de Estoque - Analista', layout='wide')

def page_correcoes_estoque():
    st.title("Correções de Estoque - Manutenção")
    st.write("Utilize esta página para corrigir erros no lançamento do estoque.")

    operacao = st.radio("Selecione o tipo de operação", ["Acrescentar", "Remover", "Transferir"])
    lojas = get_lojas()
    produtos = get_produtos()

    if operacao in ["Acrescentar", "Remover"]:
        st.subheader(f"{operacao} estoque")
        lojas_dict = {f"{loja[0]} - {loja[1]}": loja[0] for loja in lojas}
        loja_id = lojas_dict[st.selectbox("Selecione a loja", list(lojas_dict.keys()))]

        produtos_dict = {f"{p[0]} - {p[1]}": p[0] for p in produtos}
        produto_id = produtos_dict[st.selectbox("Selecione o produto", list(produtos_dict.keys()))]

        estoque = get_estoque_loja(loja_id)
        qtd_disp = {p[0]: p[2] for p in estoque}.get(produto_id, 0)
        st.info(f"Quantidade disponível: {qtd_disp}")

        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
        observacao = st.text_input("Observação (opcional)")

        if st.button("Executar Operação"):
            if operacao == "Acrescentar":
                corrigir_acrescentar(loja_id, produto_id, quantidade, observacao)
                st.success("Estoque corrigido (acréscimo) com sucesso!")
            else:
                corrigir_remover(loja_id, produto_id, quantidade, observacao)
                st.success("Estoque corrigido (remoção) com sucesso!")

    elif operacao == "Transferir":
        st.subheader("Transferir estoque entre lojas")
        lojas_dict = {f"{loja[0]} - {loja[1]}": loja[0] for loja in lojas}
        loja_origem = lojas_dict[st.selectbox("Selecione a loja de ORIGEM", list(lojas_dict.keys()))]
        loja_destino = lojas_dict[st.selectbox("Selecione a loja de DESTINO", list(lojas_dict.keys()))]

        produtos_dict = {f"{p[0]} - {p[1]}": p[0] for p in produtos}
        produto_id = produtos_dict[st.selectbox("Selecione o produto", list(produtos_dict.keys()))]

        estoque_origem = get_estoque_loja(loja_origem)
        qtd_disp = {p[0]: p[2] for p in estoque_origem}.get(produto_id, 0)
        st.info(f"Quantidade disponível na loja de origem: {qtd_disp}")

        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)

        if st.button("Executar Transferência"):
            if loja_origem == loja_destino:
                st.error("A loja de origem e destino devem ser diferentes!")
            else:
                corrigir_transferir(loja_origem, loja_destino, produto_id, quantidade)
                st.success("Transferência registrada com sucesso!")

def main():
    page_correcoes_estoque()

if __name__ == "__main__":
    main()
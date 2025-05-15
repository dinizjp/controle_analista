# home_page.py
import streamlit as st
from utils import get_lojas, add_loja, update_loja

st.set_page_config(page_title='Programa Analista', layout='wide')

def page_lojas():
    st.title("Gerenciar Lojas")
    st.write("Adicione uma nova loja ou edite uma existente.")

    # Adicionar nova loja
    st.subheader("Adicionar Nova Loja")
    with st.form("add_loja_form"):
        nova_loja_id = st.number_input(
            "ID da nova loja",
            min_value=1,
            step=1,
            help="Escolha um ID numérico único"
        )
        nova_loja_nome = st.text_input("Nome da nova loja")
        submitted_add = st.form_submit_button("Adicionar Loja")
        if submitted_add:
            if not nova_loja_nome:
                st.error("Por favor, informe o nome da loja.")
            else:
                try:
                    add_loja(int(nova_loja_id), nova_loja_nome)
                    st.success(f"Loja '{nova_loja_nome}' (ID {nova_loja_id}) adicionada com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao adicionar loja: {e}")

    # Editar loja existente
    st.subheader("Editar Loja Existente")
    lojas = get_lojas()
    if lojas:
        lojas_dict = {f"{loja[0]} – {loja[1]}": loja for loja in lojas}
        loja_selecionada = st.selectbox("Selecione a loja para editar", list(lojas_dict.keys()))
        if loja_selecionada:
            loja_id, loja_nome = lojas_dict[loja_selecionada]
            novo_nome = st.text_input("Novo nome para a loja", value=loja_nome)
            if st.button("Atualizar Loja"):
                if novo_nome and novo_nome != loja_nome:
                    try:
                        update_loja(loja_id, novo_nome)
                        st.success(f"Loja atualizada para '{novo_nome}' com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar loja: {e}")
                else:
                    st.info("Nenhuma alteração foi feita.")
    else:
        st.info("Nenhuma loja cadastrada ainda.")

def main():
    page_lojas()

if __name__ == "__main__":
    main()

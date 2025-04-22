import streamlit as st
from utils import get_lojas, registrar_entrada_xml
import pandas as pd
import xmltodict
import json
import datetime as dt

st.set_page_config(page_title="Lançamento via XML", layout="wide")

def page_xml_lancamento():
    st.title("Lançamento de Produtos via XML")
    st.markdown("Faça o upload do arquivo XML com os lançamentos de produtos.")

    # Seleção da loja
    lojas = get_lojas()
    if not lojas:
        st.error("Nenhuma loja encontrada. Cadastre uma loja antes de continuar.")
        return
    lojas_dict = {f"{loja[0]} - {loja[1]}": loja[0] for loja in lojas}
    loja_id = lojas_dict[st.selectbox("Selecione a loja", list(lojas_dict.keys()))]

    # Upload do XML
    uploaded_file = st.file_uploader("Selecione o arquivo XML", type=["xml"])
    if uploaded_file:
        # Verificar se o arquivo mudou ou se é o primeiro upload
        if ("uploaded_file_name" not in st.session_state or 
            st.session_state.uploaded_file_name != uploaded_file.name):
            st.session_state.uploaded_file_name = uploaded_file.name
            try:
                xml_content = uploaded_file.read()
                xml_dict = xmltodict.parse(xml_content)
                json_data = json.loads(json.dumps(xml_dict))
                items = json_data.get("nfeProc", {}).get("NFe", {}).get("infNFe", {}).get("det")
                if items is None:
                    st.error("Não foram encontrados itens no XML.")
                    return
                if not isinstance(items, list):
                    items = [items]
                product_list = [
                    {
                        "id": item.get("prod", {}).get("cProd", ""),
                        "quantidade": item.get("prod", {}).get("qCom", ""),
                        "motivo": "Entrada via XML",
                        "data": dt.datetime.now().isoformat()
                    }
                    for item in items
                ]
                st.session_state.df_products = pd.DataFrame(product_list)
            except Exception as e:
                st.error(f"Erro ao processar o arquivo XML: {e}")
                return

        # Seção para ajustar a data em massa
        st.subheader("Ajustar Data para Todos os Produtos")
        selected_date = st.date_input("Selecione a data", value=dt.date.today())
        if st.button("Aplicar Data a Todos"):
            current_time = dt.datetime.now().time()
            selected_datetime = dt.datetime.combine(selected_date, current_time)
            st.session_state.df_products["data"] = selected_datetime.isoformat()
            st.success("Data aplicada a todos os produtos com sucesso!")

        # Exibir e permitir edição do DataFrame
        st.markdown("### Visualize e Edite os Lançamentos")
        edited_df = st.data_editor(
            st.session_state.df_products,
            num_rows="dynamic",
            key="data_editor"
        )
        # Atualizar o session_state com as edições feitas
        st.session_state.df_products = edited_df

        # Botão para confirmar o lançamento
        if st.button("Confirmar Lançamento"):
            registrar_entrada_xml(loja_id, st.session_state.df_products.to_dict(orient="records"))
            st.success("Produtos lançados com sucesso!")
            # Limpar o session_state após o lançamento
            del st.session_state.df_products
            if "uploaded_file_name" in st.session_state:
                del st.session_state.uploaded_file_name

def main():
    page_xml_lancamento()

if __name__ == "__main__":
    main()
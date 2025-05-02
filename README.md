# controle_analista

## Descrição
Este projeto oferece uma plataforma para gerenciamento de estoques, análise de vendas, controle de lojas, geração de pedidos de compra, sugestões de compra baseadas em consumo, e lançamentos de produtos via XML. Os principais componentes incluem páginas em Streamlit para gerenciar lojas, correções de estoque, dashboard de controle, geração de pedidos, sugestões de compra, e lançamentos por XML, além de funções para conexão e manipulação de dados no banco de dados PostgreSQL.

## Sumário
- [Dependências](#dependências)
- [Instalação](#instalação)
- [Uso](#uso)
- [Estrutura de Pastas](#estrutura-de-pastas)

## Dependências
- streamlit==1.42.2
- psycopg2-binary==2.9.10
- pandas==2.2.2
- plotly==6.0.0
- xmltodict==0.14.2
- xlsxwriter==3.2.2

## Instalação
Execute o comando abaixo para instalar as dependências listadas no arquivo `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Uso
Para iniciar a aplicação, execute:
```bash
streamlit run home_page.py
```
A partir da interface, você pode navegar pelas páginas de gerenciamento de lojas, controle de estoque, dashboard, sugestão de compra, lançamento via XML, e pedidos de compra.

## Estrutura de Pastas
```plaintext
controle_analista/
├── home_page.py
├── pages_1_Dash.py
├── pages_2_Controle_Estoque.py
├── pages_3_Lancamento_XML.py
├── pages_4_Sugestao_Compra.py
├── pages_5_Pedido_Compra.py
├── utils.py
├── requirements.txt
```

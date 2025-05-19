# controle_analista

## Descrição
O projeto `controle_analista` é uma aplicação web desenvolvida com Streamlit que permite a gestão de lojas, produtos, estoque, movimentações de estoque e pedidos de compra. Inclui funcionalidades para gerenciamento de lojas, controle de estoque por loja, lançamento de produtos via XML, visualização de dashboards e sugestão de compra com geração de pedidos.

---

## Sumário
- [Dependências](#dependências)
- [Instalação](#instalação)
- [Uso](#uso)
- [Estrutura de Pastas](#estrutura-de-pastas)

---

## Dependências
- streamlit==1.42.2
- psycopg2-binary==2.9.10
- pandas==2.2.2
- plotly==6.0.0
- xmltodict==0.14.2
- xlsxwriter==3.2.2
- streamlit-aggrid==1.0.5

---

## Instalação
Clone o repositório e instale as dependências utilizando o arquivo `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## Uso
Execute o aplicativo principal com:
```bash
streamlit run home_page.py
```

A partir daí, navegue pelas diferentes páginas acessando os links disponíveis na interface para utilizar as funcionalidades de gerenciamento, controle, lançamento via XML, dashboard e sugestão de compra.

---

## Estrutura de Pastas
```
controle_analista/
│
├── home_page.py
├── pages_1_Dash.py
├── pages_2_Controle_Estoque.py
├── pages_3_Lancamento_XML.py
├── pages_4_Sugestao_Compra.py
├── requirements.txt
└── utils.py
```

---

# Observações
- Os scripts de páginas (ex.: `home_page.py`, `pages_1_Dash.py`, etc.) utilizam funções de `utils.py` para conexão com banco, consulta e atualização de dados.
- O projeto possui funcionalidades para gerenciamento de lojas, controle e correção de estoque, leitura de XML para lançamentos, dashboards de análise e geração de pedidos de compra.

---

Para mais detalhes de uso, navegue pelas páginas disponíveis no aplicativo após a sua execução.
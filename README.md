```markdown
# README.md

# controle_analista

## Objetivo
O projeto *controle_analista* é uma ferramenta de controle de estoque e análise de vendas para lojas. Permite gerenciar informações de produtos, estoques, movimentações, além de gerar relatórios, dashboards e sugestões de compra com base nas vendas passadas e no estoque atual.

## Dependências e Instalação
Para rodar o projeto, é necessário instalar as seguintes dependências listadas no arquivo `requirements.txt`:

- streamlit==1.42.2  
- psycopg2-binary==2.9.10  
- pandas==2.2.2  
- plotly==6.0.0  
- xmltodict==0.14.2  
- xlsxwriter==3.2.2  

Para instalar, execute:

```bash
pip install -r requirements.txt
```

Certifique-se de ter uma base de dados PostgreSQL configurada, com as tabelas necessárias, e atualize os segredos do Streamlit (`st.secrets`) com as credenciais corretas.

## Como rodar e testar
Após instalar as dependências e configurar o banco de dados, execute o aplicativo com:

```bash
streamlit run pages_1_dash.py
```

A interface acessível pelo navegador permitirá interagir com o projeto, acessando os diferentes módulos:
- Dashboard para análise de vendas e estoques (`pages_1_dash.py`)
- Gestão de lojas (`home_page.py`)
- Correções de estoque (`pages_2_controle_estoque.py`)
- Entrada de produtos via XML (`pages_3_lancamento_xml.py`)
- Sugestões de compra (`pages_4_sugestao_compra.py`)

## Estrutura e principais arquivos
A estrutura do projeto inclui os seguintes arquivos principais:

- `utils.py`: funções utilitárias para acesso ao banco, consultas e operações de manutenção.
- `requirements.txt`: lista de dependências necessárias.
- `home_page.py`: gerenciamento de lojas e updates.
- `pages_1_dash.py`: painel de dashboard com gráficos, tabelas e relatórios.
- `pages_2_controle_estoque.py`: páginas para ajustes e transferências de estoque.
- `pages_3_lancamento_xml.py`: upload e processamento de XML para lançamentos.
- `pages_4_sugestao_compra.py`: cálculo de sugestões de compra com base no histórico de vendas.

Para rodar o projeto, acesse o terminal, navegue até a pasta do projeto e execute:

```bash
streamlit run pages_1_dash.py
```

Assim, o aplicativo será iniciado no navegador padrão, pronto para uso.
```
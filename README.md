# controle_analista

## Descrição
O projeto *controle_analista* é uma ferramenta para gerenciamento de estoque, análise de vendas e controle de movimentações em lojas. Ele oferece funcionalidades para visualizar gráficos de vendas, controlar estoques, corrigir lançamentos, realizar transferências entre lojas, registrar entradas por XML, e gerar sugestões de compras com base no histórico de vendas.

## Sumário
- [Dependências e Instalação](#dependências-e-instalação)
- [Como rodar e testar](#como-rodar-e-testar)
- [Estrutura de Pastas](#estrutura-de-pastas)

## Dependências e Instalação
As dependências necessárias para executar o projeto estão listadas no arquivo `requirements.txt`. Para instalá-las, utilize o comando:

```bash
pip install -r requirements.txt
```

Após a instalação, configure o banco de dados e os segredos do Streamlit (`st.secrets`) com as credenciais corretas.

## Como rodar e testar
Para iniciar o projeto, execute o seguinte comando:

```bash
streamlit run <nome_do_arquivo>.py
```

Os principais scripts para navegação são:
- `pages_1_dash.py`: Dashboard de controle de estoque
- `home_page.py`: Gerenciamento das lojas
- `pages_2_controle_estoque.py`: Correções e transferências de estoque
- `pages_3_lancamento_xml.py`: Entrada de produtos via XML
- `pages_4_sugestao_compra.py`: Sugestões de compra

Abra o endereço localhost indicado no terminal para interagir com a aplicação.

## Estrutura de Pastas
```
.
├── home_page.py
├── pages_1_dash.py
├── pages_2_controle_estoque.py
├── pages_3_lancamento_xml.py
├── pages_4_sugestao_compra.py
├── requirements.txt
└── utils.py
```
- **`utils.py`**: funções auxiliares para conexão com o banco, consultas e operações de manutenção.
- **`requirements.txt`**: lista de dependências necessárias.
- **Demais arquivos `.py`**: componentes de interface e lógica para cada funcionalidade específica do sistema.
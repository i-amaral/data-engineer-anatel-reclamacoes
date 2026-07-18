# Engenharia de Dados End-to-End: Reclamações Anatel

Projeto de Engenharia de Dados ponta a ponta com foco na extração, transformação e modelagem (ETL) da base de dados de reclamações de usuários da Anatel, estruturado para consumo no Power BI.

## 🛠️ Tecnologias e Infraestrutura

* **Sistema Operacional:** Windows 11 com subsistema WSL2 (Ubuntu Linux).
* **Banco de Dados:** Oracle Database (imagem Docker `gvenzl/oracle-free` rodando localmente).
* **Gestão de Banco:** DBeaver.
* **Processamento (Python):** Polars, oracledb, SQLAlchemy.
* **Business Intelligence:** Power BI (Modelagem e DAX).

## ⚙️ Arquitetura e Fluxo de Dados

1. **Ingestão Bruta:** Download do dataset bruto em `.csv` via [Dados Abertos do Governo](https://dados.gov.br/dados/conjuntos-dados/solicitacoesregistradasnaanatel) e importação direta para o banco de dados Oracle via DBeaver utilizando o `ddl.sql`.
2. **Extração:** Script Python conecta ao banco Oracle, lendo a tabela bruta de forma otimizada com a query `filter_input.sql`.
3. **Transformação (Polars):** 
   * Limpeza, tipagem e padronização dos dados.
   * **Nota de Arquitetura:** Em algumas etapas (como na criação de grupos), optou-se por utilizar o `pl.SQLContext()` dentro do script Python. Embora o Polars nativo pudesse ser mais performático, a abordagem com SQL foi aplicada propositalmente para demonstrar o uso de consultas SQL no processamento de dados do pipeline.
   * Modelagem dimensional em **Star Schema** (Esquema Estrela), resultando em 1 tabela Fato e 4 tabelas Dimensão.
4. **Carga:** Os dataframes gerados e modelados pelo Polars são persistidos (Load) novamente no banco Oracle como tabelas finalizadas.
5. **Visualização:** O Power BI se conecta ao Oracle lendo o Star Schema. Nele, foram feitos os relacionamentos finais do modelo e desenvolvidas as medidas em DAX para análises analíticas.

## 📂 Estrutura de Arquivos

* `main.py`: Script principal em Python que realiza a conexão, leitura, transformação e carga dos dados.
* `ddl.sql`: Criação da estrutura inicial para receber o `.csv` bruto.
* `filter_input.sql`: Filtros e padronizações iniciais direto na camada de banco de dados.
* `requirements.txt`: Dependências e bibliotecas do ambiente Python.

## 🔗 Links Úteis

* [Dados Brutos + PBI - Google Drive](https://drive.google.com/drive/folders/1a1llj-02C-xoyqmbeIBK5u7PMpUQMQZa?usp=drive_link)
* [Fonte Oficial - Anatel](https://dados.gov.br/dados/conjuntos-dados/solicitacoesregistradasnaanatel)

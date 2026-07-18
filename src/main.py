import os
import time
import oracledb
import polars as pl
from dotenv import load_dotenv
import warnings
from sqlalchemy import Integer, Date
from sqlalchemy.dialects.oracle import VARCHAR2

# Variáveis de ambiente
load_dotenv()

USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
SERVICE = os.getenv("DB_SERVICE")

def connection_db() -> oracledb.Connection:
    "Conexão com o banco de dados Oracle"
    try:
        # Declaração host + porta + nome do banco
        host_port = f"{HOST}:{PORT}/{SERVICE}"
        # Criação da conexão
        connection = oracledb.connect(
            user=USER,
            password=PASSWORD,
            dsn=host_port
            )
        print('\nConexão bem-sucedida!\n')
        
        return connection
    except Exception as e:
        print(f'Erro ao conectar com o banco de dados: "{e}"')
        raise

def read_query(path: str) -> str:
    "Leitura query SQL"
    try:
        with open(path, 'r', encoding='utf-8') as file:
            query_sql = file.read()
        return query_sql
    except Exception as e:
        print(f'Erro ao aplicar "read_query": {e}')
        raise

def extract_from_db(sql_file: str, connector: oracledb.Connection) -> pl.DataFrame:
    "Extração tabela do db para df, filtrado pela query e normalizado"
    try:

        return pl.read_database(query=sql_file, connection=connector)
    
    except Exception as e:
        print(f'Erro ao aplicar "extract_from_db": {e}')
        raise

def transform(df: pl.DataFrame) -> pl.DataFrame:
    "Transformação/Processamento dos dados"
    try:
        # Mapeamento tipagem dos dados
        map_type = [
            'UF',
            'Cidade',
            'TipoAtendimento',
            'Marca',
            'Assunto',
            'Problema'
        ]
        # Depara nomenclaturas Anatel -> Nomenclaturas negócio
        map_servico = {
            'SCM': 'BANDA LARGA FIXA',
            'SEAC': 'TV POR ASSINATURA',
            'STFC': 'TELEFONIA FIXA',
            'SMP_PÓS': 'TELEFONIA MÓVEL (PÓS-PAGO / CONTROLE)',
            'SMP_PRÉ': 'TELEFONIA MÓVEL (PRÉ-PAGO)',
        }

        df_transformed = (
            df.clone()
            .with_columns(
                # Tipagem
                pl.col(map_type).cast(pl.String),
                pl.col(['Linha', 'SOLICITAÇÕES']).cast(pl.Int64),
                # Add "DIA" + conversão para data
                (pl.col('AnoMês') + '-01').str.to_date('%Y-%m-%d'),
                # Replace valores
                pl.col('Serviço').replace(map_servico)
            )
            .rename({
                'Linha': 'ID',
                'SOLICITAÇÕES': 'Quantidade Solicitações',
                'AnoMês': 'Data',
                'TipoAtendimento': 'Tipo de Atendimento',
                'Marca': 'Empresa',
                'Assunto': 'Tema',
                'Problema': 'Descrição'
            }
            )
        )

        ### Criação Coluna GRUPO, com SQL ###
        ctx = pl.SQLContext()
        ctx.register('reclamacoes_contexto', df_transformed)
        
        query_grupo = """
            SELECT *,
                CASE 
                    WHEN Empresa IN ('CLARO', 'NEXTEL', 'DESKTOP') THEN 'CLARO'
                    ELSE Empresa
                END AS Grupo
            FROM reclamacoes_contexto
            """
        df_transformed = ctx.execute(query_grupo).collect()
        
        return df_transformed
    except Exception as e:
        print(f'Erro ao aplicar "transform": {e}')
        raise

def modeling(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    "Modelagem dos dados para Star Schema (Esquema Estrela) focado em Power BI"
    try:
        print('Iniciando modelagem Dimensional...')

        # Criação das Tabelas Dimensão
        dim_localidade = (
            df.select(['UF', 'Cidade'])
            .unique()
            .with_row_index(name='ID_Localidade', offset=1)
        )

        dim_empresa = (
            df.select(['Empresa', 'Grupo'])
            .unique()
            .with_row_index(name='ID_Empresa', offset=1)
        )

        dim_problema = (
            df.select(['Tema', 'Descrição'])
            .unique()
            .with_row_index(name='ID_Problema', offset=1)
        )

        dim_servico = (
            df.select(['Tipo de Atendimento', 'Serviço'])
            .unique()
            .with_row_index(name='ID_Servico', offset=1)
        )

        # Criação da Tabela Fato
        fato_reclamacoes = (
            df.join(dim_localidade, on=['UF', 'Cidade'], how='left')
              .join(dim_empresa, on=['Empresa', 'Grupo'], how='left')
              .join(dim_problema, on=['Tema', 'Descrição'], how='left')
              .join(dim_servico, on=['Tipo de Atendimento', 'Serviço'], how='left')
              .select([
                  'ID', 
                  'Data',
                  'ID_Localidade', 
                  'ID_Empresa', 
                  'ID_Problema', 
                  'ID_Servico', 
                  'Quantidade Solicitações'
              ])
        )

        # Retorna um dicionário contendo todas as tabelas prontas
        tabelas_modeladas = {
            "DIM_LOCALIDADE": dim_localidade,
            "DIM_EMPRESA": dim_empresa,
            "DIM_PROBLEMA": dim_problema,
            "DIM_SERVICO": dim_servico,
            "FATO_RECLAMACOES": fato_reclamacoes
        }

        print('Modelagem Dimensional concluída com sucesso!')
        
        return tabelas_modeladas
    except Exception as e:
        print(f'Erro ao aplicar "modeling": {e}')
        raise

def load(tabelas_modeladas: dict[str, pl.DataFrame], connector: oracledb.Connection) -> None:
    "Carga das tabelas dimensionais e fato no banco de dados Oracle"
    try:
        print('\nIniciando a carga dos dados no banco...')

        # Dicionário Tipagens
        master_dtypes = {
            "DIM_LOCALIDADE": {
                'ID_Localidade': Integer,
                'UF': VARCHAR2(2),
                'Cidade': VARCHAR2(255)
            },
            "DIM_EMPRESA": {
                'ID_Empresa': Integer,
                'Empresa': VARCHAR2(100),
                'Grupo': VARCHAR2(100)
            },
            "DIM_PROBLEMA": {
                'ID_Problema': Integer,
                'Tema': VARCHAR2(100),
                'Descrição': VARCHAR2(255)
            },
            "DIM_SERVICO": {
                'ID_Servico': Integer,
                'Tipo de Atendimento': VARCHAR2(50),
                'Serviço': VARCHAR2(255)
            },
            "FATO_RECLAMACOES": {
                'ID': Integer,
                'Data': Date,
                'ID_Localidade': Integer,
                'ID_Empresa': Integer,
                'ID_Problema': Integer,
                'ID_Servico': Integer,
                'Quantidade Solicitações': Integer
            }
        }

        # Iteração sobre cada tabela do dicionário
        for nome_tabela, df in tabelas_modeladas.items():
            print(f'\nProcessando tabela: {nome_tabela} ({df.shape[0]} linhas)')
            
            # Drop table
            with connector.cursor() as cursor:
                try:
                    cursor.execute(f'DROP TABLE {nome_tabela} CASCADE CONSTRAINTS')
                    connector.commit()
                    print(f'Tabela "{nome_tabela}" existente removida.')
                except oracledb.DatabaseError as db_err:
                    # ORA-00942: tabela não existe
                    if 'ORA-00942' not in str(db_err):
                        raise

            # Resgata a tipagem específica para esta tabela
            dtype_map = master_dtypes.get(nome_tabela, {})

            # Supressão do warning de case sensitivity
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df.write_database(
                    table_name=nome_tabela,
                    connection=f"oracle+oracledb://{USER}:{PASSWORD}@{HOST}:{PORT}/?service_name={SERVICE}",
                    if_table_exists="append",
                    engine="sqlalchemy",
                    engine_options={"dtype": dtype_map}
                )
            
            pk_col = df.columns[0]
            with connector.cursor() as cursor:
                # O Oracle limita nomes de constraints em 30 chars nas versões mais antigas
                nome_constraint = f'pk_{nome_tabela.lower()}'[:30] 
                cursor.execute(f'ALTER TABLE {nome_tabela} ADD CONSTRAINT {nome_constraint} PRIMARY KEY ("{pk_col}")')
                connector.commit()
                print(f'Constraint de PK adicionada na coluna "{pk_col}".')

        print('\nTodas as tabelas foram carregadas com sucesso no banco de dados!')
    
    except Exception as e:
        print(f'Erro ao exportar os dados para o banco: {e}')
        raise

def main() -> None:
    "Função principal de orquestração da pipeline ETL"
    print(f'Conectando ao banco OracleDB com o usuário "{USER}"...')
    start_time = time.time()
    with connection_db() as connector:
        query_sql = read_query('./sql_query/filter_input.sql') # Lê a query SQL
        df = extract_from_db(query_sql, connector) # Realiza a extração dos dados
        df_transformed = transform(df) # Aplica as regras de negócio e tipagem
        tbs_modeladas = modeling(df_transformed)
        load(tbs_modeladas, connector) # Carrega o resultado final no banco
        end_time = time.time()
        print(f'\nExecution time: {(end_time - start_time):.1f} seconds')
if __name__ == "__main__":
    main()

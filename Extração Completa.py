import os
import pandas as pd
from google.cloud import bigquery

# --- PASSO 1: Configuração Inicial ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credenciais.json"
client = bigquery.Client()
dataset_id = "Farmacias"

# Lista para armazenar o DataFrame de cada ponto
dataframes_pontos = []

try:
    # --- PASSO 2: Mapeamento das Tabelas ---
    tabelas = list(client.list_tables(dataset_id))
    
    if len(tabelas) == 0:
        print(f"Nenhuma tabela encontrada no dataset '{dataset_id}'.")
    else:
        print(f"Encontrados {len(tabelas)} pontos (tabelas) para extração.\n")
        
        # --- PASSO 3: Extração em Lote ---
        for tabela in tabelas:
            tabela_id = tabela.table_id
            tabela_completa = f"{client.project}.{dataset_id}.{tabela_id}"
            
            print(f"Extraindo dados do ponto: {tabela_id}...")
            
            # Query para buscar tudo da tabela atual
            query = f"SELECT * FROM `{tabela_completa}`"
            df_temp = client.query(query).to_dataframe()
            
            # Cria uma coluna para rastrear de qual ponto essa venda veio
            df_temp['ponto_origem'] = tabela_id
            
            # Adiciona o DataFrame temporário à nossa lista
            dataframes_pontos.append(df_temp)
            
        # --- PASSO 4: Consolidação Final ---
        # Junta (concatena) todos os DataFrames da lista em um só, empilhando as linhas
        df_historico_completo = pd.concat(dataframes_pontos, ignore_index=True)
        
        print("\nExtração e consolidação concluídas com sucesso!")
        print(f"Total de registros históricos: {len(df_historico_completo)} linhas.")
        
        # Mostra uma amostra misturada para confirmar a consolidação
        print("\nAmostra dos dados consolidados:")
        # Pega o DataFrame que já tem 100% dos dados na memória e salva em um arquivo local
        df_historico_completo.to_csv("meus_dados_completos.csv", index=False, sep=";")

        print("Arquivo salvo! Pode abrir a pasta do projeto.")

except Exception as e:
    print(f"Ocorreu um erro durante a extração em lote: {e}")
    
    
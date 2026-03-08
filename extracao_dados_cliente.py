import os
import pandas as pd
from google.cloud import bigquery

# Aponte para a sua chave JSON da FerMazzia
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./Credenciais/credenciais_google.json"

def extrair_e_unificar_dados():
    client = bigquery.Client()
    
    # Mapeamento: "Nome da Tabela no BQ" -> "Pasta de Destino Local"
    mapeamento_tabelas = [
        {
            "tabela": "supple-fold-473517-h1.Farmacias.Historico_Vendas_Farma_Ponte", 
            "pasta": "FarmaPonte/Dados_FarmaPonte"  # Subpasta para os dados da Farma Ponte
        },
        {
            "tabela": "supple-fold-473517-h1.Farmacias.Historico_Vendas_Vera_Cruz", 
            "pasta": "VeraCruz/Dados_VeraCruz"
        },
        {
            "tabela": "supple-fold-473517-h1.Farmacias.Historico_Vendas_Sao_Joao", # Confirme o nome exato no BQ
            "pasta": "SaoJoao/Dados_SaoJoao"
        },
        {
            "tabela": "supple-fold-473517-h1.Farmacias.Historico_Vendas_Sao_Paulo", # Confirme o nome exato no BQ
            "pasta": "SaoPaulo/Dados_SaoPaulo"
        }
    ]
    
    for item in mapeamento_tabelas:
        tabela = item["tabela"]
        pasta = item["pasta"]
        
        print(f"\nIniciando extração da tabela: {tabela}...")
        
        # Cria a pasta automaticamente se ela não existir
        os.makedirs(pasta, exist_ok=True)
        
        query = f"SELECT * FROM `{tabela}`"
        
        try:
            # 1. Baixa os dados brutos do BigQuery
            df = client.query(query).to_dataframe()
            
            # ---------------------------------------------------------
            # ETAPA A: SALVAR O ARQUIVO ORIGINAL (BRUTO)
            # ---------------------------------------------------------
            nome_base_original = tabela.split('.')[-1] + ".csv"
            caminho_original = os.path.join(pasta, nome_base_original)
            
            df.to_csv(caminho_original, index=False, encoding='utf-8-sig', sep=';')
            print(f"✅ Arquivo ORIGINAL salvo em: {caminho_original}")
            
            # ---------------------------------------------------------
            # ETAPA B: PROCESSAR E SALVAR O ARQUIVO CONSOLIDADO
            # ---------------------------------------------------------
            print("   -> Gerando versão consolidada...")
            
            # Agrupa por produto, soma a quantidade e depos conta a frequência (Nesta ordem!)
            df_unificado = df.groupby('nome_produto').agg(
                Quantidade_Total=('quantidade', 'sum'),
                Frequencia_Vendas=('venda_id', 'count')
            ).reset_index()
            
            # Renomeia e ordena
            df_unificado = df_unificado.rename(columns={'nome_produto': 'Produto'})
            df_unificado = df_unificado.sort_values(by='Quantidade_Total', ascending=False)
            
            # Adiciona o sufixo "_Consolidado" no nome do arquivo
            nome_base_consolidado = tabela.split('.')[-1] + "_Consolidado.csv"
            caminho_consolidado = os.path.join(pasta, nome_base_consolidado)
            
            df_unificado.to_csv(caminho_consolidado, index=False, encoding='utf-8-sig', sep=';')
            print(f"✅ Arquivo CONSOLIDADO salvo em: {caminho_consolidado}")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Deu erro ao extrair ou processar {tabela}: {e}")
            print("-" * 60)

if __name__ == "__main__":
    extrair_e_unificar_dados()
import pandas as pd
from thefuzz import process, fuzz
import time

def unificar_bases_farmaponte_rigoroso():
    print("⏳ Carregando as planilhas consolidadas...")
    
    # 1. Carrega os arquivos
    df_historico = pd.read_csv('Dados_FarmaPonte/Historico_Vendas_Farma_Ponte_Consolidado.csv', sep=';')
    df_scraping = pd.read_csv('Dados_FarmaPonte/Scraping_FarmaPonte.csv', sep=';')
    
    # Remove as duplicatas do próprio site
    df_scraping = df_scraping.drop_duplicates(subset=['Nome do produto'], keep='first')
    
    produtos_historico = df_historico['Produto'].dropna().unique()
    produtos_scraping = df_scraping['Nome do produto'].dropna().unique()
    
    dicionario_match = {}
    
    print(f"🔎 Iniciando Fuzzy Matching rigoroso para {len(produtos_historico)} produtos...")
    inicio = time.time()
    
    # 2. O Robô Analista com motor atualizado
    for produto in produtos_historico:
        melhor_match = process.extractOne(
            produto, 
            produtos_scraping, 
            scorer=fuzz.token_sort_ratio
        )
        
        if melhor_match:
            nome_encontrado, nota = melhor_match
            if nota >= 70:
                dicionario_match[produto] = nome_encontrado
            else:
                dicionario_match[produto] = None
        else:
            dicionario_match[produto] = None

    tempo_gasto = time.time() - inicio
    print(f"✅ Matching finalizado em {tempo_gasto:.1f} segundos!")
    
    # 3. Cria a ponte entre as duas planilhas
    df_historico['nome_scraping'] = df_historico['Produto'].map(dicionario_match)
    
    sucessos = df_historico['nome_scraping'].notna().sum()
    print(f"🎯 Taxa de Sucesso Genuíno: {sucessos} produtos casaram perfeitamente.")
    
    # 4. O Cruzamento (Left Join)
    print("🔗 Fundindo os dados e formatando colunas...")
    df_final = pd.merge(
        df_historico, 
        df_scraping, 
        left_on='nome_scraping', 
        right_on='Nome do produto', 
        how='left'
    )
    
    # 5. Tratamento de Nulos (Imitando o teu ficheiro ATUALIZADO)
    df_final['Nome da Farmácia'] = df_final['Nome da Farmácia'].fillna('FarmaPonte')
    df_final['Status do produto'] = df_final['Status do produto'].fillna('Esgotado')
    df_final['EAN'] = df_final['EAN'].fillna(0)
    
    # Preenche preços vazios com 0
    cols_precos = ['Preço original', 'Preço à vista no cartão', 'Desconto cartão', 'Preço PIX', 'Desconto PIX']
    for col in cols_precos:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna(0)

    # 6. Mapeamento para os novos nomes
    mapeamento_colunas = {
        'Nome da Farmácia': 'Farmácia',
        'Status do produto': 'Status',
        'Quantidade_Total': 'Total Unidades Vendidas',
        'Frequencia_Vendas': 'Frequencia_Vendas',
        'EAN': 'EAN_ou_SKU',
        'Produto': 'Nome_do_Produto',
        'Preço original': 'Preco_Tabela',
        'Preço à vista no cartão': 'Preco_Cartao_Valor',
        'Desconto cartão': 'Desconto_Cartao',
        'Preço PIX': 'Preco_Pix_Valor',
        'Desconto PIX': 'Desconto_Pix'
    }
    
    df_final = df_final.rename(columns=mapeamento_colunas)
    
    # 7. Impor a Ordem Exata
    ordem_colunas = [
        'Farmácia', 
        'Status', 
        'Total Unidades Vendidas', 
        'Frequencia_Vendas', 
        'EAN_ou_SKU', 
        'Nome_do_Produto', 
        'Preco_Tabela', 
        'Preco_Cartao_Valor', 
        'Desconto_Cartao', 
        'Preco_Pix_Valor', 
        'Desconto_Pix'
    ]
    
    df_final = df_final[ordem_colunas]
    df_final = df_final.sort_values(by='Total Unidades Vendidas', ascending=False)
    
    # 8. Limpeza e Salvamento
    nome_arquivo_final = "Base_Cruzada_FarmaPonte.csv"
    # Salva usando vírgula (sep=',') para bater com o padrão do teu ficheiro novo
    df_final.to_csv(f"Dados_FarmaPonte/{nome_arquivo_final}", index=False, encoding='utf-8-sig', sep=',')
    
    print(f"🎉 Tabela limpa, formatada e salva como: {nome_arquivo_final}")

if __name__ == "__main__":
    unificar_bases_farmaponte_rigoroso()
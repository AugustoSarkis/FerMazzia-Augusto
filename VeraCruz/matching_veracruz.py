import pandas as pd
from thefuzz import process, fuzz
import time

def unificar_bases_veracruz_rigoroso():
    print("⏳ Carregando as planilhas da Vera Cruz...")
    
    df_historico = pd.read_csv('Dados_VeraCruz/Historico_Vendas_Vera_Cruz_Consolidado.csv', sep=';')
    df_scraping = pd.read_csv('Dados_VeraCruz/Scraping_VeraCruz.csv', sep=';')
    
    df_scraping = df_scraping.drop_duplicates(subset=['Nome do produto'], keep='first')
    
    produtos_historico = df_historico['Produto'].dropna().unique()
    produtos_scraping = df_scraping['Nome do produto'].dropna().unique()
    
    dicionario_match = {}
    
    print(f"🔎 Iniciando Fuzzy Matching rigoroso para {len(produtos_historico)} produtos...")
    inicio = time.time()
    
    for produto in produtos_historico:
        melhor_match = process.extractOne(produto, produtos_scraping, scorer=fuzz.token_sort_ratio)
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
    
    df_historico['nome_scraping'] = df_historico['Produto'].map(dicionario_match)
    df_final = pd.merge(df_historico, df_scraping, left_on='nome_scraping', right_on='Nome do produto', how='left')
    
    # Tratamento de Nulos
    df_final['Nome da Farmácia'] = df_final['Nome da Farmácia'].fillna('VeraCruz')
    df_final['Status do produto'] = df_final['Status do produto'].fillna('Esgotado')
    df_final['EAN'] = df_final['EAN'].fillna(0)
    
    cols_precos = ['Preço original', 'Preço à vista no cartão', 'Desconto cartão', 'Preço PIX', 'Desconto PIX']
    for col in cols_precos:
        if col in df_final.columns:
            df_final[col] = df_final[col].replace('-', 0).fillna(0)

    def isolar_categoria_primaria(cat):
        if not isinstance(cat, str) or cat in ['-', '']:
            return 'Sem Categoria'
        partes = [p.strip() for p in cat.split('>')]
        if 'Medicamentos' in partes:
            idx = partes.index('Medicamentos')
            if idx + 1 < len(partes):
                return partes[idx + 1]
            return 'Medicamentos'
        return partes[0]
        
    df_final['Subcategoria'] = df_final['Subcategoria'].apply(isolar_categoria_primaria)

    mapeamento_colunas = {
        'Nome da Farmácia': 'Farmácia',
        'Status do produto': 'Status',
        'Quantidade_Total': 'Total Unidades Vendidas',
        'Frequencia_Vendas': 'Frequencia_Vendas',
        'EAN': 'EAN_ou_SKU',
        'Produto': 'Nome_do_Produto',
        'Subcategoria': 'Categoria',
        'Preço original': 'Preco_Tabela',
        'Preço à vista no cartão': 'Preco_Cartao_Valor',
        'Desconto cartão': 'Desconto_Cartao',
        'Preço PIX': 'Preco_Pix_Valor',
        'Desconto PIX': 'Desconto_Pix'
    }
    
    df_final = df_final.rename(columns=mapeamento_colunas)
    
    ordem_colunas = [
        'Farmácia', 'Status', 'Total Unidades Vendidas', 'Frequencia_Vendas', 
        'EAN_ou_SKU', 'Nome_do_Produto', 'Categoria', 'Preco_Tabela', 
        'Preco_Cartao_Valor', 'Desconto_Cartao', 'Preco_Pix_Valor', 'Desconto_Pix'
    ]
    
    df_final = df_final[ordem_colunas]
    df_final = df_final.sort_values(by='Total Unidades Vendidas', ascending=False)
    
    nome_arquivo_final = "Base_Cruzada_VeraCruz.csv"
    df_final.to_csv(f"Dados_VeraCruz/{nome_arquivo_final}", index=False, encoding='utf-8-sig', sep=',')
    
    print(f"🎉 Tabela formatada e salva como: {nome_arquivo_final}")

if __name__ == "__main__":
    unificar_bases_veracruz_rigoroso()
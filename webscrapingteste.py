import pandas as pd
import re

def criar_termo_de_busca(nome):
    """
    Limpa o nome técnico do produto para criar um termo de busca amigável.
    Remove dosagens e apresentações (ex: '30mg', 'c/ 30 caps') que variam
    entre sites e costumam causar erro na busca.
    """
    if not isinstance(nome, str): return ""
    
    termo = nome.lower()
    
    # Lista de termos técnicos para remover (melhora o 'match' na busca do site)
    remover = [
        r'\d+\s*mg', r'\d+\s*mcg', r'\d+\s*g', r'\d+\s*ml',
        r'\d+\s*comprimidos?', r'\d+\s*capsulas?', r'\d+\s*cápsulas?',
        r'\d+\s*unidades?', r'\d+\s*envelopes?', r'caixa\s+com.*',
        r'c/\s*\d+.*', r'uso\s+oral', r'uso\s+tópico', r'xarope'
    ]
    
    for padrao in remover:
        termo = re.sub(padrao, ' ', termo)
    
    # Remove caracteres especiais e limpa espaços extras
    termo = re.sub(r'[^a-zA-Z0-9áéíóúâêîôûãõç\s]', ' ', termo)
    termo = " ".join(termo.split()).title()
    
    return termo

def processar_base_farmacia(arquivo_entrada, nome_saida):
    """
    Lê a base, calcula a relevância de cada produto e salva a lista de alvos.
    """
    # 1. Carregar os dados
    df = pd.read_csv(arquivo_entrada, sep=';')
    
    # 2. Agrupar por produto para medir a relevância
    # Somamos a quantidade (giro) e contamos a frequência (recorrência)
    relevancia = df.groupby('nome_produto').agg({
        'quantidade': 'sum',
        'venda_id': 'count'
    }).reset_index()
    
    relevancia.columns = ['produto_original', 'total_unidades_vendidas', 'frequencia_vendas']
    
    # 3. Criar o Termo de Busca Otimizado para o Scraping
    relevancia['termo_para_busca'] = relevancia['produto_original'].apply(criar_termo_de_busca)
    
    # 4. Ordenar pelos mais relevantes (quem vende mais deve ser monitorado primeiro)
    relevancia = relevancia.sort_values(by='total_unidades_vendidas', ascending=False)
    
    # 5. Salvar arquivo final
    relevancia.to_csv(nome_saida, index=False, sep=';', encoding='utf-8-sig')
    return relevancia

# Execução Independente para cada farmácia
print("Processando Vera Cruz...")
processar_base_farmacia('Vendas_Vera_Cruz.csv', 'alvos_scraping_vera_cruz.csv')

print("Processando Farma Ponte...")
processar_base_farmacia('Vendas_Farma_Ponte.csv', 'alvos_scraping_farma_ponte.csv')

print("\nArquivos gerados com sucesso!")
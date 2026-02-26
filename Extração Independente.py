import pandas as pd

# 1. Carregar a base de dados consolidada
file_path = "dados_organizados_FerMazzia Corrigido CSV.csv"
df = pd.read_csv(file_path, sep=None, engine='python')

# 2. Limpar a coluna 'quantidade' para garantir que sejam números reais
df['quantidade'] = df['quantidade'].replace('?', pd.NA)
df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
df['quantidade'] = df['quantidade'].fillna(1)

# 3. Descobrir os nomes únicos de todas as farmácias na base
origens_farmacias = df['ponto_origem'].unique()

print("Iniciando a separação dos arquivos CSV...\n")

# 4. Loop que vai fatiar a base e criar os arquivos .csv
for origem in origens_farmacias:
    # Filtra o DataFrame para ter apenas as linhas da farmácia atual
    df_filtrado = df[df['ponto_origem'] == origem]
    
    # Cria um nome de arquivo terminando com .csv
    nome_curto = origem.replace('Historico_Vendas_', '')
    nome_do_arquivo = f"Vendas_{nome_curto}.csv"
    
    print(f"Gerando o arquivo: {nome_do_arquivo} (Total de {len(df_filtrado)} vendas)")
    
    # Salva o pedaço filtrado em um novo arquivo CSV com separador ';'
    df_filtrado.to_csv(nome_do_arquivo, sep=';', index=False)

print("\nConcluído! Todos os arquivos foram separados em formato .csv com sucesso.")
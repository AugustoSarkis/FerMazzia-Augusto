import pandas as pd

# 1. Carrega o seu arquivo bruto recém extraído
df = pd.read_csv("dados completos FerMazzia.csv", sep=";")

# 2. Define EXATAMENTE as colunas (seções) que você quer, na ordem que você pediu
colunas_desejadas = [
    'venda_id', 
    'nome_produto', 
    'data_venda', 
    'quantidade', 
    'ponto_origem'
]

# Recorta o DataFrame para ter apenas essas colunas
df_organizado = df[colunas_desejadas].copy()

# 3. (Opcional, mas recomendado) Ordenar os dados para ficarem agrupados
# Vamos ordenar primeiro pela Loja (Origem), depois por Data e Produto
df_organizado = df_organizado.sort_values(by=['ponto_origem', 'data_venda', 'nome_produto'])

# 4. Salva o resultado em um novo arquivo super limpo e organizado
df_organizado.to_csv("dados_organizados_FerMazzia.csv", sep=";", index=False)

print("Arquivo salvo com sucesso! Dê uma olhada nas primeiras linhas:")
print(df_organizado.head())
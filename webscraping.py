import sys
import subprocess
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By

print("🤖 Iniciando o robô com Extração Semântica...")
navegador = webdriver.Chrome()

# O alvo na Ultrafarma
url_alvo = "https://www.ultrafarma.com.br/busca?q=insulina"
navegador.get(url_alvo)

print("⏳ Aguardando 8 segundos para o site carregar completamente...")
time.sleep(8)

# TRUQUE DE MESTRE: Rolar a página para forçar o site a carregar os preços ocultos
print("⬇️ Rolando a página para quebrar o 'Lazy Loading'...")
navegador.execute_script("window.scrollBy(0, 800);")
time.sleep(3)

# Em vez de tentar adivinhar a classe exata do produto, pegamos todas as "caixas" (li) e links (a) da página
vitrine_produtos = navegador.find_elements(By.CSS_SELECTOR, "li, a[class*='product'], div[class*='item']")
print(f"Lendo {len(vitrine_produtos)} blocos na tela...")

dados_extraidos = []

for produto in vitrine_produtos:
    try:
        texto_bruto = produto.text.strip()
        
        # Filtro de Ouro: Só analisa o bloco se ele tiver a palavra "R$" (Ou seja, é um remédio à venda)
        if "R$" in texto_bruto and len(texto_bruto) > 15:
            
            # Quebra o texto da "caixinha" do remédio linha por linha
            linhas = texto_bruto.split('\n')
            
            nome = ""
            preco = ""
            
            # 1. Encontrar o Preço: Pega a última linha que tem "R$" (geralmente o preço final/com desconto)
            precos_encontrados = [linha for linha in linhas if "R$" in linha]
            if precos_encontrados:
                preco = precos_encontrados[-1].strip()
            
            # 2. Encontrar o Nome: Pega a primeira linha que seja grande o suficiente e não seja preço nem porcentagem
            for linha in linhas:
                if len(linha) > 10 and "R$" not in linha and "%" not in linha and "Desconto" not in linha:
                    nome = linha.strip()
                    break # Achou o nome, para de procurar
            
            # Se achou os dois, guarda no nosso cofre de dados!
            if nome and preco:
                dados_extraidos.append({
                    "Origem": "Ultrafarma",
                    "Produto": nome,
                    "Preco": preco
                })
    except:
        continue

# Fecha o navegador
navegador.quit()

# --- EXPORTAÇÃO BLINDADA ---
if len(dados_extraidos) > 0:
    # Converte para Pandas e remove produtos repetidos que o robô possa ter lido duas vezes
    df_resultados = pd.DataFrame(dados_extraidos).drop_duplicates()
    
    nome_arquivo = "Precos_Ultrafarma_Final.csv"
    df_resultados.to_csv(nome_arquivo, sep=";", index=False, encoding="utf-8-sig")
    
    print(f"\n✅ SUCESSO ABSOLUTO! O arquivo '{nome_arquivo}' foi gerado na sua pasta com {len(df_resultados)} produtos únicos.")
else:
    print("\n🔴 O robô leu a página, mas nenhum texto com 'R$' apareceu. O site pode estar bloqueando nosso Chrome fantasma.")
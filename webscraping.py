import sys
import subprocess
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

print("🤖 Iniciando o robô com captura de itens esgotados...")
navegador = webdriver.Chrome()

# O alvo na Vera Cruz
url_alvo = "https://www.farmaponte.com.br/acetilciste%C3%ADna/?p=2"
navegador.get(url_alvo)

print("⏳ Aguardando o carregamento...")
time.sleep(8)

print("⬇️ Rolando a página para carregar todos os itens...")
navegador.execute_script("window.scrollBy(0, 1500);")
time.sleep(3)

# Seletores abrangentes
vitrine_produtos = navegador.find_elements(By.CSS_SELECTOR, "li, a[class*='product'], div[class*='item']")
print(f"Lendo {len(vitrine_produtos)} blocos na tela...")

dados_extraidos = []

# Lista de termos que indicam falta de estoque
termos_esgotado = ["avise-me", "esgotado", "indisponível", "fora de estoque"]

for produto in vitrine_produtos:
    try:
        texto_bruto = produto.text.strip()
        texto_minusculo = texto_bruto.lower()
        
        # NOVO FILTRO: Aceita se tiver "R$" OU se tiver algum termo de esgotado
        tem_preco = "R$" in texto_bruto
        esta_esgotado = any(termo in texto_minusculo for termo in termos_esgotado)

        if (tem_preco or esta_esgotado) and len(texto_bruto) > 15:
            
            linhas = texto_bruto.split('\n')
            nome = ""
            preco = ""
            status = "Disponível"

            # 1. Lógica para o Preço/Status
            if esta_esgotado:
                preco = "R$ 0,00" # Ou deixe vazio
                status = "Esgotado"
            else:
                precos_encontrados = [linha for linha in linhas if "R$" in linha]
                if precos_encontrados:
                    preco = precos_encontrados[-1].strip()

            # 2. Lógica para o Nome
            for linha in linhas:
                # O nome geralmente é a primeira linha longa que não tem caracteres de preço/desconto
                if len(linha) > 10 and "R$" not in linha and "%" not in linha and "desconto" not in linha.lower():
                    nome = linha.strip()
                    break 
            
            if nome:
                dados_extraidos.append({
                    "Origem": "FarmaPonte",
                    "Produto": nome,
                    "Preco": preco,
                    "Status": status
                })
    except:
        continue

navegador.quit()

# --- EXPORTAÇÃO ---
if len(dados_extraidos) > 0:
    df_resultados = pd.DataFrame(dados_extraidos).drop_duplicates(subset=['Produto'])
    
    nome_arquivo = "Precos_e_Estoque_Final.csv"
    df_resultados.to_csv(nome_arquivo, sep=";", index=False, encoding="utf-8-sig")
    
    # Resumo para o André
    esgotados = df_resultados[df_resultados['Status'] == 'Esgotado'].shape[0]
    print(f"\n✅ SUCESSO! Arquivo '{nome_arquivo}' gerado.")
    print(f"📊 Total: {len(df_resultados)} | Disponíveis: {len(df_resultados)-esgotados} | Esgotados: {esgotados}")
else:
    print("\n🔴 Nenhum dado extraído. Verifique se o site mudou a estrutura.")
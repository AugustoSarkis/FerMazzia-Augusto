import pandas as pd
import time
import re
import json
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By

def gerar_slug_veracruz(nome):
    n = unicodedata.normalize('NFKD', str(nome)).encode('ascii', 'ignore').decode('utf-8')
    n = n.lower()
    n = re.sub(r'[^a-z0-9\s]', '', n)
    return "-".join(n.split())

def extrair_ean_robusto(driver):
    """ Tenta 4 métodos diferentes para achar o EAN """
    # Método 1: JSON-LD (Google Data)
    try:
        scripts = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
        for s in scripts:
            conteudo = json.loads(s.get_attribute('innerHTML'))
            items = conteudo['@graph'] if '@graph' in conteudo else [conteudo]
            for item in items:
                ean = item.get('gtin13') or item.get('mpn') or item.get('sku')
                if ean and str(ean).isdigit() and len(str(ean)) >= 12:
                    return str(ean)
    except: pass

    # Método 2: dataLayer (Variáveis do site)
    try:
        datalayer = driver.execute_script("return window.dataLayer || []")
        for data in datalayer:
            if 'ean' in data: return data['ean']
            if 'productEan' in data: return data['productEan']
            if 'skuEan' in data: return data['skuEan']
    except: pass

    # Método 3: Expressão Regular (Busca 13 dígitos começando com 789 no código fonte)
    try:
        html = driver.page_source
        match = re.search(r'\b789\d{10}\b', html)
        if match: return match.group(0)
    except: pass

    return "Não encontrado"

def extrair_vera_cruz():
    print("🚀 Iniciando Extração Completa: Vera Cruz")
    df_alvos = pd.read_csv('alvos_vera_cruz.csv', sep=None, engine='python', encoding='utf-8-sig')
    df_alvos.columns = df_alvos.columns.str.strip()

    driver = webdriver.Chrome()
    resultados = []

    # REMOVIDO .head(10) -> Agora roda a lista toda!
    for i, linha in df_alvos.iterrows():
        nome_original = str(linha['Produto Original']).strip()
        slug = gerar_slug_veracruz(nome_original)
        url = f"https://www.drogariaveracruz.com.br/{slug}/p"
        
        print(f"[{i+1}/{len(df_alvos)}] 🔎 Analisando: {nome_original}")
        
        try:
            driver.get(url)
            time.sleep(3) # Tempo para scripts carregarem

            # Extração de Preço
            preco = "Consultar"
            try:
                # Seletor universal de preço para VTEX
                preco = driver.find_element(By.CSS_SELECTOR, "[class*='sellingPriceValue']").text
            except: pass

            # Extração de EAN Robusta
            ean = extrair_ean_robusto(driver)

            resultados.append({
                "EAN": ean,
                "Produto_Original": nome_original,
                "Preco": preco,
                "Farmacia": "Vera Cruz"
            })
            print(f"   ✅ EAN: {ean} | Preço: {preco}")

        except:
            print(f"   ❌ Falha ao acessar página")

        # SALVAMENTO DE SEGURANÇA: Salva o progresso a cada 10 itens
        if (i + 1) % 10 == 0:
            pd.DataFrame(resultados).to_csv('Vera_Cruz_Progresso.csv', index=False, sep=';', encoding='utf-8-sig')
            print("💾 Progresso salvo em 'Vera_Cruz_Progresso.csv'")

    driver.quit()
    pd.DataFrame(resultados).to_csv('Resultado_Vera_Cruz_Final.csv', index=False, sep=';', encoding='utf-8-sig')
    print("\n✨ FIM! Arquivo final gerado.")

extrair_vera_cruz()
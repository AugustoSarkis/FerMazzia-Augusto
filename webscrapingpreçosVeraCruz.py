import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

def extrair_tres_precos(fonte_html):
    """ Extrai os 3 preços e verifica se está esgotado """
    preco_cheio = "0.00"
    preco_pix = "0.00"
    preco_cartao = "0.00"
    status = "Disponível"

    try:
        # 1. PREÇO CARTÃO
        match_data = re.search(r'window\.dataProduct\s*=\s*{(.*?)}', fonte_html, re.DOTALL)
        if match_data:
            p_venda_match = re.search(r'"price":\s*"([\d\.]+)"', match_data.group(1))
            if p_venda_match:
                preco_cartao = f"{float(p_venda_match.group(1)):.2f}"

        # 2. PREÇO CHEIO
        match_cheio = re.search(r'class="unit-price"[^>]*>\s*R\$\s*([\d,]+)', fonte_html)
        if match_cheio:
            preco_cheio = match_cheio.group(1).replace('.', '').replace(',', '.')
        else:
            match_edrone = re.search(r'"total_price":\s*([\d\.]+)', fonte_html)
            if match_edrone:
                preco_cheio = f"{float(match_edrone.group(1)):.2f}"
            else:
                preco_cheio = preco_cartao

        # 3. PREÇO PIX
        match_pix = re.search(r'class="seal-pix[^>]*>.*?R\$\s*([\d,]+)', fonte_html)
        if match_pix:
            preco_pix = match_pix.group(1).replace('.', '').replace(',', '.')
        else:
            match_ld = re.search(r'"offers":\s*{[^}]*"price":"([\d\.]+)"', fonte_html, re.DOTALL)
            if match_ld:
                preco_pix = f"{float(match_ld.group(1)):.2f}"
            else:
                match_edrone_unit = re.search(r'"unit_price":\s*([\d\.]+)', fonte_html)
                if match_edrone_unit:
                    preco_pix = f"{float(match_edrone_unit.group(1)):.2f}"
                else:
                    preco_pix = preco_cartao

        # 4. AVALIAÇÃO DE ESTOQUE
        if "PRODUTO ESGOTADO" in fonte_html or "Avise-me" in fonte_html or 'availability":"http://schema.org/OutOfStock' in fonte_html:
            status = "Esgotado"
        elif "Ops!" in fonte_html and "Sua cesta está vazia" in fonte_html and preco_cartao == "0.00":
            status = "Página Incorreta"

    except Exception as e:
        status = "Erro na Leitura"

    return preco_cheio, preco_pix, preco_cartao, status


def extrair_por_busca_ean():
    print("🚀 Iniciando Extração nos Itens Restantes (Busca por EAN)...")
    
    arquivo_entrada = 'Vera_Cruz_Refazer.csv'
    try:
        df = pd.read_csv(arquivo_entrada, sep=';')
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ Erro ao abrir arquivo: {e}")
        return

    colunas_novas = ['Preco_De_Tabela', 'Preco_Pix', 'Preco_Cartao', 'Status_Preco']
    for col in colunas_novas:
        if col not in df.columns: 
            df[col] = "Pendente"

    alvos = df[df['Preco_De_Tabela'] == "Pendente"]
    print(f"📦 Total de itens para processar: {len(alvos)}")

    driver = webdriver.Chrome()
    contador = 0

    for index, row in alvos.iterrows():
        nome = str(row['Produto_Original']).strip()
        ean = str(row['EAN']).strip()
        
        if ean == "Não encontrado" or ean == "nan" or ean == "":
            print(f"\n🔎 [{contador+1}] Pulando item sem EAN: {nome[:30]}...")
            df.at[index, 'Status_Preco'] = "Sem EAN para Busca"
            continue
            
        print(f"\n🔎 [{contador+1}] Buscando EAN {ean} - {nome[:30]}...")
        
        try:
            # Faz a pesquisa usando o EAN
            driver.get(f"https://www.drogariaveracruz.com.br/busca?q={ean}")
            time.sleep(4) 
            
            # 1. VERIFICA SE O SITE REDIRECIONOU DIRETO PARA O PRODUTO
            url_atual_limpa = driver.current_url.split('?')[0]
            url_real = None
            
            if url_atual_limpa.endswith('/p'):
                print("   🔗 Site redirecionou direto para o produto!")
                url_real = driver.current_url
            else:
                # 2. SE NÃO REDIRECIONOU, PROCURA O LINK CORRETO NA LISTA
                elementos = driver.find_elements(By.TAG_NAME, "a")
                for el in elementos:
                    href = el.get_attribute("href")
                    if href:
                        href_limpo = href.split('?')[0]
                        # Exige que o link termine EXATAMENTE em /p (ignora categorias)
                        if href_limpo.endswith('/p'):
                            url_real = href
                            break
            
            if url_real:
                print(f"   🔗 Entrando no produto: {url_real}")
                driver.get(url_real)
                time.sleep(3)
                fonte = driver.page_source
                p_tabela, p_pix, p_cartao, status = extrair_tres_precos(fonte)
            else:
                p_tabela, p_pix, p_cartao, status = "0.00", "0.00", "0.00", "Não Encontrado na Busca"

            # Gravação
            df.at[index, 'Preco_De_Tabela'] = p_tabela
            df.at[index, 'Preco_Pix'] = p_pix
            df.at[index, 'Preco_Cartao'] = p_cartao
            df.at[index, 'Status_Preco'] = status
            
            print(f"   {status.upper()}: DE R$ {p_tabela} | PIX R$ {p_pix} | CARTÃO R$ {p_cartao}")

            contador += 1
            if contador % 5 == 0:
                df.to_csv('Precos_Vera_Cruz_Progresso.csv', index=False, sep=';', encoding='utf-8-sig')

        except Exception as e:
            print(f"   ❌ Erro de conexão do navegador.")
            df.at[index, 'Status_Preco'] = "Erro de Conexão"
            continue

    driver.quit()
    df.to_csv('Vera_Cruz_Refeitos.csv', index=False, sep=';', encoding='utf-8-sig')
    print("\n✨ Arquivo salvo: 'Vera_Cruz_Refeitos.csv'")

if __name__ == "__main__":
    extrair_por_busca_ean()
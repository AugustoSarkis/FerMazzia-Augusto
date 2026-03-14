import requests
from bs4 import BeautifulSoup
import concurrent.futures
import threading
import json
import csv
import time
import re

# Catraca de segurança para escrita simultânea no arquivo
trava_escrita = threading.Lock()

# ==========================================
# FUNÇÕES MATEMÁTICAS E DE LIMPEZA
# ==========================================
def limpar_preco(texto):
    if not texto:
        return None
    limpo = str(texto).replace('R$', '').replace('no cartão', '').strip()
    limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return None

def formatar_moeda(valor):
    if not valor or valor == 0:
        return 0
    return f"{valor:.2f}".replace('.', ',')

def calcular_desconto(original, com_desconto):
    if original and com_desconto and original > 0:
        if com_desconto >= original:
            return "-0.0%"
        desconto_perc = ((original - com_desconto) / original) * 100
        return f"-{desconto_perc:.1f}%"
    return 0

# ==========================================
# FASE 0: DESCOBRIR PÁGINAS
# ==========================================
def descobrir_total_paginas():
    print("🔭 FASE 0: Mapeando o tamanho do catálogo da Vera Cruz...")
    url_base = "https://www.drogariaveracruz.com.br/medicamentos/?p=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resposta = requests.get(url_base, headers=headers, timeout=10)
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        # Procura qualquer texto no HTML que tenha o padrão "Página X de Y"
        texto_paginacao = soup.find(string=re.compile(r'Página\s+\d+\s+de\s+\d+'))
        
        if texto_paginacao:
            # Extrai apenas o número final usando Regex
            match = re.search(r'de\s+(\d+)', texto_paginacao)
            if match:
                total = int(match.group(1))
                print(f"✅ Catálogo mapeado com sucesso: {total} páginas encontradas.")
                return total
                
    except Exception as e:
        print(f"❌ Erro ao ler a paginação: {e}")
        
    print("⚠️ Usando fallback de 1 página.")
    return 1

# ==========================================
# FASE 1: COLETA DE URLs
# ==========================================
def extrair_links_da_pagina(pagina):
    base_url = "https://www.drogariaveracruz.com.br/medicamentos/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    url_paginada = f"{base_url}?p={pagina}"
    links_da_pagina = []
    
    try:
        resposta = requests.get(url_paginada, headers=headers, timeout=10)
        if resposta.status_code != 200: return []
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        produtos = soup.find_all('div', class_='item-product')
        
        for prod in produtos:
            tag_a = prod.find('a', class_='item-image')
            if tag_a and 'href' in tag_a.attrs:
                link_completo = "https://www.drogariaveracruz.com.br" + tag_a['href']
                links_da_pagina.append(link_completo)
                
        return links_da_pagina
    except Exception:
        return []

def coletar_links_medicamentos_paralelo(total_paginas):
    print(f"🔎 FASE 1: Iniciando varredura paralela das {total_paginas} vitrines...")
    links_totais = []
    QTD_ROBOS_BATEDORES = 8
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=QTD_ROBOS_BATEDORES) as executor:
        paginas_para_raspar = range(1, total_paginas + 1)
        futuros = {executor.submit(extrair_links_da_pagina, p): p for p in paginas_para_raspar}
        
        concluidas = 0
        for futuro in concurrent.futures.as_completed(futuros):
            pagina_processada = futuros[futuro]
            concluidas += 1
            try:
                resultado_links = futuro.result()
                links_totais.extend(resultado_links)
                print(f"   -> Página {pagina_processada} mapeada! Progresso: {concluidas}/{total_paginas}")
            except Exception:
                pass
                
    links_unicos = list(set(links_totais))
    print(f"\n🎯 FASE 1 CONCLUÍDA! Total de URLs únicas: {len(links_unicos)}\n")
    return links_unicos

# ==========================================
# FASE 2: EXTRAÇÃO PROFUNDA
# ==========================================
def raspar_dados_produto(url, escritor, arquivo_csv):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resposta = requests.get(url, headers=headers, timeout=12)
        if resposta.status_code != 200: return "Erro de HTTP"
            
        soup = BeautifulSoup(resposta.text, 'html.parser')
        
        dados = {
            'Nome da Farmácia': 'VeraCruz',
            'EAN': '-',
            'Nome do produto': '-',
            'Status do produto': 'Indisponível',
            'Preço original': '-',
            'Preço PIX': '-',
            'Desconto PIX': '-',
            'Preço à vista no cartão': '-',
            'Desconto cartão': '-',
            'Subcategoria': '-',
            'Código do produto': '-',
            'URL do produto': url
        }

        # --- Subcategoria via Breadcrumb ---
        breadcrumb = soup.find('div', id='breadcrumb')
        if breadcrumb:
            itens = [li.text.strip() for li in breadcrumb.find_all('li') if li.text.strip()]
            if 'Medicamentos' in itens:
                idx = itens.index('Medicamentos')
                subcategorias = itens[idx+1:]
                if subcategorias:
                    dados['Subcategoria'] = " > ".join(subcategorias)

        # --- Nome do Produto ---
        nome_tag = soup.find(class_='name')
        if nome_tag: dados['Nome do produto'] = nome_tag.text.strip()

        # --- EAN e Código (via JSON-LD ou tags) ---
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            if s.string and ('gtin13' in s.string or 'sku' in s.string):
                try:
                    texto_json = s.string.replace('\r', '').replace('\n', '').strip()
                    if not texto_json.startswith('['): texto_json = f"[{texto_json}]"
                    data_list = json.loads(texto_json)
                    for item in data_list:
                        dados['EAN'] = item.get('gtin13', dados['EAN'])
                        dados['Código do produto'] = item.get('sku', dados['Código do produto'])
                except:
                    pass
                    
        if dados['EAN'] == '-':
            tag_ean = soup.find(class_='gtin13')
            if tag_ean: dados['EAN'] = tag_ean.text.strip()
            tag_cod = soup.find(class_=re.compile(r'C[oó]d|productReference|skuReference', re.IGNORECASE))
            if tag_cod: dados['Código do produto'] = tag_cod.text.strip()

        # --- Preços ---
        tag_original = soup.find(class_='unit-price')
        tag_pix = soup.find(class_=re.compile(r'sale-price.*money|sale-price-pix'))
        
        # O HTML da Vera Cruz usa a classe get_card_price dentro do bloco de parcelas
        tag_cartao = soup.find(class_='get_card_price')
        if not tag_cartao: 
            tag_cartao = soup.find(class_=re.compile(r'sale-price money'))

        val_original = limpar_preco(tag_original.text) if tag_original else None
        val_pix = limpar_preco(tag_pix.text) if tag_pix else None
        val_cartao = limpar_preco(tag_cartao.text) if tag_cartao else None

        # Resolve problema de preços cruzados na plataforma
        if val_original is None and val_cartao is not None:
            val_original = val_cartao

        dados['Preço original'] = formatar_moeda(val_original)
        dados['Preço PIX'] = formatar_moeda(val_pix)
        dados['Desconto PIX'] = calcular_desconto(val_original, val_pix)
        dados['Preço à vista no cartão'] = formatar_moeda(val_cartao)
        dados['Desconto cartão'] = calcular_desconto(val_original, val_cartao)

        # --- Status (Estoque) ---
        if soup.find('button', class_='btn-checkout'):
            dados['Status do produto'] = 'Disponível'
        else:
            dados['Status do produto'] = 'Esgotado'

        # Escrita segura
        with trava_escrita:
            escritor.writerow(dados)
            arquivo_csv.flush()
            
        return f"OK -> {dados['Nome do produto'][:30]}..."

    except Exception as e:
        return f"Falha: {e}"

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
def executar_spider_veracruz():
    nome_arquivo = 'Scraping_VeraCruz.csv'
    
    cabecalhos = [
        'Nome da Farmácia', 'EAN', 'Nome do produto', 'Status do produto', 
        'Preço original', 'Preço PIX', 'Desconto PIX', 'Preço à vista no cartão', 
        'Desconto cartão', 'Subcategoria', 'Código do produto', 'URL do produto'
    ]
    
    # Executa a Fase 0 (Descobre a quantidade dinamicamente)
    total_paginas = descobrir_total_paginas()
    
    # Executa a Fase 1
    links_para_raspar = coletar_links_medicamentos_paralelo(total_paginas)
    if not links_para_raspar: return

    print("\n🚀 FASE 2: Iniciando extração profunda (Multithreading)")
    print(f"Alvo: {len(links_para_raspar)} produtos. Salvando em '/home/ubuntu/.2_Dados/VeraCruz/{nome_arquivo}'.")
    print("-" * 60)
    
    with open(f"/home/ubuntu/.2_Dados/VeraCruz/{nome_arquivo}", mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=cabecalhos, delimiter=';')
        escritor.writeheader()

        QTD_ROBOS_MERGULHADORES = 15
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=QTD_ROBOS_MERGULHADORES) as executor:
            futuros = {executor.submit(raspar_dados_produto, link, escritor, arquivo_csv): link for link in links_para_raspar}
            
            concluidos = 0
            for futuro in concurrent.futures.as_completed(futuros):
                concluidos += 1
                resultado = futuro.result()
                print(f"[{concluidos}/{len(links_para_raspar)}] {resultado}")

    print(f"\n✅ Scraping finalizado! Base autônoma da Vera Cruz gerada com sucesso.")

if __name__ == "__main__":
    executar_spider_veracruz()
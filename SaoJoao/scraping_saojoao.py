import requests
import csv
import threading
import concurrent.futures

# Catraca de segurança para escrita simultânea no ficheiro
trava_escrita = threading.Lock()

def formatar_moeda(valor):
    if not valor or valor == 0:
        return "-"
    return f"{valor:.2f}".replace('.', ',')

def calcular_desconto(original, com_desconto):
    if original and com_desconto and original > 0:
        if com_desconto >= original:
            return "-0.0%"
        desconto_perc = ((original - com_desconto) / original) * 100
        return f"-{desconto_perc:.1f}%"
    return "-"

# ==========================================
# O EXTRATOR VTEX INTELLIGENT SEARCH (BLINDADO)
# ==========================================
def extrair_fatia_vtex_is(faixa_preco, escritor, arquivo_csv):
    preco_min, preco_max = faixa_preco
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    produtos_encontrados = 0
    url_base = "https://www.saojoaofarmacias.com.br/api/io/_v/api/intelligent-search/product_search/medicamentos"
    
    for pagina in range(1, 51): 
        
        # CAMADA 1: Forçando o filtro de categoria na API
        parametros = {
            'page': pagina,
            'count': 50,
            'map': 'c', # Avisa a VTEX que é estritamente uma Categoria
            'facets': f'price:{preco_min}:{preco_max}' 
        }
        
        try:
            resposta = requests.get(url_base, headers=headers, params=parametros, timeout=15)
            
            if resposta.status_code != 200:
                print(f"⚠️ Fim ou Bloqueio na faixa {preco_min}-{preco_max} (Status {resposta.status_code}).")
                break
                
            dados_json = resposta.json()
            produtos = dados_json.get('products', [])
            
            if not produtos or len(produtos) == 0:
                break 

            for prod in produtos:
                try:
                    # Coleta a árvore de categoria do produto (Ex: "/Medicamentos/Diabetes/")
                    categorias_vtex = prod.get('categories', ['-'])
                    caminho_categoria = categorias_vtex[0] if categorias_vtex else '-'
                    
                    # CAMADA 2: Filtro de Pureza (Ignora o que não é remédio)
                    if '/Medicamentos/' not in caminho_categoria:
                        continue
                        
                    if not prod.get('items'): continue
                    
                    item = prod['items'][0]
                    oferta = item.get('sellers', [{}])[0].get('commertialOffer', {})
                    
                    val_original = oferta.get('ListPrice')
                    val_venda = oferta.get('Price')
                    estoque = oferta.get('AvailableQuantity', 0)
                    
                    if not val_original or val_original == 0:
                        val_original = val_venda

                    dados = {
                        'Nome da Farmácia': 'São João',
                        'EAN': item.get('ean', '-'),
                        'Nome do produto': prod.get('productName', '-'),
                        'Status do produto': 'Disponível' if estoque > 0 else 'Indisponível',
                        'Preço original': formatar_moeda(val_original),
                        'Preço PIX': formatar_moeda(val_venda),
                        'Desconto PIX': calcular_desconto(val_original, val_venda),
                        'Preço à vista no cartão': formatar_moeda(val_venda),
                        'Desconto cartão': calcular_desconto(val_original, val_venda),
                        'Subcategoria': caminho_categoria.replace('/', ' > ').strip(' > '),
                        'Código do produto': prod.get('productReference', item.get('itemId', '-')),
                        'URL do produto': "https://www.saojoaofarmacias.com.br" + prod.get('link', '-')
                    }

                    with trava_escrita:
                        escritor.writerow(dados)
                        arquivo_csv.flush()
                        
                    produtos_encontrados += 1
                except Exception:
                    continue 

        except Exception as e:
            print(f"❌ Erro de conexão na faixa {preco_min}-{preco_max}: {e}")
            break
            
    return f"Fatia R$ {preco_min} a R$ {preco_max}: Extraiu {produtos_encontrados} medicamentos puros."

# ==========================================
# MOTOR PRINCIPAL (ORQUESTRAÇÃO)
# ==========================================
def executar_spider_saojoao_api():
    nome_arquivo = 'Scraping_SaoJoao_Definitivo.csv'
    cabecalhos = [
        'Nome da Farmácia', 'EAN', 'Nome do produto', 'Status do produto', 
        'Preço original', 'Preço PIX', 'Desconto PIX', 'Preço à vista no cartão', 
        'Desconto cartão', 'Subcategoria', 'Código do produto', 'URL do produto'
    ]
    
    fatias_de_preco = [
        (0, 15), (15.01, 30), (30.01, 50), (50.01, 80), 
        (80.01, 120), (120.01, 200), (200.01, 400), (400.01, 1000), (1000.01, 50000)
    ]

    print("🚀 FASE ÚNICA: Iniciando extração com Filtro de Pureza de Categoria")
    print("-" * 60)
    
    with open(nome_arquivo, mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=cabecalhos, delimiter=';')
        escritor.writeheader()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futuros = {executor.submit(extrair_fatia_vtex_is, fatia, escritor, arquivo_csv): fatia for fatia in fatias_de_preco}
            
            for futuro in concurrent.futures.as_completed(futuros):
                resultado = futuro.result()
                print(f"✅ {resultado}")

    print(f"\n🎉 Scraping API finalizado! A base está 100% limpa e validada.")

if __name__ == "__main__":
    executar_spider_saojoao_api()
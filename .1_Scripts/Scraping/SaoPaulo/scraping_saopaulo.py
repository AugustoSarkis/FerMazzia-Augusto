import asyncio
import aiohttp
import csv
import re
import os
import random
from datetime import datetime
import sys

# =========================================================
# CONFIGURAÇÕES DO PIPELINE
# =========================================================
ARQUIVO_SAIDA = "/home/ubuntu/.2_Dados/SaoPaulo/Scraping_SaoPaulo.csv"
CONCURRENCY_LIMIT = 5 

TAMANHO_LOTE = 2500
TEMPO_PAUSA_MINUTOS = 3 

CABECALHOS_CSV = [
    "Nome da Farmácia", "EAN", "Nome do produto", "Status do produto", 
    "Preço original", "Preço PIX", "Desconto PIX", 
    "Preço à vista no cartão", "Desconto cartão", 
    "Subcategoria", "Código do produto", "URL do produto"
]

HEADERS_REQUISICAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

bloqueios_consecutivos = 0

def carregar_checkpoint():
    urls_processadas = set()
    if os.path.exists(ARQUIVO_SAIDA):
        with open(ARQUIVO_SAIDA, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader, None) 
            for row in reader:
                if len(row) > 11:
                    urls_processadas.add(row[11])
    return urls_processadas

def formatar_moeda(valor):
    if valor is None or valor == "": return "0"
    return f"{float(valor):.2f}".replace(".", ",")

def calcular_desconto(preco_venda, preco_cheio):
    if not preco_venda or not preco_cheio or preco_cheio <= 0 or preco_venda >= preco_cheio:
        return "-"
    desconto = (1 - (preco_venda / preco_cheio)) * 100
    return f"-{desconto:.1f}%"

async def buscar_sitemap(session, url):
    print(f"[*] Lendo sitemap {url}...")
    try:
        async with session.get(url, headers=HEADERS_REQUISICAO, timeout=30) as response:
            if response.status == 200:
                xml_data = await response.text()
                urls = re.findall(r'<loc>(.*?)</loc>', xml_data)
                slugs = []
                for u in urls:
                    if "/p" in u or "drogariasaopaulo.com.br" in u:
                        partes = [p for p in u.split('/') if p]
                        if partes:
                            slug = partes[-2] if partes[-1] == 'p' else partes[-1]
                            slugs.append((slug, u))
                return slugs
            elif response.status == 404:
                return None
            return []
    except Exception:
        return []

async def extrair_dados_produto(session, slug, url_original, semaphore):
    global bloqueios_consecutivos
    api_url = f"https://www.drogariasaopaulo.com.br/api/catalog_system/pub/products/search/{slug}/p"
    
    async with semaphore: 
        try:
            # Jitter aleatório para simular comportamento humano
            await asyncio.sleep(random.uniform(0.3, 0.7)) 
            
            async with session.get(api_url, headers=HEADERS_REQUISICAO, timeout=20) as response:
                if response.status == 200:
                    bloqueios_consecutivos = 0 
                    dados = await response.json()
                    if dados and isinstance(dados, list):
                        return processar_json_vtex(dados[0], url_original)
                    return None
                
                elif response.status in [403, 429, 503]:
                    bloqueios_consecutivos += 1
                    return "BLOQUEIO"
                
                return None
        except Exception:
            return None

def processar_json_vtex(produto, url_original):
    try:
        # Extração Dinâmica de Subcategoria para QUALQUER produto
        subcategoria = "-"
        
        # Tenta pegar classe médica ou doenças primeiro (se for remédio)
        classe = produto.get("Classe do Medicamento", [])
        doencas = produto.get("Doenças & Complicações", [])
        
        if classe:
            subcategoria = classe[0]
        elif doencas:
            subcategoria = doencas[0]
        else:
            # Se for perfumaria, higiene, etc., pega a última categoria da árvore
            categorias = produto.get("categories", [])
            if categorias:
                cat_path = categorias[0] # Ex: "/Beleza e Higiene/Cabelos/"
                partes = [p.strip() for p in cat_path.strip("/").split("/") if p.strip()]
                if partes:
                    # Pega a última subcategoria disponível (a mais específica)
                    subcategoria = partes[-1]
        
        nome_farmacia = "SãoPaulo"
        codigo_produto = produto.get("productId", "-")
        nome_produto = produto.get("productName", "-")
        
        items = produto.get("items", [])
        if not items: return None
        primeiro_item = items[0]
        ean = primeiro_item.get("ean", "-")
        
        sellers = primeiro_item.get("sellers", [])
        if not sellers: return None
        oferta = sellers[0].get("commertialOffer", {})
        
        preco_venda = oferta.get("Price", 0)
        preco_cheio = oferta.get("ListPrice", 0)
        estoque = oferta.get("AvailableQuantity", 0)
        disponivel = oferta.get("IsAvailable", False)
        
        status_produto = "Disponível" if disponivel and estoque > 0 else "Indisponível"
        
        str_preco_original = formatar_moeda(preco_cheio) if preco_cheio else "-"
        str_preco_pix = formatar_moeda(preco_venda) if preco_venda else "-"
        str_preco_cartao = formatar_moeda(preco_venda) if preco_venda else "-"
        desconto_pix = calcular_desconto(preco_venda, preco_cheio)
        desconto_cartao = calcular_desconto(preco_venda, preco_cheio)

        if status_produto == "Indisponível":
            str_preco_original = "-"
            str_preco_pix = "-"
            str_preco_cartao = "-"
            desconto_pix = "-"
            desconto_cartao = "-"

        return [
            nome_farmacia, ean, nome_produto, status_produto,
            str_preco_original, str_preco_pix, desconto_pix,
            str_preco_cartao, desconto_cartao,
            subcategoria, codigo_produto, url_original
        ]
    except Exception:
        return None

async def orquestrador_scraping():
    global bloqueios_consecutivos
    inicio = datetime.now()
    print(f"[*] Iniciando Scraping do Catálogo Completo às {inicio.strftime('%H:%M:%S')}")
    
    urls_ja_processadas = carregar_checkpoint()
    
    if len(urls_ja_processadas) == 0:
        with open(ARQUIVO_SAIDA, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(CABECALHOS_CSV)
        print("[*] Nenhum arquivo anterior detectado. Iniciando do zero.")
    else:
        print(f"[+] Retomando trabalho! {len(urls_ja_processadas)} URLs já constam no CSV.")

    # =========================================================
    # FASE 1: LER SITEMAPS
    # =========================================================
    connector_sitemap = aiohttp.TCPConnector(limit=CONCURRENCY_LIMIT)
    todos_produtos = []
    
    async with aiohttp.ClientSession(connector=connector_sitemap) as session_sitemap:
        sitemap_id = 1
        while True:
            url_sitemap_atual = f"https://www.drogariasaopaulo.com.br/sitemap/product-{sitemap_id}.xml"
            produtos_encontrados = await buscar_sitemap(session_sitemap, url_sitemap_atual)
            
            if produtos_encontrados is None:
                break
            if produtos_encontrados:
                todos_produtos.extend(produtos_encontrados)
            sitemap_id += 1
            
    if not todos_produtos:
        print("[-] Falha ao ler sitemaps. Abortando.")
        return

    # Remove o que já foi baixado para não duplicar
    fila_de_trabalho = [(slug, url) for slug, url in todos_produtos if url not in urls_ja_processadas]
    total_fila = len(fila_de_trabalho)
    
    print(f"\n[*] Total do catálogo: {len(todos_produtos)} URLs.")
    print(f"[*] Restam para avaliar nesta execução: {total_fila} URLs.")
    
    if total_fila == 0:
        print("[+] Tudo já foi extraído. O banco de dados está completo!")
        return
        
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    produtos_salvos_geral = 0
    
    # =========================================================
    # FASE 2: LOOP DE LOTES COM DESTRUIÇÃO DE CONEXÃO E CHECKPOINT
    # =========================================================
    for i in range(0, total_fila, TAMANHO_LOTE):
        lote_atual_urls = fila_de_trabalho[i:i + TAMANHO_LOTE]
        numero_lote = (i // TAMANHO_LOTE) + 1
        
        print(f"\n" + "="*50)
        print(f"[*] INICIANDO LOTE {numero_lote} (URLs de {i+1} a {min(i+TAMANHO_LOTE, total_fila)})")
        print("="*50)
        
        # Destrói as conexões antigas para não acionar o Cloudflare
        connector = aiohttp.TCPConnector(limit=CONCURRENCY_LIMIT, force_close=True)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for slug, url_original in lote_atual_urls:
                task = asyncio.create_task(extrair_dados_produto(session, slug, url_original, semaphore))
                tasks.append(task)
                
            processados_neste_lote = 0
            
            with open(ARQUIVO_SAIDA, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                
                for task in asyncio.as_completed(tasks):
                    linha_dados = await task
                    
                    if linha_dados == "BLOQUEIO":
                        if bloqueios_consecutivos >= 10:
                            print("\n[!] ALERTA VERMELHO: Múltiplos bloqueios WAF detectados.")
                            print(f"[!] O Cloudflare bloqueou a máquina. Salvando {produtos_salvos_geral} produtos e abortando.")
                            for t in tasks: t.cancel()
                            sys.exit(1) # Mata o script com erro para saber que travou
                        continue 
                    
                    processados_neste_lote += 1
                    
                    if linha_dados is not None:
                        writer.writerow(linha_dados)
                        file.flush() # Força gravação instantânea no disco
                        produtos_salvos_geral += 1
                    
                    if processados_neste_lote % 250 == 0 or processados_neste_lote == len(lote_atual_urls):
                        print(f"    -> Lote {numero_lote}: {processados_neste_lote}/{len(lote_atual_urls)} URLs avaliadas | +{produtos_salvos_geral} produtos salvos")

        # =========================================================
        # PAUSA ESTRATÉGICA
        # =========================================================
        if i + TAMANHO_LOTE < total_fila:
            print(f"\n[Zzz] Lote {numero_lote} concluído. Conexão TCP completamente encerrada.")
            print(f"[Zzz] Iniciando pausa de {TEMPO_PAUSA_MINUTOS} minutos para o IP esfriar no WAF...")
            await asyncio.sleep(TEMPO_PAUSA_MINUTOS * 60)

    fim = datetime.now()
    tempo_total = (fim - inicio).total_seconds()
    print(f"\n[+] Scraping do Catálogo Finalizado!")
    print(f"[+] Total de novos produtos inseridos no CSV: {produtos_salvos_geral}")
    print(f"[+] Tempo de execução total: {int(tempo_total // 60)}m {int(tempo_total % 60)}s")

if __name__ == "__main__":
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(orquestrador_scraping())
        finally:
            loop.close()
    else:
        asyncio.run(orquestrador_scraping())
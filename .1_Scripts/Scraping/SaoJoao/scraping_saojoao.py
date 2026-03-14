import requests
import concurrent.futures
import threading
import csv
import os
import time
import random
from datetime import datetime

# =========================================================
# SÃO JOÃO + API + MULTITHREAD
# =========================================================
ARQUIVO_SAIDA = "/home/ubuntu/.2_Dados/SaoJoao/Scraping_SaoJoao.csv"

URL_BASE_API = "https://www.saojoaofarmacias.com.br/api/catalog_system/pub/products/search/medicamentos"

# Fatiamento de Segurança para não passar de 2500 produtos
FAIXAS_DE_PRECO = [
    (0, 15), (15.01, 30), (30.01, 50), (50.01, 80), 
    (80.01, 120), (120.01, 200), (200.01, 400), 
    (400.01, 1000), (1000.01, 50000)
]

CABECALHOS_CSV = [
    "Nome da Farmácia", "EAN", "Nome do produto", "Status do produto", 
    "Preço original", "Preço PIX", "Desconto PIX", 
    "Preço à vista no cartão", "Desconto cartão", 
    "Subcategoria", "Código do produto", "URL do produto"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

# A Trava de Segurança para os robôs não atropelarem o arquivo CSV
trava_escrita = threading.Lock()

# Flag global para avisar os robôs que a fatia acabou
fim_da_fatia = False

# ==========================================
# FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==========================================
def carregar_checkpoint():
    codigos_processados = set()
    if os.path.exists(ARQUIVO_SAIDA):
        with open(ARQUIVO_SAIDA, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader, None) 
            for row in reader:
                if len(row) > 10:
                    codigos_processados.add(row[10])
    return codigos_processados

def formatar_moeda(valor):
    if not valor: return "0"
    return f"{float(valor):.2f}".replace(".", ",")

def calcular_desconto(preco_venda, preco_cheio):
    if not preco_venda or not preco_cheio or preco_cheio <= 0 or preco_venda >= preco_cheio:
        return "-"
    desconto = (1 - (preco_venda / preco_cheio)) * 100
    return f"-{desconto:.1f}%"

def processar_json_vtex(produto):
    try:
        nome_farmacia = "SãoJoão"
        codigo_produto = produto.get("productId", "-")
        nome_produto = produto.get("productName", "-")
        url_original = produto.get("link", "-")
        
        categorias = produto.get("categories", [])
        subcategoria = "-"
        if categorias:
            partes = [p.strip() for p in categorias[0].strip("/").split("/") if p.strip()]
            if len(partes) > 1:
                subcategoria = partes[1]

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
            str_preco_original = "0"
            str_preco_pix = "0"
            str_preco_cartao = "0"
            desconto_pix = "0"
            desconto_cartao = "0"

        return {
            "Nome da Farmácia": nome_farmacia, "EAN": ean, "Nome do produto": nome_produto, 
            "Status do produto": status_produto, "Preço original": str_preco_original, 
            "Preço PIX": str_preco_pix, "Desconto PIX": desconto_pix,
            "Preço à vista no cartão": str_preco_cartao, "Desconto cartão": desconto_cartao,
            "Subcategoria": subcategoria, "Código do produto": codigo_produto, "URL do produto": url_original
        }
    except Exception:
        return None

# ==========================================
# O WORKER
# ==========================================
def raspar_pagina_api(sessao, preco_min, preco_max, pagina, escritor, arquivo_csv, checkpoint_set):
    global fim_da_fatia
    
    if fim_da_fatia: return 0

    from_idx = (pagina - 1) * 50
    to_idx = (pagina * 50) - 1
    
    url = f"{URL_BASE_API}?fq=P:[{preco_min} TO {preco_max}]&_from={from_idx}&_to={to_idx}"
    
    try:
        # Pausa leve
        time.sleep(random.uniform(0.5, 1.5))
        
        resposta = sessao.get(url, headers=HEADERS, timeout=15)
        
        if resposta.status_code in [200, 206]:
            dados = resposta.json()
            
            # Se a página vier vazia, avisa que a fatia acabou
            if not dados or len(dados) == 0:
                fim_da_fatia = True
                return 0
                
            produtos_salvos_na_thread = 0
            linhas_processadas = []
            
            for produto in dados:
                cod = produto.get("productId")
                if cod and cod not in checkpoint_set:
                    linha_limpa = processar_json_vtex(produto)
                    if linha_limpa:
                        linhas_processadas.append(linha_limpa)
                        checkpoint_set.add(cod)
            
            # Trava o CSV rapidamente, escreve o bloco e solta a trava
            if linhas_processadas:
                with trava_escrita:
                    escritor.writerows(linhas_processadas)
                    arquivo_csv.flush()
                produtos_salvos_na_thread += len(linhas_processadas)
                
            return produtos_salvos_na_thread
            
        elif resposta.status_code in [403, 429]:
            print(f"    [!] WAF rosnou na pág {pagina} (Status {resposta.status_code})")
            return 0
    except Exception as e:
        return 0
        
    return 0

# ==========================================
# O ORQUESTRADOR
# ==========================================
def iniciar_pipeline_saojoao():
    inicio = datetime.now()
    print("============================================================")
    print(f"🚀 INICIANDO SCRAPING HÍBRIDO SÃO JOÃO - {inicio.strftime('%H:%M:%S')}")
    print("============================================================")

    # Cria a pasta se não existir
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    
    codigos_ja_processados = carregar_checkpoint()
    modo_abertura = 'a' if len(codigos_ja_processados) > 0 else 'w'
    
    if modo_abertura == 'w':
        print("[*] Base limpa detectada. Iniciando do zero.")
    else:
        print(f"[+] Retomando! {len(codigos_ja_processados)} medicamentos já constam no banco.")

    total_geral_inseridos = 0
    QTD_ROBOS_SIMULTANEOS = 5 # Seguro contra WAF.

    with open(ARQUIVO_SAIDA, mode=modo_abertura, newline='', encoding='utf-8') as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=CABECALHOS_CSV, delimiter=';')
        if modo_abertura == 'w':
            escritor.writeheader()
            
        # Keep-Alive
        with requests.Session() as sessao:
            
            for preco_min, preco_max in FAIXAS_DE_PRECO:
                global fim_da_fatia
                fim_da_fatia = False
                
                print(f"\n[+] Extraindo Fatia R$ {preco_min} a R$ {preco_max}...")
                
                todas_as_paginas = list(range(1, 51))
                produtos_nesta_fatia = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=QTD_ROBOS_SIMULTANEOS) as executor:
                    futuros = {executor.submit(raspar_pagina_api, sessao, preco_min, preco_max, pag, escritor, arquivo_csv, codigos_ja_processados): pag for pag in todas_as_paginas}
                    
                    for futuro in concurrent.futures.as_completed(futuros):
                        pagina_responsavel = futuros[futuro]
                        try:
                            qtd_salva = futuro.result()
                            produtos_nesta_fatia += qtd_salva
                        except Exception:
                            pass
                            
                print(f"    -> Fatia concluída! Rendimento: +{produtos_nesta_fatia} novos medicamentos.")
                total_geral_inseridos += produtos_nesta_fatia

    fim = datetime.now()
    tempo_total = (fim - inicio).total_seconds()
    print(f"\n============================================================")
    print(f"🎉 PIPELINE DA SÃO JOÃO FINALIZADO!")
    print(f"[+] Novos itens adicionados: {total_geral_inseridos}")
    print(f"[+] Total no Data Lake: {len(codigos_ja_processados)}")
    print(f"[+] Tempo de execução: {int(tempo_total // 60)}m {int(tempo_total % 60)}s")
    print(f"============================================================")

if __name__ == "__main__":
    iniciar_pipeline_saojoao()
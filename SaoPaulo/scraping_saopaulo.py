import requests
import pandas as pd

def extrair_dados_api_vtex(url_api):
    print("Conectando diretamente ao banco de dados da Drogaria São Paulo...")
    
    # O User-Agent continua sendo importante para a VTEX não achar que somos um ataque DDoS
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    resposta = requests.get(url_api, headers=headers)
    
    if resposta.status_code != 200:
        print(f"Erro na conexão! Código: {resposta.status_code}")
        return
        
    # A mágica acontece aqui: O Python transforma o texto do site num Dicionário gigante!
    produtos_json = resposta.json()
    print(f"Sucesso! {len(produtos_json)} produtos carregados em milissegundos.\n")
    
    lista_final = []
    
    for produto in produtos_json:
        try:
            # Na VTEX, as informações de preço e estoque ficam dentro de "items" -> "sellers" -> "commertialOffer"
            item = produto['items'][0]
            oferta = item['sellers'][0]['commertialOffer']
            
            # Pegando as informações básicas
            nome = produto.get('productName', '-')
            ean = item.get('ean', '-')
            codigo = item.get('itemId', '-')
            link = produto.get('link', '-')
            
            # Pegando a Categoria (A VTEX devolve uma lista ex: ['/Saúde/Medicamentos/', '/Saúde/'])
            categorias = produto.get('categories', [])
            categoria_limpa = categorias[0].strip('/') if categorias else '-'
            
            # Analisando o Estoque e Preço
            estoque = oferta.get('AvailableQuantity', 0)
            status = 'Disponível' if estoque > 0 else 'Indisponível'
            
            preco_original = oferta.get('ListPrice', 0.0)
            preco_venda = oferta.get('Price', 0.0) # Preço com desconto
            
            # Calculando o Desconto Percentual
            if preco_original > 0 and preco_venda < preco_original:
                desconto_perc = ((preco_original - preco_venda) / preco_original) * 100
                desconto_formatado = f"-{desconto_perc:.1f}%"
            else:
                desconto_formatado = "-"
            
            # Montando a linha da nossa tabela
            dados = {
                'Farmácia': 'Drogaria São Paulo',
                'EAN': ean,
                'Nome_do_Produto': nome,
                'Status': status,
                'Categoria': categoria_limpa,
                'Código': codigo,
                'Preço_De_Tabela': f"{preco_original:.2f}" if preco_original > 0 else "-",
                'Preço_Venda': f"{preco_venda:.2f}" if preco_venda > 0 else "-",
                'Desconto': desconto_formatado,
                'URL': link
            }
            
            lista_final.append(dados)
            
        except Exception as e:
            print(f"Erro ao processar o produto {produto.get('productName')}: {e}")
            
    # Salva tudo no Excel num piscar de olhos
    df = pd.DataFrame(lista_final)
    nome_arquivo = "Scraping_API_DrogariaSaoPaulo.csv"
    df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig', sep=';')
    
    print(f"✅ Scraping Finalizado! Tabela salva como: {nome_arquivo}")
    print(df.head()) # Mostra as 5 primeiras linhas no terminal

if __name__ == "__main__":
    # A URL maravilhosa que você encontrou!
    url_vtex = "https://www.drogariasaopaulo.com.br/api/catalog_system/pub/products/search?_from=0&_to=49&fq=skuId:887528&fq=skuId:887455&fq=skuId:155349&fq=skuId:887951&fq=skuId:862029&fq=skuId:841188&fq=skuId:819000&fq=skuId:701173&fq=skuId:684333&fq=skuId:681393&fq=skuId:668419&fq=skuId:645958&fq=skuId:602809&fq=skuId:602426&fq=skuId:530174&fq=skuId:525529&fq=skuId:314625&fq=skuId:308390&fq=skuId:302007&fq=skuId:290602&fq=skuId:220850&fq=skuId:128805&fq=skuId:116408&fq=skuId:264&fq=skuId:902586&fq=skuId:898350&fq=skuId:888060&fq=skuId:862045&fq=skuId:852759&fq=skuId:824003&fq=skuId:818445&fq=skuId:785350&fq=skuId:785296&fq=skuId:761770&fq=skuId:730343&fq=skuId:724815&fq=skuId:721514&fq=skuId:702269&fq=skuId:702234&fq=skuId:693189&fq=skuId:690481&fq=skuId:690473&fq=skuId:685429&fq=skuId:679909&fq=skuId:674133&fq=skuId:674125&fq=skuId:668435&fq=skuId:655031"
    
    extrair_dados_api_vtex(url_vtex)
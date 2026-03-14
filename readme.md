# 💊 Projeto FerMazzia: Pipeline Autônomo de Inteligência de Preços

Este repositório contém o código-fonte da arquitetura de dados desenvolvida para a rede de farmácias **FerMazzia** (Projeto Poli Júnior). O sistema consiste em uma esteira (pipeline) automatizada de Web Scraping, Engenharia de Dados e Fuzzy Matching, projetada para rodar de forma 100% autônoma e otimizada na nuvem da AWS (Amazon Web Services).

## 🏗️ Arquitetura em Nuvem (AWS)

Para garantir alta performance com o menor custo possível (aproveitando o *Free Tier*), o projeto utiliza um padrão de **Orquestração Efêmera**:

1. **Amazon EventBridge (Cron Trigger):** Atua como o despertador do sistema. De madrugada, ele envia um sinal para ligar a máquina virtual.
2. **Amazon EC2 (Ubuntu):** A instância "acorda" e, através de um gatilho `@reboot` no *crontab* do Linux, executa automaticamente o ambiente virtual Python e o script orquestrador (`comando_unificado.py`).
3. **Extração & Processamento (Local na EC2):** Os robôs realizam a extração de dados do cliente, raspagem paralela/API dos concorrentes e o cruzamento matemático dos produtos.
4. **Amazon S3 (Data Lake):** Os arquivos consolidados (`Base_Cruzada_*.csv`) e os relatórios de execução (`log_execucao.txt`) são enviados via `boto3` para o bucket `fermazzia-equipe01` nas pastas `/raw` e `/logs`.
5. **Auto-Shutdown:** Assim que o upload termina, a máquina virtual desliga a si mesma (`sudo shutdown -h now`), garantindo que não haja cobranças por horas ociosas.

## 📂 Estrutura do Repositório

O projeto foi refatorado para uma arquitetura modular, separando scripts executáveis, arquivos de saída e logs do sistema:

```text
📦 FerMazzia-Pipeline
 ┣ 📂 .1_Scripts
 ┃ ┣ 📜 extracao_dados_cliente.py     # ETL do banco de dados interno da farmácia
 ┃ ┗ 📂 Scraping                      # Módulos independentes por concorrente
 ┃   ┣ 📂 FarmaPonte
 ┃   ┃ ┣ 📜 matching_farmaponte.py    # Algoritmo de Fuzzy Matching (TheFuzz)
 ┃   ┃ ┗ 📜 scraping_farmaponte.py    # Multithreading (BeautifulSoup)
 ┃   ┣ 📂 SaoJoao
 ┃   ┃ ┣ 📜 matching_saojoao.py       # Algoritmo de Fuzzy Matching (TheFuzz)
 ┃   ┃ ┗ 📜 scraping_saojoao.py       # Extração via API (VTEX Intelligent Search)
 ┃   ┗ 📂 VeraCruz
 ┃     ┣ 📜 matching_veracruz.py      # Algoritmo de Fuzzy Matching (TheFuzz)
 ┃     ┗ 📜 scraping_veracruz.py      # Multithreading (BeautifulSoup)
 ┣ 📂 .2_Dados                        # Diretórios temporários de armazenamento
 ┃ ┣ 📂 Cliente
 ┃ ┃ ┗ 📊 Historico_Vendas_Consolidado.csv
 ┃ ┣ 📂 FarmaPonte
 ┃ ┃ ┗ 📊 Base_Cruzada_FarmaPonte.csv
 ┃ ┣ 📂 SaoJoao
 ┃ ┃ ┗ 📊 Base_Cruzada_SaoJoao.csv
 ┃ ┗ 📂 VeraCruz
 ┃   ┗ 📊 Base_Cruzada_VeraCruz.csv
 ┣ 📂 .3_Logs
 ┃ ┗ 📝 log_execucao.txt              # Diário de bordo interceptado via sys.stdout
 ┣ 📜 comando_unificado.py            # Orquestrador Master (Gatilho da EC2)
 ┗ 📜 requirements.txt                # Dependências do ambiente Python

```

 ## ⚙️ Como o Pipeline Funciona (Fluxo de Execução)

O arquivo central `comando_unificado.py` utiliza a biblioteca `subprocess` para ditar o ritmo da operação em fases estritas:

* **Fase 1 (Configuração da Função Lambda):** Usando Event Bridge como trigger da função, ela, dia sim dia não, ao meio dia, liga a máquina EC2.
* **Fase 2 (Função Reebot):** Ao acordar, usando a função `@reboot`, a máquina executa o script `comando_unificado.py` toda vez que é ligada, desencadeando o resto dos processos.
* **Fase 1 (Coleta Mestra):** Aciona o script `extracao_dados_cliente.py` para gerar a base atualizada de produtos da FerMazzia.
* **Fase 2 (Web Scraping):** Dispara os robôs de coleta da FarmaPonte, VeraCruz e São João. Os scripts lidam com bloqueios, paginações ocultas e fatiamento de preços (*Price Bucketing*) de forma assíncrona/multithread.
* **Fase 3 (Fuzzy Matching):** Os scripts de *matching* são acionados. Utilizando o motor `token_sort_ratio` (com nota de corte rigorosa de 70%), o algoritmo compara a base do cliente com o scraping, unifica as strings, trata categorias, preenche valores nulos com zero absoluto e impõe um *schema* estrito.
* **Fase 4 (Transferência S3):** O orquestrador identifica os CSVs de cruzamento finalizados e faz o upload assíncrono para o AWS S3.
* **Fase 5 (Logging & Encerramento):** O log completo da operação é salvo e enviado para a nuvem, seguido do comando de *power-off* do Linux.

---

## 🚀 Tecnologias Utilizadas

* **Linguagem:** Python 3.x
* **Scraping & Requests:** `requests`, `beautifulsoup4`, `lxml`
* **Processamento de Dados:** `pandas`, `thefuzz`, `python-Levenshtein`
* **Cloud & Integração:** `boto3` (AWS SDK), Bash Scripting (Crontab/Linux)

## 💻 Como Executar e Testar Localmente

Para rodar este pipeline no seu próprio computador antes de fazer o *deploy* para a AWS, siga os passos abaixo:

### 1. Clonar o Repositório
```bash
git clone [https://github.com/seu-usuario/FerMazzia-Pipeline.git](https://github.com/seu-usuario/FerMazzia-Pipeline.git)
cd FerMazzia-Pipeline
```
### 2. Criar e Ativar o Ambiente Virtual
É fortemente recomendado isolar as dependências do projeto para não gerar conflitos na sua máquina. No terminal, execute:
```bash
python3 -m venv env && source env/bin/activate
```
* (Nota: Se estiver a utilizar o Windows, o comando de ativação é env\Scripts\activate)

### 3. Instalar as Dependências
Com o ambiente ativado (env) visível no seu terminal, instale as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```
### 4. Configurar Credenciais da AWS (Crucial) e do Google BigQuery
Como o comando unificado utiliza a biblioteca boto3 para enviar os arquivos finais para o Data Lake, você precisa ter as suas credenciais da AWS configuradas localmente e
Se tiver o AWS CLI instalado, basta executar:
```bash
aws configure
```

Além disso, para que o `comando_unificado.py` consiga acessar a Data Base da FerMazzia, é necessário anexar o caminho local para as `Credenciais.json` e inseri-las nesse trecho do código do `extracao_dados_cliente.py`.
```python 
# Aponte para a sua chave JSON da FerMazzia
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ADICIONE_O_CAMINHO_PARA_SUA_CHAVE_JSON_AQUI.json"
```
* Dica de Teste Offline: Se quiser testar apenas o funcionamento do Web Scraping e do Fuzzy Matching sem fazer o upload para a nuvem, abra arquivo `comando_unificado.py` e comente as linhas que chamam a função `upload_para_s3()`.

### 5. Executar o Comando Unificado
com o ambiente preparado, execute o seguinte comando:
```bash
cd .\.1_Scripts
python3 comando_unificado.py
```
O script fará toda a extração, limpeza e cruzamento. Você poderá acompanhar o progresso diretamente no terminal ou através do arquivo de diário de bordo gerado na pasta de logs do bucket.
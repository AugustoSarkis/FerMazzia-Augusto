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

 ## ⚙️ Como o Pipeline Funciona (Fluxo de Execução)

O arquivo central `comando_unificado.py` utiliza a biblioteca `subprocess` para ditar o ritmo da operação em fases estritas:

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
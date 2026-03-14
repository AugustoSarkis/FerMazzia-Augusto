import subprocess
import boto3
import os
import time
import sys
from datetime import datetime

# ==========================================
# O LOGGER
# ==========================================
ARQUIVO_LOG_LOCAL = "log_execucao.txt"

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # Força a gravação imediata no arquivo

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Redireciona as saídas padrão (sucessos e erros) para o nosso Logger
sys.stdout = Logger(ARQUIVO_LOG_LOCAL)
sys.stderr = sys.stdout

# ==========================================
# CONFIGURAÇÕES DO PROJETO
# ==========================================
NOME_BUCKET = "fermazzia-equipe01" 

# ----------------------------------------------------
# CAMINHO ABSOLUTO DO PYTHON NO AMBIENTE VIRTUAL
# ----------------------------------------------------
PYTHON_BIN = "/home/ubuntu/fermazzia_env/bin/python3"

SCRIPTS_EXTRACAO_SCRAPING = [
    # Extracao de dados do cliente
    "/home/ubuntu/.1_Scripts/extracao_dados_cliente.py",
    
    # Scraping dos dados:
    "/home/ubuntu/.1_Scripts/Scraping/FarmaPonte/scraping_farmaponte.py",
    "/home/ubuntu/.1_Scripts/Scraping/VeraCruz/scraping_veracruz.py",
    "/home/ubuntu/.1_Scripts/Scraping/SaoJoao/scraping_saojoao.py",
    "/home/ubuntu/.1_Scripts/Scraping/SaoPaulo/scraping_saopaulo.py"
]

SCRIPTS_MATCHING = {
    "/home/ubuntu/.1_Scripts/Scraping/FarmaPonte/matching_farmaponte.py": "/home/ubuntu/.2_Dados/FarmaPonte/Base_Cruzada_FarmaPonte.csv",
    "/home/ubuntu/.1_Scripts/Scraping/VeraCruz/matching_veracruz.py": "/home/ubuntu/.2_Dados/VeraCruz/Base_Cruzada_VeraCruz.csv",
    "/home/ubuntu/.1_Scripts/Scraping/SaoJoao/matching_saojoao.py": "/home/ubuntu/.2_Dados/SaoJoao/Base_Cruzada_SaoJoao.csv",
    "/home/ubuntu/.1_Scripts/Scraping/SaoPaulo/matching_saopaulo.py": "/home/ubuntu/.2_Dados/SaoPaulo/Base_Cruzada_SaoPaulo.csv"
}

def executar_script(nome_script):
    print(f"\n🚀 Iniciando execução de: {nome_script}")
    try:
        resultado = subprocess.run([PYTHON_BIN, nome_script], capture_output=True, text=True, check=True)
        
        # Imprime o que o script secundário falou (o Logger vai gravar isso no txt)
        if resultado.stdout:
            print(resultado.stdout)
            
        print(f"✅ {nome_script} finalizado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro crítico ao executar {nome_script}. Código de erro: {e.returncode}")
        if e.stdout: print(f"Log do erro: {e.stdout}")
        if e.stderr: print(f"Detalhe do erro: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"⚠️ O script {nome_script} não foi encontrado no diretório.")
        return False

def upload_para_s3(arquivo_local, chave_s3):
    s3_client = boto3.client('s3')
    try:
        print(f"☁️ Enviando {arquivo_local} para s3://{NOME_BUCKET}/{chave_s3}...")
        s3_client.upload_file(arquivo_local, NOME_BUCKET, chave_s3)
        print("✅ Upload concluído!")
    except Exception as e:
        print(f"❌ Erro no upload de {arquivo_local}: {e}")

def iniciar_pipeline():
    print("==========================================")
    print(f" INICIANDO PIPELINE DE DADOS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ")
    print("==========================================")
    
    print("\n--- FASE 1: Extração e Scraping ---")
    for script in SCRIPTS_EXTRACAO_SCRAPING:
        executar_script(script)
        
    print("\n--- FASE 2: Processamento e Matching ---")
    for script_match in SCRIPTS_MATCHING.keys():
        executar_script(script_match)
        
    print("\n==========================================")
    print(" INICIANDO TRANSFERÊNCIA PARA O DATA LAKE ")
    print("==========================================")
    
    for arquivo_csv in SCRIPTS_MATCHING.values():
        if os.path.exists(arquivo_csv):
            nome_limpo_arquivo = os.path.basename(arquivo_csv)
            chave_destino = f"raw/{nome_limpo_arquivo}" 
            upload_para_s3(arquivo_csv, chave_destino)
        else:
            print(f"⚠️ Arquivo {arquivo_csv} não encontrado. O upload foi pulado.")
            
    print("\n==========================================")
    print(" SALVANDO LOGS E ENCERRANDO ")
    print("==========================================")
    print("🛑 Pipeline concluído. Salvando diário de bordo e preparando desligamento em 10 segundos...")
    
    # ----------------------------------------------------
    # UPLOAD DO ARQUIVO DE LOG (ÚLTIMA AÇÃO ANTES DO FIM)
    # ----------------------------------------------------
    # Restaura o terminal original para liberar o arquivo de texto
    sys.stdout = sys.stdout.terminal
    
    # Gera um nome único com a data de hoje, ex: log_2026-03-13.txt
    nome_log_s3 = f"logs/log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    upload_para_s3(ARQUIVO_LOG_LOCAL, nome_log_s3)
    
    time.sleep(10) # Pequena pausa para garantir que o upload termine na nuvem
    
    # Para ativar o desligamento automático, descomente a linha abaixo. CUIDADO: Isso desligará a máquina imediatamente após a execução!
    # os.system("sudo shutdown -h now")

if __name__ == "__main__":
    iniciar_pipeline()
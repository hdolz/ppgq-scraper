import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import time
import smtplib
import os
import datetime
import glob
import Levenshtein

url = "https://ppgq.ufam.edu.br/"
main = ""
interval = 3600 # in seconds
timeout = 10 # in seconds
max_retries = 3  # Número máximo de tentativas
retry_backoff_factor = 2  # Fator de retrocesso entre as tentativas (1 = sem retrocesso)
retry_status_forcelist = [500, 502, 503, 504]  # Códigos de status HTTP que acionam retentativas
keepRunning = True
subject = "Atualização na página do PPGQ"
body = "Parece que houve uma atualização na página do PPGQ. Por favor, verifique."
sender = ""
password = ""
recipients = [""]

def sendEmail(subject, body, sender, recipients, password):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender, password)
       smtp_server.sendmail(sender, recipients, msg.as_string())
    print("Email notification sent!")

def loadMain():
    pasta_logs = 'datalog'
    padrao_nome_arquivo = 'log_*.html'
    arquivos = glob.glob(os.path.join(pasta_logs, padrao_nome_arquivo))
    arquivos_ordenados = sorted(arquivos, key=lambda arquivo: os.path.getmtime(arquivo), reverse=True)
    if arquivos_ordenados:
        arquivo_mais_recente = arquivos_ordenados[0]
        with open(arquivo_mais_recente, 'r', encoding="utf-8") as arquivo:
            print(f'Last change loaded from file: {arquivo_mais_recente}')
            conteudo = arquivo.read()
            return conteudo
    else:
        print('Nenhum arquivo encontrado.')
        return None
    
def writeFile():
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"datalog/log_{formatted_datetime}.html"
    logs_dir = os.path.dirname(file_name)
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    with open(file_name, 'w', encoding="utf-8") as file:
        file.write(main)

main = loadMain()
while keepRunning:
    try:
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff_factor,
            status_forcelist=retry_status_forcelist
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        response = session.get(url, timeout=timeout)
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            main_tag = soup.find('main')
            main_string = str(main_tag)
            # needed to match the strings when loaded from log file (when loaded from file string comes with \n\n)
            main_string = main_string.replace('\r\n', '\n\n')
            if main == None:
                print("Main initialized from response")
                main = main_string
                writeFile()
            distancia = Levenshtein.distance(main, main_string)
            current_datetime = datetime.datetime.now()
            formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H-%M-%SZ")
            if distancia != 0:
                print(f"{formatted_datetime} - Html main page content change detected.")
                sendEmail(subject, body, sender, recipients, password)
                main = main_string
                writeFile()
            else:
                print(f"{formatted_datetime} - Nothing new under the sun")
            time.sleep(interval)
    except requests.exceptions.RequestException as ex:
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime("%Y-%m-%dT%H-%M-%SZ")
        file_name = f"errorlog/error.txt"
        logs_dir = os.path.dirname(file_name)
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        with open(file_name, 'a') as file:
            file.write(f'{formatted_datetime} - Erro na solicitação HTTP: {str(ex)}\n')
        print(f'{formatted_datetime} - Erro na solicitação HTTP: {str(ex)}\n')

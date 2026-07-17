from dotenv import load_dotenv
import os
import json
import requests
from sanepar import consultar_cep, montar_mensagem
load_dotenv()


TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CEP = os.getenv("CEP")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado no .env")

if not CHAT_ID:
    raise ValueError("CHAT_ID não encontrado no .env")

STATUS_FILE = "ultimo_status.json"

def log(msg):
    print(msg)


def telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=30
        )

        log(f"Status Telegram: {response.status_code}")
        log(f"Resposta Telegram: {response.text}")

    except Exception as e:
        log(f"Erro Telegram: {e}")


def carregar_status():
    if not os.path.exists(STATUS_FILE):
        return ""

    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return f.read()


def salvar_status(msg):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(msg)

if __name__ == "__main__":

    CEP = os.getenv("CEP")

    log("Consultando Sanepar")

    registros = consultar_cep(CEP)

    mensagem = montar_mensagem(registros)

    if mensagem.strip() != carregar_status().strip():
        telegram(mensagem)
        salvar_status(mensagem)
        log("Mensagem alterada. Notificação enviada.")
    else:
        log("Mensagem não alterou. Nada enviado.")

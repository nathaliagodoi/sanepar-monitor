from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
from sanepar import consultar_cep, montar_mensagem
load_dotenv()


TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado no .env")

if not CHAT_ID:
    raise ValueError("CHAT_ID não encontrado no .env")

STATUS_FILE = "ultimo_status.json"
ALERTA_FILE = "ultimo_alerta_diario.json"


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
        return []

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def salvar_status(registros):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def status_mudou(registros):
    return carregar_status() != registros


def carregar_alerta_diario():
    if not os.path.exists(ALERTA_FILE):
        return None

    try:
        with open(ALERTA_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("data")
    except Exception:
        return None


def salvar_alerta_diario():
    with open(ALERTA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"data": datetime.now().strftime("%Y-%m-%d")},
            f,
            ensure_ascii=False,
            indent=2
        )


def pode_enviar_alerta_diario():
    hoje = datetime.now().strftime("%Y-%m-%d")
    return carregar_alerta_diario() != hoje

if __name__ == "__main__":

    CEP = os.getenv("CEP")

    log("Consultando Sanepar")

    def consultar():
        return consultar_cep(CEP)
    registros = consultar()

    # =====================================
    # SEM OCORRÊNCIAS
    # =====================================

    if not registros:

        log("Nenhuma ocorrência encontrada")

        if status_mudou(registros):

            telegram(
                "✅ O abastecimento foi normalizado. Boa tomar banho 🚿🎉"
            )

            salvar_status(registros)

        elif pode_enviar_alerta_diario():

            telegram(
                "✅ Nenhuma parada programada encontrada para a sua casa. O banho tá garantido 🚿🎉"
            )

            salvar_alerta_diario()
            salvar_status(registros)

        else:

            log("Alerta diário já enviado hoje")

            salvar_status(registros)

        exit()

    # =====================================
    # EXISTEM OCORRÊNCIAS
    # =====================================

    if not status_mudou(registros):

        log("Nenhuma mudança detectada")
        exit()

    mensagem = montar_mensagem(registros)

    telegram(mensagem)

    salvar_status(registros)

    log("Mudança detectada e enviada")
from playwright.sync_api import sync_playwright
from datetime import datetime
import requests
import os
import json

# ======================================================
# CONFIGURAÇÕES
# ======================================================

CEP = "82820210"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

URL = "https://portal.sanepar.com.br/paradasprogramadas/"

STATUS_FILE = "ultimo_status.json"

LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/monitor.log"

os.makedirs(LOG_DIR, exist_ok=True)

# ======================================================
# LOG
# ======================================================

def log(msg):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha = f"[{agora}] {msg}"

    print(linha)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

# ======================================================
# TELEGRAM
# ======================================================

def telegram(msg):

    try:

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=30
        )

    except Exception as e:
        log(f"Erro Telegram: {e}")

# ======================================================
# STATUS
# ======================================================

def carregar_status():

    if not os.path.exists(STATUS_FILE):
        return []

    try:

        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return []

def salvar_status(registros):

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            registros,
            f,
            ensure_ascii=False,
            indent=2
        )

def status_mudou(registros_atuais):

    status_anterior = carregar_status()

    return status_anterior != registros_atuais

# ======================================================
# EXTRAIR TABELA
# ======================================================

def extrair_tabela(page):

    log("Aguardando painel carregar")

    try:

        # espera tabela aparecer
        page.wait_for_selector(
            "calcite-flow-item table tbody",
            timeout=20000
        )

    except Exception as e:

        log(f"Tabela não apareceu: {e}")

        return []

    tabela = page.locator(
        "calcite-flow-item table"
    )

    if tabela.count() == 0:

        log("Tabela não encontrada")

        return []

    cells = tabela.locator("tbody td")

    total = cells.count()

    log(f"Total de células encontradas: {total}")

    if total == 0:

        log("Tabela vazia")

        return []

    valores = []

    for i in range(total):

        texto = cells.nth(i).inner_text().strip()

        if texto:
            valores.append(texto)

    log(f"Valores encontrados: {valores}")

    chunk_size = 3

    linhas = [
        valores[i:i + chunk_size]
        for i in range(0, len(valores), chunk_size)
    ]

    resultado = []

    for linha in linhas:

        if len(linha) < 3:
            continue

        resultado.append({
            "inicio": linha[0],
            "fim": linha[1],
            "descricao": linha[2]
        })

    log(f"{len(resultado)} registros extraídos")

    return resultado

# ======================================================
# CONSULTA
# ======================================================

def consultar():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        try:

            log("Abrindo portal")

            page.goto(URL)

            page.wait_for_load_state("networkidle")
            
            page.wait_for_timeout(4000)

            log("Preenchendo CEP")

            campo = page.get_by_role(
                "textbox",
                name="Rua, número, cidade"
            )
            
            campo.wait_for(timeout=30000)
            
            campo.click()
            
            campo.fill(CEP)
            
            botao = page.get_by_role(
                "button",
                name="Pesquisar"
            )
            
            botao.wait_for(timeout=30000)
            
            page.wait_for_timeout(3000)
            
            botao.click(force=True)

            log("Aguardando resultados")

            page.wait_for_selector(
                "div.record-container",
                timeout=40000
            )

            cards = page.locator("div.record-container")

            log(f"Cards encontrados: {cards.count()}")

            todos_registros = []

            for i in range(cards.count()):

                try:

                    log(f"Abrindo ocorrência {i}")

                    cards.nth(i).click()

                    page.wait_for_timeout(8000)

                    tabela = extrair_tabela(page)

                    todos_registros.extend(tabela)

                except Exception as e:

                    log(f"Erro no card {i}: {e}")

            return todos_registros

        except Exception as e:

            log(f"Erro geral: {e}")

            return []

        finally:

            browser.close()

# ======================================================
# ENVIO TELEGRAM FORMATADO
# ======================================================

def enviar_registros(registros):

    mensagem = "🚨 <b>PARADAS PROGRAMADAS - SANEPAR</b>\n\n"

    for r in registros:

        mensagem += (
            f"📅 <b>Início:</b> {r['inicio']}\n"
            f"📅 <b>Fim:</b> {r['fim']}\n"
            f"🛠 <b>Descrição:</b> {r['descricao']}\n"
            f"-----------------------------\n"
        )

    telegram(mensagem)

# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":

    log("Iniciando consulta")

    registros = consultar()

    # ==================================================
    # NÃO ENVIA SE NÃO EXISTIR REGISTRO
    # ==================================================

    if not registros:

        log("Nenhum registro encontrado")

        exit()

    # ==================================================
    # NÃO ENVIA SE FOR IGUAL AO ÚLTIMO STATUS
    # ==================================================

    if not status_mudou(registros):

        log("Nenhuma mudança detectada")

        exit()

    # ==================================================
    # ENVIA SOMENTE SE MUDOU
    # ==================================================

    log("Mudança detectada")

    enviar_registros(registros)

    salvar_status(registros)

    log("Novo status salvo")

    log("Finalizado")

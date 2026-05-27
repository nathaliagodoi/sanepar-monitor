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

        log("Mensagem enviada ao Telegram")

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

    log("Status salvo")

def status_mudou(registros_atuais):

    status_anterior = carregar_status()

    return status_anterior != registros_atuais

# ======================================================
# LOCALIZAR INPUT
# ======================================================

def localizar_input(page):

    try:

        xpath = "/html/body/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div[2]/div/div[1]/div/span/input"

        campo = page.locator(f"xpath={xpath}")

        campo.wait_for(
            state="visible",
            timeout=30000
        )

        log("Input localizado via XPath")

        return campo

    except Exception as e:

        log(f"Erro ao localizar input: {e}")

        return None

# ======================================================
# EXTRAIR TABELA
# ======================================================

def extrair_tabela(page):

    try:

        log("Aguardando tabela")

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

    log(f"Total de células: {total}")

    if total == 0:
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

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        try:

            log("Abrindo portal")

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(8000)

            # ==================================================
            # INPUT CEP
            # ==================================================

            campo = localizar_input(page)

            if campo is None:

                log("Campo CEP não encontrado")

                return []

            log("Preenchendo CEP")

            campo.click()

            campo.fill(CEP)

            page.wait_for_timeout(2000)

            # ==================================================
            # BOTÃO PESQUISAR
            # ==================================================

            try:

                botao = page.get_by_role(
                    "button",
                    name="Pesquisar"
                )

                botao.click()

            except Exception as e:

                log(f"Erro botão pesquisar: {e}")

                return []

            # ==================================================
            # AGUARDA RESULTADOS
            # ==================================================

            log("Aguardando resultados")

            page.wait_for_timeout(8000)

            cards = page.locator(
                "div.record-container"
            )

            total_cards = cards.count()

            log(f"Cards encontrados: {total_cards}")

            if total_cards == 0:

                log("Nenhuma ocorrência encontrada")

                return []

            todos_registros = []

            # ==================================================
            # ABRE CADA CARD
            # ==================================================

            for i in range(total_cards):

                try:

                    log(f"Abrindo ocorrência {i + 1}")

                    card = cards.nth(i)

                    card.scroll_into_view_if_needed()

                    card.click(force=True)

                    page.wait_for_timeout(3000)

                    tabela = extrair_tabela(page)

                    todos_registros.extend(tabela)

                except Exception as e:

                    log(f"Erro no card {i}: {e}")

            # ==================================================
            # REMOVE DUPLICADOS
            # ==================================================

            resultado_unico = [
                dict(t)
                for t in {
                    tuple(d.items())
                    for d in todos_registros
                }
            ]

            return resultado_unico

        except Exception as e:

            log(f"Erro geral durante scraping: {e}")

            return []

        finally:

            context.close()

            browser.close()

# ======================================================
# ENVIO TELEGRAM
# ======================================================

def enviar_registros(registros):

    mensagem = "🚨 <b>PARADAS PROGRAMADAS - SANEPAR</b>\n\n"

    for r in registros:

        mensagem += (
            f"📅 <b>Início:</b> {r['inicio']}\n"
            f"📅 <b>Fim:</b> {r['fim']}\n"
            f"🛠 <b>Descrição:</b> {r['descricao']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

    telegram(mensagem)

# ======================================================
# EXECUÇÃO
# ======================================================

if __name__ == "__main__":

    log("Iniciando consulta")

    registros = consultar()

    # ==================================================
    # SEM REGISTROS
    # ==================================================

    if not registros:

        log("Nenhum registro encontrado")

        exit()

    # ==================================================
    # STATUS IGUAL
    # ==================================================

    if not status_mudou(registros):

        log("Nenhuma mudança detectada")

        exit()

    # ==================================================
    # ENVIA TELEGRAM
    # ==================================================

    log("Mudança detectada")

    enviar_registros(registros)

    # ==================================================
    # SALVA STATUS
    # ==================================================

    salvar_status(registros)

    log("Finalizado")

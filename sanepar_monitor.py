from playwright.sync_api import sync_playwright
from datetime import datetime
import requests
import os
import json

# ======================================================
# CONFIGURAÇÕES
# ======================================================

CEP = "82820210"

# Busca dos Secrets do GitHub Actions. Se não encontrar (rodando local), usa as strings abaixo.
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

URL = "https://portal.sanepar.com.br/paradasprogramadas/"

STATUS_FILE = "ultimo_status.json"
ALERTA_DIARIO_FILE = "ultimo_alerta_diario.json"

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
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=30
        )
        log(f"Status Telegram: {response.status_code}")
        log(f"Resposta Telegram: {response.text}")
    except Exception as e:
        log(f"Erro Telegram: {e}")

# ======================================================
# STATUS (MUDANÇAS)
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
        json.dump(registros, f, ensure_ascii=False, indent=2)
    log("Status salvo")

def status_mudou(registros_atuais):
    status_anterior = carregar_status()
    return status_anterior != registros_atuais

# ======================================================
# ALERTA DIÁRIO
# ======================================================

def carregar_alerta_diario():
    if not os.path.exists(ALERTA_DIARIO_FILE):
        return None
    try:
        with open(ALERTA_DIARIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("data")
    except:
        return None

def salvar_alerta_diario():
    with open(ALERTA_DIARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"data": datetime.now().strftime("%Y-%m-%d")},
            f
        )

def pode_enviar_alerta_diario():
    ultima_data = carregar_alerta_diario()
    hoje = datetime.now().strftime("%Y-%m-%d")
    return ultima_data != hoje

# ======================================================
# LOCALIZAR INPUT
# ======================================================

def localizar_input(page):
    try:
        xpath = "/html/body/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div[2]/div/div[1]/div/span/input"
        campo = page.locator(f"xpath={xpath}")
        campo.wait_for(state="visible", timeout=30000)
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
        page.wait_for_selector("calcite-flow-item table tbody", timeout=20000)
    except Exception as e:
        log(f"Tabela não apareceu: {e}")
        return []

    tabela = page.locator("calcite-flow-item table")
    if tabela.count() == 0:
        return []

    cells = tabela.locator("tbody td")
    total = cells.count()
    if total == 0:
        return []

    valores = []
    for i in range(total):
        texto = cells.nth(i).inner_text().strip()
        if texto:
            valores.append(texto)

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
    return resultado

# ======================================================
# CONSULTA
# ======================================================

def consultar():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)

            campo = localizar_input(page)
            if campo is None:
                return []

            campo.click()
            campo.fill(CEP)
            page.wait_for_timeout(2000)

            botao = page.get_by_role("button", name="Pesquisar")
            botao.click()
            page.wait_for_timeout(8000)

            cards = page.locator("div.record-container")
            total_cards = cards.count()
            if total_cards == 0:
                return []

            todos_registros = []
            for i in range(total_cards):
                try:
                    card = cards.nth(i)
                    card.scroll_into_view_if_needed()
                    card.click(force=True)
                    page.wait_for_timeout(3000)

                    tabela = extrair_tabela(page)
                    todos_registros.extend(tabela)
                except Exception as e:
                    log(f"Erro no card {i}: {e}")

            resultado_unico = [
                dict(t)
                for t in {
                    tuple(d.items())
                    for d in todos_registros
                }
            ]
            return resultado_unico

        except Exception as e:
            log(f"Erro geral: {e}")
            return []
        finally:
            context.close()
            browser.close()

# ======================================================
# TELEGRAM (ENVIO EM MASSA)
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
    # CASO 1: SEM REGISTROS (TUDO NORMALIZADO)
    # ==================================================
    if not registros:
        log("Nenhum registro encontrado")

        # Se antes tínhamos paradas salvas e agora limpou, avisa a normalização
        if status_mudou(registros):
            log("Aviso de normalização: O status mudou para sem paradas.")
            telegram("✅ <b>O abastecimento foi normalizado ou nenhuma parada está agendada.</b>")
            salvar_status(registros)  # Salva [] para atualizar o arquivo no Git

        # Se continua sem paradas e ainda não enviou o relatório de "tudo limpo" do dia
        elif pode_enviar_alerta_diario():
            telegram("✅ <b>Nenhuma parada programada encontrada para o CEP consultado.</b>")
            salvar_alerta_diario()
            log("Alerta diário enviado")
            salvar_status(registros)  # Garante o gatilho de atualização do arquivo
            
        else:
            log("Alerta diário já enviado hoje. Atualizando arquivo de checagem para o Actions.")
            salvar_status(registros)  # Força a gravação para manter o Actions ativo no cron

        exit()

    # ==================================================
    # CASO 2: COM REGISTROS MAS SEM MUDANÇAS EM RELAÇÃO AO ANTERIOR
    # ==================================================
    if not status_mudou(registros):
        log("Nenhuma mudança detectada nos registros existentes.")
        exit()

    # ==================================================
    # CASO 3: MUDANÇA DETECTADA (NOVAS PARADAS PROGRAMADAS)
    # ==================================================
    log("Mudança detectada no status da Sanepar")
    enviar_registros(registros)
    salvar_status(registros)

    log("Finalizado")

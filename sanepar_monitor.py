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
        # Configuração de contexto robusta para evitar bloqueios no CI
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="pt-BR"
        )
        page = context.new_page()

        try:
            log("Abrindo portal")
            page.goto(URL, wait_until="domcontentloaded")
            
            # Dá um tempo para que os scripts do mapa/portal carreguem completamente
            page.wait_for_load_state("networkidle")
            
            log("Preenchendo CEP")
            campo = page.get_by_role("textbox", name="Rua, número, cidade")
            campo.wait_for(status="visible", timeout=20000)
            
            # Limpa o campo, clica e preenche o CEP
            campo.click()
            campo.fill("")
            campo.fill(CEP)
            
            # Força o disparo dos eventos de input que o framework do site possa estar ouvindo
            campo.dispatch_event("input")
            campo.dispatch_event("change")
            
            log("Clicando no botão Pesquisar")
            botao = page.get_by_role("button", name="Pesquisar")
            botao.wait_for(status="visible", timeout=10000)
            
            # Usar force=True garante que o Playwright clique mesmo se houver uma 
            # sobreposição invisível ou se o elemento parecer "não clicável" momentaneamente no headless
            botao.click(force=True)

            log("Aguardando container de resultados")
            # O Actions é mais lento; aumentamos o timeout para esperar os cards surgirem
            try:
                page.wait_for_selector("div.record-container", timeout=30000)
            except Exception as e:
                log("Nenhum card de registro apareceu na tela. Verifique se o CEP foi aceito.")
                return []

            cards = page.locator("div.record-container")
            total_cards = cards.count()
            log(f"Cards encontrados: {total_cards}")

            todos_registros = []

            for i in range(total_cards):
                try:
                    log(f"Abrindo ocorrência {i + 1} de {total_cards}")
                    
                    # Garante que o card está visível na tela do headless antes de clicar
                    cards.nth(i).scroll_into_view_if_needed()
                    cards.nth(i).click(force=True)

                    tabela = extrair_tabela(page)
                    todos_registros.extend(tabela)

                    # Tenta fechar o card expandido para não atrapalhar o clique no próximo
                    botao_voltar = page.locator("calcite-action[text='Voltar'], .back-button").first
                    if botao_voltar.is_visible():
                        botao_voltar.click(force=True)
                        page.wait_for_timeout(1000)

                except Exception as e:
                    log(f"Erro no card {i}: {e}")

            # Remove duplicados exatos se houver sobreposição de dados
            resultado_unico = [dict(t) for t in {tuple(d.items()) for d in todos_registros}]
            return resultado_unico

        except Exception as e:
            log(f"Erro geral durante a raspagem: {e}")
            return []

        finally:
            context.close()
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

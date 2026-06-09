# 💧 Sanepar Monitor Bot

Bot automatizado que monitora possíveis interrupções no fornecimento de água da Sanepar com base em um CEP e envia alertas via Telegram.

O projeto roda automaticamente via GitHub Actions.

---

## 🚀 Objetivo

Automatizar a verificação de falta de água ou manutenção programada na sua região e receber alertas no Telegram.

---

## 🧰 Pré-requisitos

Antes de começar, você precisa:

- Conta no GitHub
- Python 3 (apenas para execução local opcional)
- Um bot do Telegram
- Seu CEP

---

## 🤖 Criando o bot no Telegram

1. Abra o Telegram e procure pelo [@BotFather](https://t.me/BotFather).
2. Envie o comando: `/newbot`.
3. Escolha um **nome** e um **username** (usuário) para o seu bot.
4. Copie o **TOKEN** gerado.

---

## 💬 Como obter o CHAT_ID

1. Envie uma mensagem para o seu bot no Telegram
2. Abra no navegador: https://api.telegram.org/botSEU_TOKEN/getUpdates

3. Procure por algo como:

{
  "chat": {
    "id": 123456789
  }
}

👉 O número que aparece no campo "id" (ex: 123456789) é o seu CHAT_ID.

---

## ⚙️ Configuração no GitHub (IMPORTANTE)

Depois de fazer fork ou clonar o projeto:

1. Vá até:
Settings → Secrets and variables → Actions → New repository secret

2. Adicione os seguintes secrets:

| Nome             | Descrição                           |
| ---------------- | ----------------------------------- |
| `CEP`            | CEP da região a ser monitorada      |
| `TELEGRAM_TOKEN` | Token do bot do Telegram            |
| `CHAT_ID`        | ID do chat para envio das mensagens |

---

## 🧪 Exemplo de configuração

CEP=80000000  
TELEGRAM_TOKEN=123456:ABCDEF...  
CHAT_ID=123456789  

---

## ⏰ Execução automática (GitHub Actions)

O bot executa automaticamente nos seguintes horários:

06:00
12:00
17:00

---

## ▶️ Execução manual

Caso queira testar manualmente:

GitHub → Actions → Sanepar Monitor → Run workflow

---

## Como personalizar (Somente com ceps atendidos pela Sanepar)
Para usar em outra região, basta alterar o secret: `CEP`

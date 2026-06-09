from sanepar import consultar_cep, montar_mensagem
import os

CEP = os.getenv("CEP")

if not CEP:
    raise ValueError("CEP não encontrado nas variáveis de ambiente")

resultado = consultar_cep(CEP)

mensagem = montar_mensagem(resultado)

print(mensagem)

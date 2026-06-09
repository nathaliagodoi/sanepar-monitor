from sanepar import consultar_cep, montar_mensagem

resultado = consultar_cep("82820210")

mensagem = montar_mensagem(resultado)

print(mensagem)
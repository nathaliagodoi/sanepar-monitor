import requests

SITUACOES = {
    1: "Manutenção Prevista",
    2: "Manutenção em Execução",
    3: "Abastecimento em Normalização",
    4: "Abastecimento Normalizado"
}


def consultar_cep(cep):

    # -------------------------
    # 1 - Descobrir coordenadas
    # -------------------------

    geo_url = (
        "https://geocode.arcgis.com/arcgis/rest/services/"
        "World/GeocodeServer/findAddressCandidates"
    )

    geo_params = {
        "SingleLine": cep,
        "countryCode": "BRA",
        "maxSuggestions": 1,
        "f": "json"
    }

    geo = requests.get(
        geo_url,
        params=geo_params,
        timeout=30
    ).json()

    candidatos = geo.get("candidates", [])

    if not candidatos:
        return []

    x = candidatos[0]["location"]["x"]
    y = candidatos[0]["location"]["y"]

    # -------------------------
    # 2 - Consultar a Sanepar
    # -------------------------

    query_url = (
        "https://server.sanepar.com.br/server/rest/services/"
        "Agua/manobras_site/MapServer/0/query"
    )

    params = {
        "f": "json",
        "returnGeometry": "false",
        "outFields": "*",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": 4326,
        "geometry": f'{{"x":{x},"y":{y}}}'
    }

    resposta = requests.get(
        query_url,
        params=params,
        timeout=30
    ).json()

    resultado = []

    for item in resposta.get("features", []):

        dados = item["attributes"]

        resultado.append({
            "protocolo": dados["man_protocolo"],
            "inicio": dados["man_previsao_inicio"],
            "fim": dados["man_previsao_fim"],
            "normalizacao": dados["man_normalizacao_previsao"],
            "situacao": SITUACOES.get(
                dados["man_situacao"],
                str(dados["man_situacao"])
            ),
            "motivo": dados["man_motivo"]
        })

    return resultado

def montar_mensagem(registros):

    if not registros:
        return "✅ Nenhuma parada programada encontrada. O banho tá garantido 🎉🎉🎉"

    mensagem = "🚨 SANEPAR - OCORRÊNCIAS ENCONTRADAS\n\n"

    for item in registros:

        mensagem += (
            f"📍 Situação: {item['situacao']}\n"
            f"🛠 Motivo: {item['motivo']}\n"
            f"🕒 Início: {item['inicio']}\n"
            f"🕒 Fim: {item['fim']}\n"
            f"💧 Normalização: {item['normalizacao']}\n"
            f"\n━━━━━━━━━━━━━━━━━━\n\n"
        )

    return mensagem
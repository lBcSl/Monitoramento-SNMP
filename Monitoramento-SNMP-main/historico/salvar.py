import json
from datetime import datetime


def salvar_historico(dados):

    try:

        with open(
            "historico/historico.json",
            "r",
            encoding="utf-8"
        ) as arquivo:

            historico = json.load(arquivo)

    except:

        historico = []

    dados["timestamp"] = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    historico.append(dados)

    # Limita para não crescer infinitamente
    if len(historico) > 1000:

        historico = historico[-1000:]

    with open(
        "historico/historico.json",
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            historico,
            arquivo,
            indent=4,
            ensure_ascii=False
        )
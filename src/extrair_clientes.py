"""Extrai os clientes do GitHub Pages e os envia ao webhook do n8n."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests
from bs4 import BeautifulSoup


DEFAULT_PAGE_URL = (
    "https://leandrinhoaraujo.github.io/"
    "dio-lab-assistente-investimentos-rpa-n8n/"
)


def extrair_clientes(page_url: str = DEFAULT_PAGE_URL) -> list[dict[str, str]]:
    """Baixa a pagina e devolve os clientes presentes na tabela #clientes."""
    resposta = requests.get(page_url, timeout=30)
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")
    linhas = soup.select("#clientes tbody tr")
    if not linhas:
        raise ValueError("A tabela #clientes nao foi encontrada ou esta vazia.")

    clientes: list[dict[str, str]] = []
    for numero, linha in enumerate(linhas, start=1):
        colunas = linha.find_all("td")
        if len(colunas) != 4:
            raise ValueError(
                f"Linha {numero} invalida: eram esperadas 4 colunas, "
                f"mas foram encontradas {len(colunas)}."
            )
        clientes.append(
            {
                "nome": colunas[0].get_text(strip=True),
                "email": colunas[1].get_text(strip=True),
                "saldo": colunas[2].get_text(strip=True),
                "perfil": colunas[3].get_text(strip=True),
            }
        )
    return clientes


def enviar_ao_n8n(
    clientes: list[dict[str, str]], webhook_url: str
) -> dict[str, Any]:
    """Envia os clientes ao n8n e devolve a resposta JSON do workflow."""
    resposta = requests.post(
        webhook_url,
        json={"clientes": clientes},
        timeout=60,
    )
    resposta.raise_for_status()
    try:
        return resposta.json()
    except requests.JSONDecodeError as erro:
        raise ValueError("O webhook respondeu, mas nao retornou JSON valido.") from erro


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--page-url",
        default=os.getenv("CLIENTES_URL", DEFAULT_PAGE_URL),
        help="URL da pagina de clientes.",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("N8N_WEBHOOK_URL"),
        help="URL do webhook (ou defina N8N_WEBHOOK_URL).",
    )
    parser.add_argument(
        "--somente-extrair",
        action="store_true",
        help="Extrai e exibe os clientes sem chamar o n8n.",
    )
    args = parser.parse_args()

    clientes = extrair_clientes(args.page_url)
    print(f"Clientes encontrados: {len(clientes)}")
    for cliente in clientes:
        print(cliente)

    if args.somente_extrair:
        return 0
    if not args.webhook_url:
        parser.error(
            "informe --webhook-url ou defina a variavel N8N_WEBHOOK_URL"
        )

    resultado = enviar_ao_n8n(clientes, args.webhook_url)
    print("\nResposta do n8n:")
    for recomendacao in resultado.get("recomendacoes", []):
        print(recomendacao.get("mensagem", recomendacao))
    return 0


if __name__ == "__main__":
    sys.exit(main())

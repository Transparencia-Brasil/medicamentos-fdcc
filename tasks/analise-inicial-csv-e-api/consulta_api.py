"""Consulta manual de releases OCDS da API de Dados Abertos do Compras.gov.br."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")
BASE_URL = os.getenv("COMPRAS_API_BASE_URL", "https://dadosabertos.compras.gov.br").rstrip("/")
TIMEOUT = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
ROTA_OCDS = "/modulo-ocds/1_releases"


def parametros_ocds(
    buyer_id: str,
    release_start_date: str,
    release_end_date: str,
    page: int = 1,
    offset: int = 10,
) -> dict[str, str | int]:
    """Valida os filtros e preserva os nomes de parâmetros usados pela API."""
    if not (buyer_id.isdigit() and len(buyer_id) == 14):
        raise ValueError("buyerID deve ser um CNPJ com 14 dígitos, sem pontuação")
    try:
        inicio = date.fromisoformat(release_start_date)
        fim = date.fromisoformat(release_end_date)
    except ValueError as exc:
        raise ValueError("Datas devem estar no formato AAAA-MM-DD") from exc
    if inicio.isoformat() != release_start_date or fim.isoformat() != release_end_date:
        raise ValueError("Datas devem estar no formato AAAA-MM-DD")
    if inicio > fim:
        raise ValueError("releaseStartDate deve ser anterior ou igual a releaseEndDate")
    if page < 1 or not 1 <= offset <= 500:
        raise ValueError("page deve ser positivo e offSet deve estar entre 1 e 500")
    return {
        "page": page,
        "offSet": offset,
        "buyerID": buyer_id,
        "releaseStartDate": release_start_date,
        "releaseEndDate": release_end_date,
    }


def url_ocds(**filtros: str | int) -> str:
    """Mostra a URL exata antes de fazer a chamada HTTP."""
    params = parametros_ocds(**filtros)
    return requests.Request("GET", BASE_URL + ROTA_OCDS, params=params).prepare().url


def consultar_ocds(**filtros: str | int) -> dict:
    """Busca uma página e devolve o JSON bruto, sem descartar campos."""
    params = parametros_ocds(**filtros)
    resposta = requests.get(BASE_URL + ROTA_OCDS, params=params, timeout=TIMEOUT)
    resposta.raise_for_status()
    dados = resposta.json()
    if not isinstance(dados, dict):
        raise ValueError("A API retornou JSON em formato inesperado; esperado um objeto")
    return dados

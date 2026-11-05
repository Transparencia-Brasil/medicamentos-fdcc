"""Seleciona os processos de contratação com comprador no DF.

Lê um arquivo OCDS em JSON Lines (uma release compilada por linha) e grava, em
outro arquivo, só as linhas cujo comprador tem `address.region == "DF"`. O
comprador é a parte de `parties[]` com o mesmo `id` de `buyer.id`. As linhas são
copiadas exatamente como vieram, sem serem reescritas.

A UF é a da unidade que fez a compra: um órgão federal com unidades em vários
estados só entra pelos processos das unidades do DF.

Uso:
    python filtra_df.py ENTRADA.jsonl SAIDA.jsonl

Códigos de saída: 0 arquivo gravado; 1 linha que não é JSON válido ou erro de
leitura/escrita; 2 argumentos inválidos, entrada inexistente ou saída já
existente.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

UF = "DF"


@dataclass
class Resumo:
    total: int = 0
    df: int = 0
    sem_uf: int = 0


def uf_do_comprador(release):
    """UF do comprador da release, ou None se ela não informar.

    Uma UF vazia ou que não seja texto conta como não informada. Levanta
    AttributeError se a release, o comprador ou uma parte não forem objetos.
    """
    id_comprador = (release.get("buyer") or {}).get("id")
    if id_comprador is None:
        return None
    for parte in release.get("parties") or []:
        if parte.get("id") == id_comprador:
            uf = (parte.get("address") or {}).get("region")
            return uf if isinstance(uf, str) and uf else None
    return None


def filtra(entrada, saida):
    """Grava em `saida` as linhas de `entrada` com comprador no DF.

    Passa por `{saida}.part`, que só ganha o nome final no fim. Uma linha
    inválida levanta ValueError com o número da linha, e nada fica gravado.
    """
    saida = Path(saida)
    part = saida.with_name(saida.name + ".part")
    resumo = Resumo()
    try:
        with open(entrada, "rb") as origem, open(part, "wb") as destino:
            for numero, linha in enumerate(origem, start=1):
                if not linha.strip():
                    continue
                try:
                    release = json.loads(linha)
                except ValueError as erro:
                    raise ValueError(f"linha {numero} não é JSON válido: {erro}") from erro
                try:
                    uf = uf_do_comprador(release)
                except AttributeError as erro:
                    raise ValueError(
                        f"linha {numero} não tem a estrutura de uma release OCDS: {erro}"
                    ) from erro
                resumo.total += 1
                if uf is None:
                    resumo.sem_uf += 1
                elif uf == UF:
                    resumo.df += 1
                    destino.write(linha)
        part.replace(saida)
    finally:
        part.unlink(missing_ok=True)
    return resumo


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else argv
    if len(argumentos) != 2:
        print("Uso: python filtra_df.py ENTRADA.jsonl SAIDA.jsonl", file=sys.stderr)
        return 2
    entrada, saida = map(Path, argumentos)
    if not entrada.is_file():
        print(f"Erro: entrada não encontrada: {entrada}", file=sys.stderr)
        return 2
    if saida.exists():
        print(f"Erro: a saída já existe e não será sobrescrita: {saida}", file=sys.stderr)
        return 2
    try:
        resumo = filtra(entrada, saida)
    except (ValueError, OSError) as erro:
        print(f"Erro ao filtrar {entrada}: {erro}", file=sys.stderr)
        return 1
    print(
        f"Filtro DF: {resumo.total} processos, {resumo.df} com comprador no DF, "
        f"{resumo.sem_uf} sem UF do comprador. Gravado em {argumentos[1]}"
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

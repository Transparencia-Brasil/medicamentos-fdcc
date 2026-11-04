"""Converte um arquivo JSON Lines (um objeto por linha) numa lista JSON formatada.

O resultado é o mesmo de `json.dumps(lista, ensure_ascii=False, indent=2)`: uma
lista com recuo de 2 espaços e acentos legíveis, que abre num editor e é lida por
qualquer leitor de JSON. A conversão é feita linha a linha, sem carregar o
arquivo inteiro na memória.

Uso:
    python jsonl_para_json.py ENTRADA.jsonl SAIDA.json

Códigos de saída: 0 arquivo gravado; 1 linha que não é JSON válido ou erro de
leitura/escrita; 2 argumentos inválidos, entrada inexistente ou saída já
existente.
"""

import json
import sys
from pathlib import Path


def converte(entrada, saida):
    """Grava em `saida` a lista JSON com os objetos de `entrada` e devolve o total.

    Passa por `{saida}.part`, que só ganha o nome final no fim. Uma linha
    inválida (JSON inválido, texto que não é UTF-8 ou um surrogate solto)
    levanta ValueError com o número da linha, e nada fica gravado. Não confere
    se `saida` já existe: isso fica com quem chama, como o `main`.
    """
    saida = Path(saida)
    part = saida.with_name(saida.name + ".part")
    total = 0
    try:
        with open(entrada, "rb") as origem, open(part, "wb") as destino:
            for numero, linha in enumerate(origem, start=1):
                if not linha.strip():
                    continue
                try:
                    objeto = json.loads(linha)
                    # O json.dumps só emite \n estrutural (quebras dentro de
                    # textos saem como \n escapado), então recuar a cada \n não
                    # altera nenhum valor. Não use str.splitlines/textwrap: eles
                    # também quebram em U+2028, U+2029 e U+0085, que o
                    # json.dumps grava sem escape.
                    texto = "  " + json.dumps(objeto, ensure_ascii=False, indent=2).replace("\n", "\n  ")
                    dados = (("[\n" if total == 0 else ",\n") + texto).encode("utf-8")
                except ValueError as erro:
                    raise ValueError(f"linha {numero} não é JSON válido em UTF-8: {erro}") from erro
                destino.write(dados)
                total += 1
            destino.write(b"\n]\n" if total else b"[]\n")
        part.replace(saida)
    finally:
        part.unlink(missing_ok=True)
    return total


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else argv
    if len(argumentos) != 2:
        print("Uso: python jsonl_para_json.py ENTRADA.jsonl SAIDA.json", file=sys.stderr)
        return 2
    entrada, saida = map(Path, argumentos)
    if not entrada.is_file():
        print(f"Erro: entrada não encontrada: {entrada}", file=sys.stderr)
        return 2
    if saida.exists():
        print(f"Erro: a saída já existe e não será sobrescrita: {saida}", file=sys.stderr)
        return 2
    try:
        total = converte(entrada, saida)
    except (ValueError, OSError) as erro:
        print(f"Erro ao converter {entrada}: {erro}", file=sys.stderr)
        return 1
    print(f"JSON: {total} processos em lista formatada. Gravado em {argumentos[1]}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())

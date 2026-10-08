import gzip
import json
from pathlib import Path

entrada = Path("tasks/analise-inicial-csv-e-api/docs/inputs/brazil_compras_2025.jsonl.gz")
saida = Path("tasks/analise-inicial-csv-e-api/docs/output/mock_compras.json")

limite = 150
campo_id = "id"  # Ajuste para o nome exato do campo.

registros = []
ids_selecionados = set()

with gzip.open(entrada, "rt", encoding="utf-8") as arquivo:
    for numero_linha, linha in enumerate(arquivo, start=1):
        if not linha.strip():
            continue

        registro = json.loads(linha)

        if campo_id not in registro:
            raise KeyError(
                f"Campo '{campo_id}' ausente na linha {numero_linha}. "
                f"Campos disponíveis: {list(registro)}"
            )

        identificador = registro[campo_id]

        if identificador is None:
            raise ValueError(f"ID nulo na linha {numero_linha}.")

        if identificador in ids_selecionados:
            continue

        registros.append(registro)
        ids_selecionados.add(identificador)

        if len(registros) == limite:
            break

saida.parent.mkdir(parents=True, exist_ok=True)
with saida.open("w", encoding="utf-8") as arquivo:
    json.dump(registros, arquivo, ensure_ascii=False, indent=2)

print(f"{len(registros)} IDs salvos em: {saida.resolve()}")

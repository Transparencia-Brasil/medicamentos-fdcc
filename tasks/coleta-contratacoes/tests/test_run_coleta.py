"""Testes do run-coleta-contratacoes.sh, sem acessar a rede.

Copiam o script e o filtro para uma raiz temporária, com um coletor falso (via
COLETOR_CONTRATACOES_DIR) que grava um .gz pequeno, e põem no PATH executáveis
`python3` e `python` falsos para testar a escolha do Python. No Windows, usam o
Bash do Git for Windows; sem Bash, os testes são pulados.

Rodar da raiz do repositório:
    python -m unittest discover -s tasks/coleta-contratacoes/tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]

COLETOR_FALSO = """#!/usr/bin/env bash
# Recebe --ano ANO --saida ARQUIVO e grava o fixture compactado em ARQUIVO.
if [ -n "${FALHA_COLETOR:-}" ]; then echo "falha simulada" >&2; exit "$FALHA_COLETOR"; fi
mkdir -p "$(dirname "$4")"
gzip -c "$(dirname "$0")/../../../fixture.jsonl" > "$4"
"""

PYTHON_AUSENTE = """#!/bin/sh
echo "Python was not found" >&2
exit 49
"""

# Passa na verificação de versão, mas falha ao rodar o filtro com um código
# fora de 0, 1 e 2.
PYTHON_QUE_FALHA_NO_FILTRO = """#!/bin/sh
if [ "$1" = "-c" ]; then exec "{python}" "$@"; fi
exit 49
"""

# Roda o filtro normalmente, mas falha na conversão para JSON.
PYTHON_QUE_FALHA_NA_CONVERSAO = """#!/bin/sh
case "$*" in *jsonl_para_json.py*) exit 49 ;; esac
exec "{python}" "$@"
"""

PYTHON_REAL = """#!/bin/sh
exec "{python}" "$@"
"""


def acha_bash():
    if os.name != "nt":
        return shutil.which("bash")
    # No Windows, o bash do PATH pode ser o do WSL; usa o do Git for Windows.
    git = shutil.which("git")
    if git:
        for pasta in Path(git).resolve().parents:
            candidato = pasta / "bin" / "bash.exe"
            if candidato.is_file():
                return str(candidato)
    return None


BASH = acha_bash()


def release(ocid, uf):
    return {
        "ocid": ocid,
        "buyer": {"id": "BR-CNPJ-1"},
        "parties": [{"id": "BR-CNPJ-1", "roles": ["buyer"], "address": {"region": uf}}],
    }


@unittest.skipUnless(BASH, "Bash não encontrado")
class TestRunColeta(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)

        src = self.raiz / "tasks" / "coleta-contratacoes" / "src"
        src.mkdir(parents=True)
        for nome in ("run-coleta-contratacoes.sh", "filtra_df.py", "jsonl_para_json.py"):
            shutil.copy(TASK / "src" / nome, src / nome)

        coletor = self.raiz / "coletor-falso"
        (coletor / "src" / "ETL" / "coletores").mkdir(parents=True)
        self.escreve(coletor / "src" / "ETL" / "coletores" / "run-coleta-contratacoes.sh", COLETOR_FALSO)
        linhas = [json.dumps(release("ocds-df", "DF")), json.dumps(release("ocds-go", "GO"))]
        self.escreve(coletor / "fixture.jsonl", "\n".join(linhas) + "\n")

        self.bin = self.raiz / "bin"
        self.bin.mkdir()
        self.python = Path(sys.executable).as_posix()
        # python3 ausente (como o atalho da Microsoft Store) vem antes do python real.
        self.escreve(self.bin / "python3", PYTHON_AUSENTE)
        self.escreve(self.bin / "python", PYTHON_REAL.format(python=self.python))

    def escreve(self, caminho, texto):
        caminho.write_bytes(texto.encode("utf-8"))
        caminho.chmod(0o755)

    def roda(self, **ambiente_extra):
        ambiente = os.environ | {
            "COLETOR_CONTRATACOES_DIR": "coletor-falso",
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
        } | ambiente_extra
        return subprocess.run(
            [BASH, "tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh", "--anos", "2026"],
            cwd=self.raiz, env=ambiente, capture_output=True, text=True, encoding="utf-8",
        )

    def arquivos(self, padrao):
        return sorted((self.raiz / "tasks" / "coleta-contratacoes" / "outputs" / "2026").glob(padrao))

    def test_baixa_descompacta_filtra_e_converte_pulando_o_python_que_nao_funciona(self):
        resultado = self.roda()
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
        self.assertEqual(len(self.arquivos("*_2026.jsonl.gz")), 1)
        self.assertEqual(len(self.arquivos("*_2026.jsonl")), 1)
        (df,) = self.arquivos("*_2026_df.jsonl")
        self.assertEqual([json.loads(l)["ocid"] for l in df.read_text().splitlines()], ["ocds-df"])
        self.assertIn("1 com comprador no DF", resultado.stdout)
        (df_json,) = self.arquivos("*_2026_df.json")
        self.assertEqual(df_json.name, df.name.removesuffix(".jsonl") + ".json")
        self.assertEqual([p["ocid"] for p in json.loads(df_json.read_bytes())], ["ocds-df"])

    def test_falha_no_coletor_nao_roda_o_filtro(self):
        resultado = self.roda(FALHA_COLETOR="2")
        self.assertEqual(resultado.returncode, 2)
        self.assertEqual(self.arquivos("*_df.jsonl"), [])
        self.assertEqual(self.arquivos("*_df.json"), [])
        self.assertNotIn("Filtro DF", resultado.stdout)

    def test_codigo_inesperado_do_filtro_vira_1(self):
        self.escreve(self.bin / "python", PYTHON_QUE_FALHA_NO_FILTRO.format(python=self.python))
        resultado = self.roda()
        self.assertEqual(resultado.returncode, 1, resultado.stdout + resultado.stderr)
        self.assertIn("Ano 2026: código 1", resultado.stdout)

    def test_falha_na_conversao_mantem_o_df_jsonl_e_vira_codigo_1(self):
        self.escreve(self.bin / "python", PYTHON_QUE_FALHA_NA_CONVERSAO.format(python=self.python))
        resultado = self.roda()
        self.assertEqual(resultado.returncode, 1, resultado.stdout + resultado.stderr)
        self.assertEqual(len(self.arquivos("*_df.jsonl")), 1)
        self.assertEqual(self.arquivos("*_df.json"), [])


if __name__ == "__main__":
    unittest.main()

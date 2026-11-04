"""Testes do conversor de JSON Lines para lista JSON (jsonl_para_json.py).

Rodar da raiz do repositório:
    python -m unittest discover -s tasks/coleta-contratacoes/tests -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import jsonl_para_json  # noqa: E402

PROCESSOS = [
    {"ocid": "ocds-1", "tender": {"title": "Medicação — açúcar", "items": [{"id": 1}, {"id": 2}]}},
    {"ocid": "ocds-2", "descricao": "linha 1\nlinha 2", "vazio": {}, "lista": []},
    # Separadores Unicode que o str.splitlines trata como fim de linha, mas que
    # o json.dumps grava sem escape: o recuo não pode entrar no texto.
    {"ocid": "ocds-3", "texto": "a b c\u0085d"},
]


def jsonl(*objetos):
    return "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in objetos).encode("utf-8")


class TestConverte(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.entrada = Path(pasta.name) / "contratacoes_2026_df.jsonl"
        self.saida = Path(pasta.name) / "contratacoes_2026_df.json"

    def test_grava_a_lista_formatada_igual_ao_json_dumps(self):
        self.entrada.write_bytes(jsonl(*PROCESSOS))
        total = jsonl_para_json.converte(self.entrada, self.saida)
        esperado = json.dumps(PROCESSOS, ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(self.saida.read_bytes(), esperado.encode("utf-8"))
        self.assertEqual(json.loads(self.saida.read_bytes()), PROCESSOS)
        self.assertEqual(total, 3)

    def test_acentos_ficam_legiveis(self):
        self.entrada.write_bytes(jsonl(PROCESSOS[0]))
        jsonl_para_json.converte(self.entrada, self.saida)
        self.assertIn("Medicação — açúcar", self.saida.read_text(encoding="utf-8"))

    def test_entrada_vazia_vira_lista_vazia(self):
        self.entrada.write_bytes(b"")
        self.assertEqual(jsonl_para_json.converte(self.entrada, self.saida), 0)
        self.assertEqual(json.loads(self.saida.read_bytes()), [])

    def test_linhas_em_branco_sao_ignoradas(self):
        self.entrada.write_bytes(jsonl(PROCESSOS[0]) + b"\n" + jsonl(PROCESSOS[1]))
        jsonl_para_json.converte(self.entrada, self.saida)
        self.assertEqual(json.loads(self.saida.read_bytes()), PROCESSOS[:2])

    def test_texto_que_nao_e_utf8_da_erro_com_o_numero_da_linha(self):
        self.entrada.write_bytes(jsonl(PROCESSOS[0]) + '{"a": "ação"}\n'.encode("latin-1"))
        with self.assertRaises(ValueError) as erro:
            jsonl_para_json.converte(self.entrada, self.saida)
        self.assertIn("linha 2", str(erro.exception))
        self.assertFalse(self.saida.exists())

    def test_surrogate_solto_da_erro_com_o_numero_da_linha(self):
        self.entrada.write_bytes(jsonl(PROCESSOS[0]) + b'{"a": "\\ud800"}\n')
        with self.assertRaises(ValueError) as erro:
            jsonl_para_json.converte(self.entrada, self.saida)
        self.assertIn("linha 2", str(erro.exception))
        self.assertFalse(self.saida.exists())
        self.assertFalse(self.saida.with_name(self.saida.name + ".part").exists())

    def test_linha_invalida_da_erro_e_nao_deixa_saida(self):
        self.entrada.write_bytes(jsonl(PROCESSOS[0]) + b'{"ocid": "cortado\n')
        with self.assertRaises(ValueError) as erro:
            jsonl_para_json.converte(self.entrada, self.saida)
        self.assertIn("linha 2", str(erro.exception))
        self.assertFalse(self.saida.exists())
        self.assertFalse(self.saida.with_name(self.saida.name + ".part").exists())


class TestMain(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.entrada = Path(pasta.name) / "contratacoes_2026_df.jsonl"
        self.saida = Path(pasta.name) / "contratacoes_2026_df.json"
        self.entrada.write_bytes(jsonl(*PROCESSOS))

    def roda(self, *argumentos):
        return subprocess.run(
            [sys.executable, str(SRC / "jsonl_para_json.py"), *map(str, argumentos)],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_sucesso_grava_e_registra_o_total(self):
        resultado = self.roda(self.entrada, self.saida.as_posix())
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("3 processos", resultado.stdout)
        self.assertIn(self.saida.as_posix(), resultado.stdout)
        self.assertEqual(json.loads(self.saida.read_bytes()), PROCESSOS)

    def test_saida_existente_e_recusada_com_codigo_2(self):
        self.saida.write_bytes(b"antigo")
        resultado = self.roda(self.entrada, self.saida)
        self.assertEqual(resultado.returncode, 2)
        self.assertEqual(self.saida.read_bytes(), b"antigo")

    def test_entrada_inexistente_da_codigo_2(self):
        resultado = self.roda(self.entrada.with_name("nao-existe.jsonl"), self.saida)
        self.assertEqual(resultado.returncode, 2)
        self.assertFalse(self.saida.exists())

    def test_numero_errado_de_argumentos_da_codigo_2(self):
        self.assertEqual(self.roda(self.entrada).returncode, 2)

    def test_linha_invalida_da_codigo_1_com_mensagem_e_sem_traceback(self):
        self.entrada.write_bytes(b"nao e json\n")
        resultado = self.roda(self.entrada, self.saida)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("linha 1", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)
        self.assertFalse(self.saida.exists())


if __name__ == "__main__":
    unittest.main()

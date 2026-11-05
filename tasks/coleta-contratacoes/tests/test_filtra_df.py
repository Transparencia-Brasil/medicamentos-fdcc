"""Testes do filtro de compradores do DF (filtra_df.py).

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

import filtra_df  # noqa: E402


def processo(ocid, uf_comprador, outras_partes=(), papeis=("buyer", "procuringEntity")):
    """Monta uma release mínima com o comprador na UF indicada (None = sem UF)."""
    comprador = {"id": "BR-CNPJ-1", "name": "ORGAO", "roles": list(papeis)}
    if uf_comprador is not None:
        comprador["address"] = {"region": uf_comprador, "locality": "CIDADE"}
    return {
        "ocid": ocid,
        "buyer": {"id": "BR-CNPJ-1", "name": "ORGAO"},
        "parties": [*outras_partes, comprador],
    }


def linha(release):
    # Espaçamento e acentos diferentes do json.dumps padrão, para provar que a
    # linha é copiada, não reescrita.
    return json.dumps(release, ensure_ascii=False, separators=(", ", ": ")).encode("utf-8") + b"\n"


def pasta_temporaria(teste):
    pasta = tempfile.TemporaryDirectory()
    teste.addCleanup(pasta.cleanup)
    return Path(pasta.name)


class TestFiltra(unittest.TestCase):
    def setUp(self):
        self.pasta = pasta_temporaria(self)
        self.entrada = self.pasta / "contratacoes_2026.jsonl"
        self.saida = self.pasta / "contratacoes_2026_df.jsonl"

    def grava(self, *linhas):
        self.entrada.write_bytes(b"".join(linhas))

    def assert_falha_na_linha(self, numero):
        with self.assertRaises(ValueError) as erro:
            filtra_df.filtra(self.entrada, self.saida)
        self.assertIn(f"linha {numero}", str(erro.exception))
        self.assertFalse(self.saida.exists())
        self.assertFalse(self.saida.with_name(self.saida.name + ".part").exists())

    def test_mantem_comprador_do_df_e_descarta_outras_ufs(self):
        self.grava(linha(processo("ocds-df", "DF")), linha(processo("ocds-go", "GO")))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        ocids = [json.loads(l)["ocid"] for l in self.saida.read_bytes().splitlines()]
        self.assertEqual(ocids, ["ocds-df"])
        self.assertEqual((resumo.total, resumo.df, resumo.sem_uf), (2, 1, 0))

    def test_processo_sem_uf_do_comprador_e_descartado_e_contado(self):
        self.grava(linha(processo("ocds-sem-uf", None)))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual(self.saida.read_bytes(), b"")
        self.assertEqual((resumo.total, resumo.df, resumo.sem_uf), (1, 0, 1))

    def test_uf_vazia_conta_como_sem_uf(self):
        self.grava(linha(processo("ocds-uf-vazia", "")))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual((resumo.df, resumo.sem_uf), (0, 1))

    def test_outra_parte_no_df_nao_conta_se_o_comprador_e_de_fora(self):
        fornecedor = {"id": "BR-CNPJ-2", "roles": ["supplier"], "address": {"region": "DF"}}
        self.grava(linha(processo("ocds-go", "GO", outras_partes=[fornecedor])))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual(self.saida.read_bytes(), b"")
        self.assertEqual(resumo.df, 0)

    def test_comprador_e_achado_pelo_id_e_nao_pelo_papel(self):
        outra = {"id": "BR-CNPJ-2", "roles": ["buyer"], "address": {"region": "GO"}}
        self.grava(linha(processo("ocds-df", "DF", outras_partes=[outra], papeis=["tenderer"])))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual(resumo.df, 1)

    def test_sem_buyer_nao_casa_com_parte_sem_id(self):
        sem_buyer = {"ocid": "ocds-x", "buyer": None, "parties": [{"address": {"region": "DF"}}]}
        self.grava(linha(sem_buyer))
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual((resumo.df, resumo.sem_uf), (0, 1))

    def test_linha_gravada_e_identica_a_original(self):
        original = linha(processo("ocds-df", "DF") | {"descricao": "Medicação — açúcar"})
        self.grava(original)
        filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual(self.saida.read_bytes(), original)

    def test_linhas_em_branco_sao_ignoradas(self):
        self.grava(linha(processo("ocds-df", "DF")), b"\n")
        resumo = filtra_df.filtra(self.entrada, self.saida)
        self.assertEqual(resumo.total, 1)

    def test_linha_invalida_da_erro_e_nao_deixa_saida(self):
        self.grava(linha(processo("ocds-df", "DF")), b'{"ocid": "cortado\n')
        self.assert_falha_na_linha(2)

    def test_linha_que_nao_e_objeto_da_erro_com_o_numero_da_linha(self):
        self.grava(b"[]\n")
        self.assert_falha_na_linha(1)

    def test_parte_que_nao_e_objeto_da_erro_com_o_numero_da_linha(self):
        self.grava(linha(processo("ocds-df", "DF")), b'{"buyer": {"id": "x"}, "parties": ["x"]}\n')
        self.assert_falha_na_linha(2)


class TestMain(unittest.TestCase):
    def setUp(self):
        self.pasta = pasta_temporaria(self)
        self.entrada = self.pasta / "contratacoes_2026.jsonl"
        self.saida = self.pasta / "contratacoes_2026_df.jsonl"
        self.entrada.write_bytes(linha(processo("ocds-df", "DF")) + linha(processo("ocds-go", "GO")))

    def roda(self, *argumentos):
        return subprocess.run(
            [sys.executable, str(SRC / "filtra_df.py"), *map(str, argumentos)],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_sucesso_grava_e_registra_os_totais(self):
        resultado = self.roda(self.entrada, self.saida.as_posix())
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("2 processos, 1 com comprador no DF, 0 sem UF", resultado.stdout)
        # O caminho aparece como foi passado, sem trocar / por \ no Windows.
        self.assertIn(self.saida.as_posix(), resultado.stdout)
        self.assertTrue(self.saida.exists())

    def test_saida_existente_e_recusada_com_codigo_2(self):
        self.saida.write_bytes(b"antigo")
        resultado = self.roda(self.entrada, self.saida)
        self.assertEqual(resultado.returncode, 2)
        self.assertEqual(self.saida.read_bytes(), b"antigo")

    def test_entrada_inexistente_da_codigo_2(self):
        resultado = self.roda(self.pasta / "nao-existe.jsonl", self.saida)
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

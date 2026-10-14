# Coleta de contratações (OCDS · Compras.gov.br)

Baixa os processos de contratação do Compras.gov.br em formato [OCDS](https://standard.open-contracting.org/) e mantém só os de compradores sediados no **DF**.

## Fonte

[OCP Data Registry, publicação 157](https://data.open-contracting.org/en/publication/157). Os dados são do Compras.gov.br (SEGES/MGI), com licença CC BY 4.0. A OCP disponibiliza um arquivo `.jsonl.gz` por ano, de 2021 em diante, e o atualiza mensalmente. Cada linha é um processo (release compilada) com a licitação (`tender`) e as adjudicações (`awards`).

O arquivo do ano cobre o país todo. Por isso o coletor baixa o ano inteiro para `tmp/`, lê linha a linha e filtra.

## Filtro

O coletor mantém o processo quando a parte compradora (`buyer`) tem `address.region == "DF"`. Isso inclui todas as esferas: federal, distrital e outras. A esfera vem na coluna `comprador_esfera` de `contratacoes.csv`, para filtrar depois. Para restringir já na coleta, use `--esferas Distrital`.

Em 2026, até a atualização de set/2026, o arquivo trouxe 11.732 processos no DF: 9.693 federais, 1.386 distritais, 648 de outras esferas ("Não se Aplica", como a EBSERH) e 5 estaduais.

## Como rodar

O ambiente Python fica na raiz do repositório (`.venv`).

```bash
pip install -r tasks/coleta-contratacoes/requirements.txt

# um ou mais anos
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh 2025 2026

# opções extras depois de "--"
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh 2026 -- --esferas Distrital --alias DF-distrital-2026

# teste rápido: lê só as primeiras 5.000 linhas de cada ano
python tasks/coleta-contratacoes/src/coleta_contratacoes.py --anos 2026 --limite 5000 --alias teste
```

| Opção | Padrão | Para quê |
| --- | --- | --- |
| `--anos` | ano atual | Anos a baixar (2021 em diante). |
| `--uf` | `DF` | UF do comprador. |
| `--esferas` | todas | Esferas a manter: `Federal`, `Distrital`, `Estadual`, `Municipal`, `"Não se Aplica"`. |
| `--alias` | `DF-<anos>` | Subpasta de saída em `outputs/`. |
| `--manter-download` | não | Mantém o `.jsonl.gz` em `tmp/` (por padrão é apagado se o ano der certo). |
| `--forcar-download` | não | Baixa de novo mesmo que o arquivo já esteja em `tmp/`. |
| `--limite` | — | Lê só as N primeiras linhas de cada ano. |

Os downloads são grandes: 146 MB para 2026 e 379 MB para 2025. Com o arquivo já baixado, processar 2026 leva cerca de 30 s.

## Saídas

Ficam em `outputs/<alias>/`, que o Git ignora.

| Arquivo | Granularidade | Chave |
| --- | --- | --- |
| `contratacoes.jsonl.gz` | release OCDS original, só as selecionadas | `ocid` |
| `contratacoes.csv` | um processo de contratação | `ocid` |
| `itens.csv` | um item licitado (`tender.items` + dados do lote) | `ocid` + `item_id` |
| `adjudicacoes.csv` | um item adjudicado × fornecedor | `ocid` + `adjudicacao_id` + `item_id` + `fornecedor_id` |
| `monitoramento.csv` | um ano processado (linhas lidas, selecionadas, duração, status) | `ano` |
| `erros.csv` | linha ou ano com falha | — |
| `coleta.log` | log da execução | — |

Em `itens.csv`, `codigo_catalogo` é o código CATMAT/CATSER. Ele serve para identificar medicamentos depois, por exemplo cruzando com `tasks/mapeamento-ocds/input/dicionario-medicamentos-ocds.csv`.

## Limites conhecidos

- **Cobertura:** só entram compras feitas pelo Compras.gov.br. No CSV do PNCP em `tasks/analise-inicial-csv-e-api/`, 319 das 320 contratações distritais (abr–ago/2026) foram publicadas por essa plataforma. Órgãos que usam outras plataformas ficam de fora.
- **Defasagem:** a OCP baixa a fonte uma vez por mês. Processos publicados depois da última atualização só aparecem na seguinte. É o caso do misoprostol da SES/DF publicado em 30/09/2026.
- **Etapas:** o arquivo traz licitação e adjudicação. Contratos e empenhos virão de outros coletores.
- **Valores:** em `adjudicacoes.csv`, `valor_total_item` é quantidade × valor unitário do item, e `valor_adjudicacao` é o valor do *award* inteiro. Não some `valor_adjudicacao` por item.
- **`valor_unitario_estimado = 0`** costuma indicar orçamento sigiloso (`orcamento_sigiloso = True`).

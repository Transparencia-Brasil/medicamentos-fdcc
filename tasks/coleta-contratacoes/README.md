# Coleta de contratações (OCDS · Compras.gov.br)

Baixa os processos de contratação do Compras.gov.br em formato
[OCDS](https://standard.open-contracting.org/), mantém só os de compradores
sediados no **DF** e os salva em `outputs/` como CSVs (contratações, itens e
adjudicações), junto com as releases OCDS originais selecionadas.

A coleta em si é feita pelo repositório
[coletor-contratacoes](https://github.com/Transparencia-Brasil/coletor-contratacoes).
Esta task só o chama, define onde as saídas serão salvas e guarda o log.

## Fonte e filtro

- [OCP Data Registry, publicação 157](https://data.open-contracting.org/en/publication/157):
  dados do Compras.gov.br (SEGES/MGI), sob licença CC BY 4.0. Há um arquivo
  `.jsonl.gz` por ano, de 2021 em diante, atualizado mensalmente pela OCP.
- O arquivo do ano cobre o país todo (154 MB em 2026 e 379 MB em 2025). O
  coletor baixa o ano inteiro, filtra e apaga o download ao final, então toda
  execução baixa o arquivo de novo.
- Um processo é mantido quando a parte compradora (`buyer`) tem
  `address.region == "DF"`. Por padrão entram todas as esferas, e a esfera fica
  na coluna `comprador_esfera` de `contratacoes.csv`. Para restringir já na
  coleta, use `--esferas`.

No arquivo de 2026 baixado em 03/11/2026, foram 12.594 processos no DF, 1.459
deles distritais.

## Pré-requisitos

1. Um clone local do `coletor-contratacoes`, com o `.venv` dele criado e as
   dependências instaladas (ver o README daquele repositório).
2. A variável `COLETOR_CONTRATACOES_DIR` no `.env` da raiz deste repositório,
   apontando para esse clone. Um caminho relativo é resolvido a partir da raiz
   deste repositório; uma variável definida no ambiente tem precedência.

```bash
COLETOR_CONTRATACOES_DIR=../coletor-contratacoes
```

O script funciona no Git Bash e no WSL. No WSL, prefira o caminho relativo
acima: um caminho no formato `C:\...` não é entendido pelo Bash.

## Como rodar

De qualquer pasta:

```bash
# um ou mais anos
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2025 2026

# só compradores distritais
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2026 --esferas Distrital

# teste rápido: lê só as primeiras 5.000 linhas de cada ano
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2026 --limite 5000
```

| Opção | Padrão | Para quê |
| --- | --- | --- |
| `--anos` | ano atual | Um ou mais anos, de 2021 ao ano atual. |
| `--uf` | `DF` | UF do comprador. |
| `--esferas` | todas | Uma ou mais esferas: `Federal`, `Distrital`, `Estadual`, `Municipal`, `"Não se Aplica"`. |
| `--limite` | — | Lê só as N primeiras linhas de cada ano. |

Os valores são validados pelo coletor: ano fora do intervalo ou limite que não
seja um inteiro positivo encerram com código 2 antes de acessar a fonte. Este
script aceita só as opções acima e `--help`, que mostra a ajuda do coletor. O
destino é definido pela task, por isso `--saida` não é aceito.

Com o arquivo já baixado, processar 2026 leva cerca de 20 s; o download depende
da conexão (alguns minutos para 2026).

## Saídas

Ficam em `outputs/`, que o Git ignora (exceto o `.gitkeep`). Cada execução cria
uma pasta nova, com a data e a hora do início no nome, e nada é sobrescrito: as
coletas se acumulam até serem removidas manualmente.

```text
outputs/
├── {UF}[-{esferas}]-{anos}/{AAAAMMDD}_{HHMMSS}/
│   ├── contratacoes.jsonl.gz
│   ├── contratacoes.csv
│   ├── itens.csv
│   ├── adjudicacoes.csv
│   ├── monitoramento.csv
│   ├── erros.csv
│   └── coleta.log
└── LOGS/run-coleta-contratacoes-{UF}[-{esferas}]-{anos}-{AAAAMMDD}_{HHMMSS}.log
```

Exemplos de pasta: `outputs/DF-2025-2026/20261103_142300/` e
`outputs/DF-Distrital-2026/20261103_142300/`.

| Arquivo | Granularidade | Chave |
| --- | --- | --- |
| `contratacoes.jsonl.gz` | release OCDS original, só as selecionadas | `ocid` |
| `contratacoes.csv` | um processo de contratação | `ocid` |
| `itens.csv` | um item licitado (`tender.items` + dados do lote) | `ocid` + `item_id` |
| `adjudicacoes.csv` | um item adjudicado × fornecedor | `ocid` + `adjudicacao_id` + `item_id` + `fornecedor_id` |
| `monitoramento.csv` | um ano processado (linhas lidas, selecionadas, duração, status) | `ano` |
| `erros.csv` | linha ou ano com falha | — |
| `coleta.log` | log do coletor | — |

O log em `LOGS/` registra os argumentos, o destino, o commit do
`coletor-contratacoes` usado (com aviso se houver alterações locais nele) e toda
a saída do coletor.

Em `itens.csv`, `codigo_catalogo` é o código CATMAT/CATSER. Ele serve para
identificar medicamentos depois, por exemplo cruzando com
`tasks/mapeamento-ocds/input/dicionario-medicamentos-ocds.csv`.

## Códigos de saída

| Código | Situação |
| --- | --- |
| 0 | Todos os anos processados. |
| 1 | Algum ano falhou no download ou na leitura (ver `erros.csv` e `monitoramento.csv`). |
| 2 | Argumento inválido ou não aceito, coletor não encontrado ou pasta de destino já ocupada. |

## Limites conhecidos

- **Toda execução baixa o ano inteiro de novo:** o coletor não guarda o arquivo
  baixado entre execuções.
- **Um ano com falha não interrompe os demais:** a coleta segue para o ano
  seguinte e termina com código 1. Confira `monitoramento.csv`.

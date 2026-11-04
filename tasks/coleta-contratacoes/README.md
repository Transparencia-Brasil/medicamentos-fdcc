# Coleta de contratações (OCDS · Compras.gov.br)

Baixa os arquivos anuais de contratações do Compras.gov.br em formato
[OCDS](https://standard.open-contracting.org/) (JSON) e os descompacta em
`outputs/`, um arquivo por ano.

O download e a verificação de integridade são feitos pelo repositório
[coletor-contratacoes](https://github.com/Transparencia-Brasil/coletor-contratacoes),
que só baixa o arquivo. Esta task chama o coletor uma vez por ano, descompacta o
arquivo baixado e guarda o log. A seleção dos medicamentos e dos compradores do
DF será feita a partir desses arquivos, em uma etapa ainda a definir.

## Fonte

- [OCP Data Registry, publicação 157](https://data.open-contracting.org/en/publication/157):
  compras públicas do Governo Federal no sistema Compras.gov.br, publicadas pela
  SEGES/MGI, sob licença CC BY 4.0, atualizadas todo mês pela OCP.
- É a fonte oficial. Cobre as etapas de licitação e de adjudicação de todos os
  órgãos que usam o Compras.gov.br, do país todo, e traz **todos os itens
  comprados**, não só medicamentos.
- Há um arquivo `{ano}.jsonl.gz` por ano, de 2021 em diante, com um processo de
  contratação (release compilada OCDS) por linha.

Em 2026, no arquivo de 04/11/2026, eram 202.324 processos, 154 MB compactados e
2,35 GB descompactados. O de 2025 tem 379 MB compactado.

Para separar os medicamentos depois, vale saber:

- Cada item traz o código do item no catálogo CATMAT (`classification.id`), mas
  não a classe dele. A classe 6505 (medicamentos) só é obtida no catálogo.
- O lote traz a NCM (`ncmNbsCode`). Os medicamentos ficam nas posições 3003 e
  3004.
- A categoria de catálogo dos lotes (`catalogItemCategoryName`) vem igual em
  todos os itens e não serve para isso.

## Pré-requisitos

1. Um clone local do `coletor-contratacoes`, com o `.venv` dele criado e as
   dependências instaladas (ver o README daquele repositório).
2. A variável `COLETOR_CONTRATACOES_DIR` no `.env` da raiz deste repositório,
   apontando para esse clone. Um caminho relativo é resolvido a partir da raiz
   deste repositório; uma variável definida no ambiente tem precedência.
3. Espaço em disco: cada ano ocupa o `.gz` mais o `.jsonl`. São cerca de 2,5 GB
   em 2026 e, pela mesma proporção, de 5 a 6 GB em 2025, cujo `.gz` tem 379 MB.
   Para `--anos 2025 2026`, reserve uns 9 GB livres.

```bash
COLETOR_CONTRATACOES_DIR=../coletor-contratacoes
```

O script funciona no Git Bash e no WSL e usa o `gzip`, que vem com os dois. No
WSL, prefira o caminho relativo acima: um caminho no formato `C:\...` não é
entendido pelo Bash.

## Como rodar

De qualquer pasta:

```bash
# o ano atual
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh

# um ou mais anos
bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2025 2026
```

| Opção | Padrão | Para quê |
| --- | --- | --- |
| `--anos` | ano atual | Um ou mais anos, com quatro dígitos. |

Um ano que não tenha arquivo na fonte recebe 404 e termina com código 2, sem
impedir os demais. Este script aceita só `--anos` e `--help`. O destino é
definido pela task, por isso `--saida` não é aceito.

## Saídas

Ficam em `outputs/`, que o Git ignora (exceto o `.gitkeep`). Cada execução grava
arquivos novos, com a data e a hora no nome, e nada é sobrescrito: as coletas se
acumulam até serem removidas manualmente.

```text
outputs/
├── {ano}/
│   ├── {AAAAMMDD}_{HHMMSS}_contratacoes_{ano}.jsonl.gz
│   └── {AAAAMMDD}_{HHMMSS}_contratacoes_{ano}.jsonl
└── LOGS/run-coleta-contratacoes-{anos}-{AAAAMMDD}_{HHMMSS}.log
```

| Arquivo | Conteúdo |
| --- | --- |
| `.jsonl.gz` | O arquivo como foi publicado, verificado pelo coletor (`Content-Length` e CRC do gzip). O SHA-256 dele fica no log. |
| `.jsonl` | O mesmo conteúdo descompactado, com uma release compilada OCDS por linha. |
| `LOGS/*.log` | Os anos pedidos, o commit do `coletor-contratacoes` usado (com aviso se houver alterações locais nele) e toda a saída do coletor, incluindo a URL final, que traz a versão da publicação, e o SHA-256. |

O `.jsonl` passa por um arquivo temporário e só ganha o nome final quando a
descompactação termina, então nunca fica pela metade.

Com mais de 2 GB por ano, o `.jsonl` é pesado para abrir num editor. Para
inspecionar, prefira ler algumas linhas, por exemplo
`head -n 5 arquivo.jsonl > amostra.jsonl`. Para processar, os scripts podem ler
o `.jsonl` linha a linha ou o próprio `.gz`, sem descompactar, com
`gzip.open(caminho, "rt", encoding="utf-8")`.

## Códigos de saída

| Código | Situação |
| --- | --- |
| 0 | Todos os anos foram baixados e descompactados. |
| 1 | Algum ano falhou no download, na verificação de integridade ou na descompactação. |
| 2 | Argumento inválido ou não aceito, coletor não encontrado, ano não publicado (404) ou destino já existente. |

Com vários anos, o código final é o maior entre eles. O resultado de cada ano
fica no log, na linha `Ano {ano}: código {código}`.

## Limites conhecidos

- **Toda execução baixa os anos de novo:** um arquivo baixado antes não é
  reaproveitado.
- **Um ano com falha não interrompe os demais:** a coleta segue para o ano
  seguinte e termina com o maior código. Confira o log.
- **Uma interrupção (Ctrl-C) durante a descompactação** deixa o `.jsonl.part`
  em andamento, que pode passar de 2 GB, e o log sem a linha de fim. O `.jsonl`
  com o nome final nunca fica pela metade, e o `.part` pode ser apagado.
- **Ainda não há seleção de medicamentos nem de compradores do DF:** esta task
  entrega o dado bruto, compactado e descompactado.

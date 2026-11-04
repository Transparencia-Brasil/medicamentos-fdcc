# Coleta de contratações (OCDS · Compras.gov.br)

Baixa os arquivos anuais de contratações do Compras.gov.br em formato
[OCDS](https://standard.open-contracting.org/) (JSON), os descompacta em
`outputs/` e separa os processos com comprador no Distrito Federal, em JSON
Lines e em uma lista JSON formatada.

O download e a verificação de integridade são feitos pelo repositório
[coletor-contratacoes](https://github.com/Transparencia-Brasil/coletor-contratacoes),
que só baixa o arquivo. Esta task chama o coletor uma vez por ano, descompacta o
arquivo baixado, filtra os compradores do DF, grava essa seleção também como
lista JSON e guarda o log. A seleção dos medicamentos ainda vai ser definida.

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

## Filtro do DF

O script [`src/filtra_df.py`](src/filtra_df.py) mantém os processos cujo
comprador tem `address.region == "DF"`. O comprador é a parte de `parties[]` com
o mesmo `id` de `buyer.id`; outras partes no DF, como um fornecedor de Brasília,
não contam. Em 2026, nenhuma parte além do comprador traz UF, então essa regra só
protege contra mudanças futuras na fonte. As linhas são copiadas como vieram, sem
serem reescritas.

- A UF é a da unidade que fez a compra, não a da sede do órgão: o Comando do
  Exército, por exemplo, tem processos nas 27 UFs, e só os das unidades do DF
  entram.
- Entram todos os compradores do DF, não só o GDF. Para separar depois, o
  comprador traz a esfera e o poder em `details.classifications` (esquemas
  `BRA-ESFERA` e `BRA-PODER`) e o nome da unidade em `additionalIdentifiers`.
- O Departamento de Logística em Saúde do Ministério da Saúde está no DF, mas
  compra para o país todo, e por isso entra.

Em 2026, ficaram 12.594 dos 202.324 processos, 106 MB:

| Esfera do comprador (`BRA-ESFERA`) | Processos | Compradores (CNPJs) |
| --- | --- | --- |
| Federal | 10.454 | 137 |
| Distrital (GDF) | 1.459 | 56 |
| Não se Aplica (estatais, como EBSERH, Metrô DF e Caesb, e o Sistema S) | 676 | 18 |
| Estadual (só a Secretaria de Justiça e Cidadania do DF) | 5 | 1 |

A esfera sozinha não separa o GDF inteiro: as empresas distritais vêm como "Não
se Aplica" e uma secretaria do DF vem como "Estadual". Oito processos, todos do
Comando da Marinha, vêm sem UF do comprador e ficam de fora; o log mostra
quantos foram. Uma UF vazia também conta como "sem UF".

Uma linha que não seja JSON válido, ou que não tenha a estrutura de uma release,
interrompe o filtro com código 1 e o número da linha no log, sem deixar o
`_df.jsonl`.

Para rodar o filtro sozinho, sobre um `.jsonl` já descompactado:

```bash
python tasks/coleta-contratacoes/src/filtra_df.py ENTRADA.jsonl SAIDA_df.jsonl
```

## JSON formatado

Um arquivo JSON Lines tem um JSON completo por linha, sem nada envolvendo as
linhas. Num editor, cada processo aparece numa linha só, e um leitor de JSON
comum (`json.load`, `jsonlite::fromJSON`) dá erro depois da primeira linha.

Por isso, o script [`src/jsonl_para_json.py`](src/jsonl_para_json.py) grava
também o `_df.json`: os mesmos processos do `_df.jsonl`, na mesma ordem, numa
lista JSON com recuo de 2 espaços e acentos legíveis, igual ao resultado de
`json.dumps(lista, ensure_ascii=False, indent=2)`. Os valores são os mesmos que o
`json.load` lê no `_df.jsonl`; só a escrita pode mudar (`1E5` vira `100000.0`,
por exemplo, e uma chave repetida fica só com o último valor).

- Em 2026, são 157 MB e 4,8 milhões de linhas, convertidos em cerca de 6 s.
- O VS Code abre o arquivo, mas, acima de uns 20 MB, desliga as cores e o
  recolhimento de blocos para não travar.
- Para ler em Python: `json.load(open(caminho, encoding="utf-8"))`. Em R:
  `jsonlite::fromJSON(caminho, simplifyVector = FALSE)`.
- Só o recorte do DF é convertido. O arquivo completo, com 2,35 GB, ficaria
  grande demais para ler assim.

Para converter sozinho:

```bash
python tasks/coleta-contratacoes/src/jsonl_para_json.py ENTRADA_df.jsonl SAIDA_df.json
```

## Pré-requisitos

1. Um clone local do `coletor-contratacoes`, com o `.venv` dele criado e as
   dependências instaladas (ver o README daquele repositório).
2. A variável `COLETOR_CONTRATACOES_DIR` no `.env` da raiz deste repositório,
   apontando para esse clone. Um caminho relativo é resolvido a partir da raiz
   deste repositório; uma variável definida no ambiente tem precedência.
3. Python 3.10 ou superior, só com a biblioteca padrão, para o filtro do DF e
   a conversão para JSON. O script testa, nesta ordem, o do `.venv` da raiz
   deste repositório e o `python3` e o `python` do sistema, e usa o primeiro que
   rodar com a versão certa. Assim, um atalho que não funciona, como o
   `python3` da Microsoft Store, é ignorado.
4. Espaço em disco: cada ano ocupa o `.gz` e o `.jsonl`, mais o `_df.jsonl` e o
   `_df.json`. São cerca de 2,75 GB em 2026 (2,5 GB do `.gz` e do `.jsonl` e
   263 MB do recorte do DF) e, pela mesma proporção, de 5 a 6 GB em 2025, cujo
   `.gz` tem 379 MB. Para `--anos 2025 2026`, reserve uns 9 GB livres.

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
│   ├── {AAAAMMDD}_{HHMMSS}_contratacoes_{ano}.jsonl
│   ├── {AAAAMMDD}_{HHMMSS}_contratacoes_{ano}_df.jsonl
│   └── {AAAAMMDD}_{HHMMSS}_contratacoes_{ano}_df.json
└── LOGS/run-coleta-contratacoes-{anos}-{AAAAMMDD}_{HHMMSS}.log
```

| Arquivo | Conteúdo |
| --- | --- |
| `.jsonl.gz` | O arquivo como foi publicado, verificado pelo coletor (`Content-Length` e CRC do gzip). O SHA-256 dele fica no log. |
| `.jsonl` | O mesmo conteúdo descompactado, com uma release compilada OCDS por linha. |
| `_df.jsonl` | Só as linhas do `.jsonl` com comprador no DF (ver [Filtro do DF](#filtro-do-df)). |
| `_df.json` | Os mesmos processos do `_df.jsonl`, em lista JSON formatada (ver [JSON formatado](#json-formatado)). |
| `LOGS/*.log` | Os anos pedidos, o commit do `coletor-contratacoes` usado (com aviso se houver alterações locais nele), toda a saída do coletor, incluindo a URL final, que traz a versão da publicação, e o SHA-256, e os totais do filtro do DF e da conversão. |

O `.jsonl`, o `_df.jsonl` e o `_df.json` passam por um arquivo temporário
(`.part`) e só ganham o nome final quando terminam, então nunca ficam pela
metade.

Com mais de 2 GB por ano, o `.jsonl` é pesado para abrir num editor. Para
inspecionar, prefira ler algumas linhas, por exemplo
`head -n 5 arquivo.jsonl > amostra.jsonl`. Para processar, os scripts podem ler
o `.jsonl` linha a linha ou o próprio `.gz`, sem descompactar, com
`gzip.open(caminho, "rt", encoding="utf-8")`.

## Códigos de saída

| Código | Situação |
| --- | --- |
| 0 | Todos os anos foram baixados, descompactados, filtrados e convertidos. |
| 1 | Algum ano falhou no download, na verificação de integridade, na descompactação, no filtro do DF ou na conversão para JSON. |
| 2 | Argumento inválido ou não aceito, coletor ou Python não encontrados, ano não publicado (404) ou destino já existente. |

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
- **Uma interrupção durante o filtro ou a conversão** com Ctrl-C apaga o
  `.part` do `_df.jsonl` ou do `_df.json`. Se o processo for morto (fechar o
  terminal, `kill`), o `.part` fica e pode ser apagado. Nos dois casos, o log
  fica sem a linha `Ano {ano}`.
- **Ainda não há seleção de medicamentos:** o `_df.jsonl` e o `_df.json` trazem
  todos os itens comprados pelos órgãos do DF.

## Testes

Da raiz do repositório:

```bash
python -m unittest discover -s tasks/coleta-contratacoes/tests -v
```

Não acessam a rede. Cobrem:

- o filtro do DF, com arquivos pequenos montados no próprio teste: comprador do
  DF e de outra UF, comprador sem UF ou com UF vazia, processo sem `buyer`,
  fornecedor no DF com comprador de fora, comprador achado pelo `id` e não pelo
  papel, linha copiada byte a byte, linhas inválidas e os códigos de saída;
- a conversão para JSON: resultado igual ao `json.dumps` da lista (inclusive
  com os separadores Unicode U+2028, U+2029 e U+0085 dentro de textos), acentos
  legíveis, entrada vazia, linhas em branco, linha inválida, texto que não é
  UTF-8, surrogate solto e os códigos de saída;
- o `run-coleta-contratacoes.sh`, com um coletor falso: a coleta completa, a
  escolha do Python (pulando um `python3` que não funciona), o `_df.json`
  gerado, o filtro e a conversão que não rodam quando o coletor falha, um
  código inesperado do filtro virando 1 e uma falha na conversão, que mantém o
  `_df.jsonl` e não deixa o `_df.json`.

Os testes do script usam o Bash do Git for Windows no Windows e são pulados se
não houver Bash.

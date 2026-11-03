# Coleta de contratos (Contratos.gov.br · SEGES)

Baixa o CSV de contratos do Contratos.gov.br publicado pela SEGES em
<https://repositorio.dados.gov.br/seges/comprasnet_contratos/> e o salva em
`outputs/`, exatamente como veio da fonte. O arquivo cobre o país todo: o
recorte do GDF fica para uma task seguinte.

A coleta em si é feita pelo repositório
[coletor-contratos](https://github.com/Transparencia-Brasil/coletor-contratos).
Esta task só o chama, define onde o arquivo será salvo e guarda o log.

## Pré-requisitos

1. Um clone local do `coletor-contratos`, com o `.venv` dele criado e as
   dependências instaladas (ver o README daquele repositório).
2. A variável `COLETOR_CONTRATOS_DIR` no `.env` da raiz deste repositório,
   apontando para esse clone. Um caminho relativo é resolvido a partir da raiz
   deste repositório; uma variável definida no ambiente tem precedência.

```bash
COLETOR_CONTRATOS_DIR=../coletor-contratos
```

O script funciona no Git Bash e no WSL. No WSL, prefira o caminho relativo
acima: um caminho no formato `C:\...` não é entendido pelo Bash.

## Como rodar

De qualquer pasta, informe o tipo de coleta e o período:

```bash
bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta anual --ano 2026
bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta mensal --ano 2026 --mes 07
bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta diario --ano 2026 --mes 07 --dia 09
```

| Coleta | Parâmetros exigidos | Arquivo na fonte |
| --- | --- | --- |
| `anual` | `--ano` | contratos criados ou alterados no ano (de 57 MB a 165 MB) |
| `mensal` | `--ano` e `--mes` | só os novos ou alterados no mês |
| `diario` | `--ano`, `--mes` e `--dia` | só os novos ou alterados no dia |

Os argumentos são validados pelo coletor: parâmetro faltando ou sobrando, mês
fora de 1 a 12 ou data inexistente encerram com código 2 antes de acessar a
fonte. Este script aceita só `--coleta`, `--ano`, `--mes` e `--dia` (também na
forma `--ano=2026`), além de `--help`. O destino é definido pela task, por isso
`--saida` não é aceito.

## Saídas

Ficam em `outputs/`, que o Git ignora (exceto o `.gitkeep`):

```text
outputs/
├── anual/{ano}/{AAAAMMDD}_{HHMMSS}_contratos_anual_{ano}.csv
├── mensal/{ano}/{mes}/{AAAAMMDD}_{HHMMSS}_contratos_mensal_{ano}-{mes}.csv
├── diario/{ano}/{mes}/{dia}/{AAAAMMDD}_{HHMMSS}_contratos_diario_{ano}-{mes}-{dia}.csv
└── LOGS/run-coleta-contratos-{coleta}-{período}-{AAAAMMDD}_{HHMMSS}.log
```

A data e a hora no nome são as do início da execução. Cada execução gera um
arquivo novo, e nada é sobrescrito: as cópias se acumulam até serem removidas
manualmente.

O log registra os argumentos, o destino, o commit do `coletor-contratos` usado
(com aviso se houver alterações locais nele) e toda a saída do coletor, inclusive
o `Last-Modified` do arquivo na fonte, que indica a versão dos dados.

## Códigos de saída

| Código | Situação |
| --- | --- |
| 0 | Arquivo salvo. |
| 1 | Falha de rede, HTTP diferente de 200 e 404, download incompleto ou erro de escrita. |
| 2 | Argumento inválido ou não aceito, coletor não encontrado, período não publicado (404) ou destino já existente. |

## Limites conhecidos

- **A fonte parou de atualizar:** o último arquivo publicado é de 09/07/2026.
  Mensais e diários têm lacunas (faltam, por exemplo, 11/2022 e set a dez/2025);
  um período não publicado sai com código 2.
- **O GDF aparece pouco:** só entram órgãos que usam o Contratos.gov.br. No
  arquivo, o GDF vem com esfera "Estadual" e `orgao_codigo` 97400 ("DISTRITO
  FEDERAL") ou 25915 ("FUNDO CONSTITUCIONAL DO DISTRITO FEDERAL").
- **Pasta vazia após 404:** o coletor cria a pasta do período antes de consultar
  a fonte, então um período não publicado deixa a pasta vazia em `outputs/`.

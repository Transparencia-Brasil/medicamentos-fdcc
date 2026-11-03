#!/usr/bin/env bash
# Executa o coletor de contratações OCDS do Compras.gov.br (repositório
# coletor-contratacoes) e salva as saídas em tasks/coleta-contratacoes/outputs/.
#
# Uso (de qualquer pasta, no Git Bash ou no WSL):
#   bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2025 2026
#   bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2026 --esferas Distrital
#   bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2026 --limite 5000
#
# O caminho do coletor vem de COLETOR_CONTRATACOES_DIR, no ambiente ou no .env
# da raiz (o ambiente tem precedência). A validação dos valores fica no coletor.
#
# Códigos de saída: os do coletor (0 sucesso; 1 algum ano falhou; 2 argumento
# inválido ou destino ocupado) e 2 quando o coletor não é encontrado ou um
# argumento não é aceito por este script.

set -euo pipefail


# : SET DIR --------------------------------------------------------------------

# Garante que o script rode a partir da raiz do repositório
cd "$(dirname "$0")/../../.." || { echo "Erro: não foi possível acessar a raiz do projeto." >&2; exit 1; }
RAIZ="$(pwd)"
TASK_DIR="tasks/coleta-contratacoes"


# : COLETOR --------------------------------------------------------------------

# Lê só a linha COLETOR_CONTRATACOES_DIR do .env, sem carregar o arquivo inteiro.
if [ -z "${COLETOR_CONTRATACOES_DIR:-}" ] && [ -f .env ]; then
  COLETOR_CONTRATACOES_DIR="$(grep -E '^[[:space:]]*COLETOR_CONTRATACOES_DIR=' .env | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)"
  COLETOR_CONTRATACOES_DIR="${COLETOR_CONTRATACOES_DIR%\"}"
  COLETOR_CONTRATACOES_DIR="${COLETOR_CONTRATACOES_DIR#\"}"
fi

if [ -z "${COLETOR_CONTRATACOES_DIR:-}" ]; then
  echo "Erro: defina COLETOR_CONTRATACOES_DIR no .env ou no ambiente (ex.: ../coletor-contratacoes)." >&2
  exit 2
fi

# Caminho relativo é resolvido a partir da raiz deste repositório
case "$COLETOR_CONTRATACOES_DIR" in
  /*|[A-Za-z]:*) ;;
  *) COLETOR_CONTRATACOES_DIR="$RAIZ/$COLETOR_CONTRATACOES_DIR" ;;
esac

WRAPPER="$COLETOR_CONTRATACOES_DIR/src/ETL/coletores/run-coleta-contratacoes.sh"
if [ ! -f "$WRAPPER" ]; then
  echo "Erro: coletor não encontrado em '$WRAPPER'. Confira COLETOR_CONTRATACOES_DIR." >&2
  exit 2
fi


# : ARGUMENTOS -----------------------------------------------------------------

# Só as opções do recorte são aceitas. O destino é definido por esta task, por
# isso --saida não é aceito. --anos e --esferas recebem um ou mais valores, até
# a próxima opção.
ANOS=()
ESFERAS=()
UF="DF"
LIMITE=""
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      exec bash "$WRAPPER" --help
      ;;
    --anos|--esferas)
      opcao="$1"
      shift
      while [ $# -gt 0 ] && [[ "$1" != --* ]]; do
        if [ "$opcao" = "--anos" ]; then ANOS+=("$1"); else ESFERAS+=("$1"); fi
        shift
      done
      ;;
    --uf|--limite)
      if [ $# -lt 2 ]; then
        echo "Erro: $1 exige um valor." >&2
        exit 2
      fi
      if [ "$1" = "--uf" ]; then UF="$2"; else LIMITE="$2"; fi
      shift 2
      ;;
    *)
      echo "Erro: argumento não aceito: '$1'. Use --anos, --uf, --esferas e --limite." >&2
      exit 2
      ;;
  esac
done

# Sem --anos, coleta o ano atual, como o coletor.
[ ${#ANOS[@]} -eq 0 ] && ANOS=("$(date +%Y)")

ARGS=(--anos "${ANOS[@]}" --uf "$UF")
[ ${#ESFERAS[@]} -gt 0 ] && ARGS+=(--esferas "${ESFERAS[@]}")
[ -n "$LIMITE" ] && ARGS+=(--limite "$LIMITE")

# Alias da pasta de saída, igual ao padrão do coletor: UF, esferas e anos
# ordenados, separados por "-" (espaços viram "_").
mapfile -t ANOS_ORDENADOS < <(printf '%s\n' "${ANOS[@]}" | sort -n -u)
PARTES=("${UF^^}")
if [ ${#ESFERAS[@]} -gt 0 ]; then
  mapfile -t ESFERAS_ORDENADAS < <(printf '%s\n' "${ESFERAS[@]}" | LC_ALL=C sort -u)
  PARTES+=("${ESFERAS_ORDENADAS[@]}")
fi
PARTES+=("${ANOS_ORDENADOS[@]}")
ALIAS="$(IFS=-; echo "${PARTES[*]}")"
ALIAS="${ALIAS// /_}"


# : SAÍDA E LOG ----------------------------------------------------------------

AGORA="$(date +%Y%m%d_%H%M%S)"
# Caminho relativo à raiz: funciona também com o Python do Windows chamado pelo WSL.
DESTINO="${TASK_DIR}/outputs/${ALIAS}/${AGORA}"
LOG_DIR="${TASK_DIR}/outputs/LOGS"
LOG_FILE="${LOG_DIR}/run-coleta-contratacoes-${ALIAS}-${AGORA}.log"
mkdir -p "$LOG_DIR"

COMMIT="$(git -C "$COLETOR_CONTRATACOES_DIR" rev-parse --short HEAD 2>/dev/null || echo "desconhecido")"
# autocrlf=true evita falso positivo no WSL, cujo git compara os arquivos CRLF
# do checkout do Windows com o LF do repositório.
if [ -n "$(git -c core.autocrlf=true -C "$COLETOR_CONTRATACOES_DIR" status --porcelain 2>/dev/null || true)" ]; then
  COMMIT="$COMMIT (git status indica alterações locais)"
fi

{
  echo "INÍCIO: $(date +"%d-%b-%Y %H:%M:%S")"
  echo "Coletor: $COLETOR_CONTRATACOES_DIR"
  echo "Commit do coletor: $COMMIT"
  echo "Argumentos: ${ARGS[*]}"
  echo "Destino: $DESTINO"
  echo "Log: $LOG_FILE"
  echo ""
} | tee "$LOG_FILE"


# : RODAR COLETOR --------------------------------------------------------------

set +e
bash "$WRAPPER" "${ARGS[@]}" --saida "$DESTINO" 2>&1 | tee -a "$LOG_FILE"
CODIGO=${PIPESTATUS[0]}
set -e

{
  echo ""
  echo "FIM: $(date +"%d-%b-%Y %H:%M:%S") (código de saída $CODIGO)"
} | tee -a "$LOG_FILE"

exit "$CODIGO"

#!/usr/bin/env bash
# Executa o coletor de contratos do Contratos.gov.br (repositório coletor-contratos)
# e salva o CSV em tasks/coleta-contratos/outputs/.
#
# Uso (de qualquer pasta, no Git Bash ou no WSL):
#   bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta anual --ano 2026
#   bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta mensal --ano 2026 --mes 07
#   bash tasks/coleta-contratos/src/run-coleta-contratos.sh --coleta diario --ano 2026 --mes 07 --dia 09
#
# O caminho do coletor vem de COLETOR_CONTRATOS_DIR, no ambiente ou no .env da
# raiz (o ambiente tem precedência). A validação dos argumentos fica no coletor.
#
# Códigos de saída: os do coletor (0 arquivo salvo; 1 falha no download; 2
# argumento inválido, período não publicado ou destino já existente) e 2 quando
# o coletor não é encontrado ou um argumento não é aceito por este script.

set -euo pipefail


# : SET DIR --------------------------------------------------------------------

# Garante que o script rode a partir da raiz do repositório
cd "$(dirname "$0")/../../.." || { echo "Erro: não foi possível acessar a raiz do projeto." >&2; exit 1; }
RAIZ="$(pwd)"
TASK_DIR="tasks/coleta-contratos"


# : COLETOR --------------------------------------------------------------------

# Lê só a linha COLETOR_CONTRATOS_DIR do .env, sem carregar o arquivo inteiro.
if [ -z "${COLETOR_CONTRATOS_DIR:-}" ] && [ -f .env ]; then
  COLETOR_CONTRATOS_DIR="$(grep -E '^[[:space:]]*COLETOR_CONTRATOS_DIR=' .env | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)"
  COLETOR_CONTRATOS_DIR="${COLETOR_CONTRATOS_DIR%\"}"
  COLETOR_CONTRATOS_DIR="${COLETOR_CONTRATOS_DIR#\"}"
fi

if [ -z "${COLETOR_CONTRATOS_DIR:-}" ]; then
  echo "Erro: defina COLETOR_CONTRATOS_DIR no .env ou no ambiente (ex.: ../coletor-contratos)." >&2
  exit 2
fi

# Caminho relativo é resolvido a partir da raiz deste repositório
case "$COLETOR_CONTRATOS_DIR" in
  /*|[A-Za-z]:*) ;;
  *) COLETOR_CONTRATOS_DIR="$RAIZ/$COLETOR_CONTRATOS_DIR" ;;
esac

WRAPPER="$COLETOR_CONTRATOS_DIR/src/coletores/run-coleta-contratos.sh"
if [ ! -f "$WRAPPER" ]; then
  echo "Erro: coletor não encontrado em '$WRAPPER'. Confira COLETOR_CONTRATOS_DIR." >&2
  exit 2
fi


# : ARGUMENTOS -----------------------------------------------------------------

# Só as opções do período são aceitas, na forma exata, para que o caminho de
# saída montado aqui corresponda ao que o coletor vai validar. O destino é
# definido por esta task, por isso --saida não é aceito.
COLETA=""
ANO=""
MES=""
DIA=""
args=("$@")
i=0
while [ $i -lt ${#args[@]} ]; do
  arg="${args[$i]}"
  case "$arg" in
    -h|--help)
      exec bash "$WRAPPER" --help
      ;;
    --coleta|--ano|--mes|--dia)
      valor="${args[$((i + 1))]:-}"
      i=$((i + 1))
      ;;
    --coleta=*|--ano=*|--mes=*|--dia=*)
      valor="${arg#*=}"
      arg="${arg%%=*}"
      ;;
    *)
      echo "Erro: argumento não aceito: '$arg'. Use --coleta, --ano, --mes e --dia." >&2
      exit 2
      ;;
  esac
  case "$arg" in
    --coleta) COLETA="$valor" ;;
    --ano) ANO="$valor" ;;
    --mes) MES="$valor" ;;
    --dia) DIA="$valor" ;;
  esac
  i=$((i + 1))
done

# Completa mês e dia com zero à esquerda, como o coletor; valores inválidos
# seguem como vieram e são recusados por ele.
completa_zero() {
  if [[ "$1" =~ ^[0-9]{1,2}$ ]]; then printf '%02d' "$((10#$1))"; else printf '%s' "$1"; fi
}
MES="$(completa_zero "$MES")"
DIA="$(completa_zero "$DIA")"

case "$COLETA" in
  anual) PARTES=("$ANO") ;;
  mensal) PARTES=("$ANO" "$MES") ;;
  *) PARTES=("$ANO" "$MES" "$DIA") ;;
esac
PASTAS="$(IFS=/; echo "${PARTES[*]}")"
ROTULO="$(IFS=-; echo "${PARTES[*]}")"


# : SAÍDA E LOG ----------------------------------------------------------------

AGORA="$(date +%Y%m%d_%H%M%S)"
# Caminho relativo à raiz: funciona também com o Python do Windows chamado pelo WSL.
DESTINO="${TASK_DIR}/outputs/${COLETA}/${PASTAS}/${AGORA}_contratos_${COLETA}_${ROTULO}.csv"
LOG_DIR="${TASK_DIR}/outputs/LOGS"
LOG_FILE="${LOG_DIR}/run-coleta-contratos-${COLETA}-${ROTULO}-${AGORA}.log"
mkdir -p "$LOG_DIR"

COMMIT="$(git -C "$COLETOR_CONTRATOS_DIR" rev-parse --short HEAD 2>/dev/null || echo "desconhecido")"
# autocrlf=true evita falso positivo no WSL, cujo git compara os arquivos CRLF
# do checkout do Windows com o LF do repositório.
if [ -n "$(git -c core.autocrlf=true -C "$COLETOR_CONTRATOS_DIR" status --porcelain 2>/dev/null || true)" ]; then
  COMMIT="$COMMIT (git status indica alterações locais)"
fi

{
  echo "INÍCIO: $(date +"%d-%b-%Y %H:%M:%S")"
  echo "Coletor: $COLETOR_CONTRATOS_DIR"
  echo "Commit do coletor: $COMMIT"
  echo "Argumentos: $*"
  echo "Destino: $DESTINO"
  echo "Log: $LOG_FILE"
  echo ""
} | tee "$LOG_FILE"


# : RODAR COLETOR --------------------------------------------------------------

set +e
bash "$WRAPPER" "$@" --saida "$DESTINO" 2>&1 | tee -a "$LOG_FILE"
CODIGO=${PIPESTATUS[0]}
set -e

{
  echo ""
  echo "FIM: $(date +"%d-%b-%Y %H:%M:%S") (código de saída $CODIGO)"
} | tee -a "$LOG_FILE"

exit "$CODIGO"

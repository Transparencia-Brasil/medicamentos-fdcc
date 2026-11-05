#!/usr/bin/env bash
# Baixa os arquivos anuais de contratações do Compras.gov.br em OCDS (JSON) com o
# coletor-contratacoes, os descompacta em tasks/coleta-contratacoes/outputs/ e
# separa os processos com comprador no DF (filtra_df.py), em JSON Lines e em
# lista JSON formatada (jsonl_para_json.py).
#
# Uso (de qualquer pasta, no Git Bash ou no WSL):
#   bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2026
#   bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh --anos 2025 2026
#
# O caminho do coletor vem de COLETOR_CONTRATACOES_DIR, no ambiente ou no .env
# da raiz (o ambiente tem precedência). O coletor é chamado uma vez por ano; um
# ano com falha não interrompe os demais.
#
# Códigos de saída: 0 quando todos os anos foram baixados, descompactados,
# filtrados e convertidos; se algum falhou, o maior código entre os anos (1 falha
# de rede, integridade, descompactação, filtro ou conversão; 2 ano não publicado
# ou destino já existente); 2 também quando o coletor ou o Python não são
# encontrados ou um argumento é inválido.

set -euo pipefail


# : SET DIR --------------------------------------------------------------------

# Garante que o script rode a partir da raiz do repositório
cd "$(dirname "$0")/../../.." || { echo "Erro: não foi possível acessar a raiz do projeto." >&2; exit 1; }
RAIZ="$(pwd)"
TASK_DIR="tasks/coleta-contratacoes"

uso() {
  cat <<'USO'
Uso: bash tasks/coleta-contratacoes/src/run-coleta-contratacoes.sh [--anos ANO ...]

Baixa os arquivos anuais da publicação 157 (Compras.gov.br, OCDS em JSON) com o
coletor-contratacoes, os descompacta em tasks/coleta-contratacoes/outputs/{ano}/
e separa os processos com comprador no DF em *_df.jsonl e *_df.json.

  --anos ANO ...   Um ou mais anos, com quatro dígitos. Padrão: o ano atual.
USO
}

# --help funciona mesmo sem o coletor configurado.
for argumento in "$@"; do
  case "$argumento" in
    -h|--help) uso; exit 0 ;;
  esac
done


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

# Python do filtro do DF: o do .venv da raiz, se existir; senão, o do sistema.
# O filtro usa só a biblioteca padrão. Cada candidato é executado antes de ser
# aceito, porque um python3 no PATH pode não funcionar (o atalho da Microsoft
# Store, um .venv quebrado ou, no WSL, um .exe sem interop).
PYTHON=""
for candidato in .venv/Scripts/python.exe .venv/bin/python python3 python; do
  if "$candidato" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    PYTHON="$candidato"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Erro: Python 3.10 ou superior não encontrado (nem no .venv da raiz, nem python3/python no PATH)." >&2
  exit 2
fi


# : ARGUMENTOS -----------------------------------------------------------------

# --anos recebe um ou mais valores, até a próxima opção. O destino é definido por
# esta task, por isso --saida não é aceito.
ANOS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --anos)
      shift
      valores=0
      while [ $# -gt 0 ] && [[ "$1" != --* ]]; do
        ANOS+=("$1")
        shift
        valores=$((valores + 1))
      done
      if [ "$valores" -eq 0 ]; then
        echo "Erro: --anos exige ao menos um valor." >&2
        exit 2
      fi
      ;;
    *)
      echo "Erro: argumento não aceito: '$1'. Use --anos." >&2
      exit 2
      ;;
  esac
done

# Sem --anos, coleta o ano atual, como o coletor.
[ ${#ANOS[@]} -eq 0 ] && ANOS=("$(date +%Y)")

# O ano entra no caminho de saída antes de chegar ao coletor, então é validado
# aqui com a mesma regra dele: quatro dígitos ASCII.
for ano in "${ANOS[@]}"; do
  if [[ ! "$ano" =~ ^[0-9]{4}$ ]]; then
    echo "Erro: ano inválido: '$ano'. Use quatro dígitos, como 2026." >&2
    exit 2
  fi
done
mapfile -t ANOS < <(printf '%s\n' "${ANOS[@]}" | sort -n -u)


# : LOG ------------------------------------------------------------------------

AGORA="$(date +%Y%m%d_%H%M%S)"
ROTULO="$(IFS=-; echo "${ANOS[*]}")"
LOG_DIR="${TASK_DIR}/outputs/LOGS"
LOG_FILE="${LOG_DIR}/run-coleta-contratacoes-${ROTULO}-${AGORA}.log"
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
  echo "Anos: ${ANOS[*]}"
  echo "Log: $LOG_FILE"
} | tee "$LOG_FILE"


# : COLETA, DESCOMPACTAÇÃO E FILTRO DO DF --------------------------------------

# Descompacta o .jsonl.gz ao lado dele, passando por um .part para não deixar um
# .jsonl pela metade. O .gz fica: é o arquivo publicado, com o SHA-256 do log.
descompacta() {
  local gz="$1" jsonl="${1%.gz}"
  if gzip -dc "$gz" > "$jsonl.part" && mv "$jsonl.part" "$jsonl"; then
    echo "Descompactado em $jsonl ($(wc -c < "$jsonl") bytes)"
  else
    rm -f "$jsonl.part"
    echo "Erro: falha ao descompactar $gz" >&2
    return 1
  fi
}

CODIGO_FINAL=0
for ano in "${ANOS[@]}"; do
  # Caminho relativo à raiz: funciona também com o Python do Windows chamado pelo WSL.
  ARQUIVO="${TASK_DIR}/outputs/${ano}/$(date +%Y%m%d_%H%M%S)_contratacoes_${ano}.jsonl.gz"
  {
    echo ""
    echo "--- Ano $ano: $ARQUIVO"
  } | tee -a "$LOG_FILE"

  set +e
  bash "$WRAPPER" --ano "$ano" --saida "$ARQUIVO" 2>&1 | tee -a "$LOG_FILE"
  CODIGO=${PIPESTATUS[0]}
  if [ "$CODIGO" -eq 0 ]; then
    descompacta "$ARQUIVO" 2>&1 | tee -a "$LOG_FILE"
    [ "${PIPESTATUS[0]}" -eq 0 ] || CODIGO=1
  fi
  # Nos dois passos em Python, um código fora dos documentados (Ctrl-C, um Python
  # que quebra no meio: 130, 49...) vira 1.
  DF="${ARQUIVO%.jsonl.gz}_df.jsonl"
  if [ "$CODIGO" -eq 0 ]; then
    "$PYTHON" "${TASK_DIR}/src/filtra_df.py" "${ARQUIVO%.gz}" "$DF" 2>&1 | tee -a "$LOG_FILE"
    CODIGO=${PIPESTATUS[0]}
    [ "$CODIGO" -le 2 ] || CODIGO=1
  fi
  # A mesma seleção do DF em lista JSON formatada, para ler no editor.
  if [ "$CODIGO" -eq 0 ]; then
    "$PYTHON" "${TASK_DIR}/src/jsonl_para_json.py" "$DF" "${DF%.jsonl}.json" 2>&1 | tee -a "$LOG_FILE"
    CODIGO=${PIPESTATUS[0]}
    [ "$CODIGO" -le 2 ] || CODIGO=1
  fi
  set -e

  echo "Ano $ano: código $CODIGO" | tee -a "$LOG_FILE"
  if [ "$CODIGO" -gt "$CODIGO_FINAL" ]; then CODIGO_FINAL=$CODIGO; fi
done

{
  echo ""
  echo "FIM: $(date +"%d-%b-%Y %H:%M:%S") (código de saída $CODIGO_FINAL)"
} | tee -a "$LOG_FILE"

exit "$CODIGO_FINAL"

#!/usr/bin/env bash
# Приёмка «открывается на чужой машине» — одной командой с мака.
#
#   bash priemka.sh <listing_id> [<listing_id> ...]
#
# Для каждого листинга: прогоняет проверенный зелёный на твоём стенде, печатает
# вердикт, скачивает скриншот «глазами покупателя» в ~/Extella-priemka/ и
# открывает его. Стенд — твой VPS, токен — твой, чужого кода нет.
# (Имена переменных латиницей: bash не принимает кириллицу в идентификаторах.)
set -u

BENCH_HOST="${BENCH_HOST:-ubuntu@82.115.42.21}"
KEY="${KEY:-$HOME/.ssh/extella_hosting_ed25519}"
OUTDIR="$HOME/Extella-priemka"
SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10)

if [ "$#" -lt 1 ]; then
  echo "как звать: bash priemka.sh <listing_id> [<listing_id> ...]"
  exit 2
fi
mkdir -p "$OUTDIR"

fail_all=0
for lid in "$@"; do
  echo "──────────────────────────────────────────"
  echo "приёмка: $lid"
  out=$(ssh "${SSH_OPTS[@]}" "$BENCH_HOST" \
    "cd ~/extella-bench && timeout 260 python3 check_opens_elsewhere.py --домен '$lid'" 2>&1)
  code=$?
  echo "$out"
  folder=$(printf '%s\n' "$out" | sed -n 's/.*DOM и скриншот: //p' | tail -1)
  if [ -n "$folder" ]; then
    loc="$OUTDIR/${lid}.png"
    if scp "${SSH_OPTS[@]}" "$BENCH_HOST:$folder/окно_на_домене.png" "$loc" >/dev/null 2>&1; then
      echo "скриншот: $loc"
      command -v open >/dev/null 2>&1 && open "$loc" >/dev/null 2>&1
    fi
  fi
  if [ "$code" -eq 1 ]; then
    echo ">> СТОП: не выкладывай."
    fail_all=1
  elif [ "$code" -eq 2 ]; then
    echo ">> проба не смогла прогнать (см. вывод выше)."
    [ "$fail_all" -eq 0 ] && fail_all=2
  else
    echo ">> можно выкладывать."
  fi
done
echo "──────────────────────────────────────────"
exit "$fail_all"

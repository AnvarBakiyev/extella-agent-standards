#!/usr/bin/env bash
# Одна команда, которая гоняет ВСЕ самопроверки стандартов.
#
# Зачем. Гейтов стало пятнадцать, и каждый со своей командой. Запускать их поодиночке никто не
# будет — а гейт, который никто не гоняет, тихо краснеет и перестаёт защищать. Это не догадка:
# 22.07 гейт account-scope был красным неделю, 28.07 мой собственный гейт канона начал врать
# через несколько часов после написания, потому что правило сменилось, а проверка нет.
#
# Использование:
#   bash tools/run_all_gates.sh                    # все самопроверки (как раньше)
#   bash tools/run_all_gates.sh --quiet            # только итог и провалы
#   bash tools/run_all_gates.sh --stage demo       # только то, что требует стадия
#
# Про --stage. Прежде тут гонялись все гейты всегда, и это была та самая полная цена
# «сразу как в проде»: на показе клиенту она стоила дороже продукта. Объём берётся у
# tools/stage_gates.py, чтобы список жил в одном месте (stages.yaml), а не в двух.
#
# Коды выхода: 0 — все зелёные, 1 — есть провалившиеся.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUIET=""
STAGE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --quiet) QUIET="--quiet" ;;
    --stage) STAGE="${2:-}"; shift ;;
    *) echo "неизвестный аргумент: $1" >&2; exit 2 ;;
  esac
  shift
done
FAILED=""
OK=0

run() {
  local name="$1"
  local out
  if out="$(python3 "$ROOT/tools/$name.py" --selftest 2>&1)"; then
    OK=$((OK + 1))
    [ "$QUIET" = "--quiet" ] || printf "  ✓ %-30s %s\n" "$name" "$(echo "$out" | tail -1)"
  else
    FAILED="$FAILED $name"
    printf "  ✗ %-30s ПРОВАЛ\n" "$name"
    echo "$out" | grep -E "^FAIL" | sed 's/^/      /'
  fi
}

run_command() {
  local name="$1"
  shift
  local out
  if out="$("$@" 2>&1)"; then
    OK=$((OK + 1))
    [ "$QUIET" = "--quiet" ] || printf "  ✓ %-30s %s\n" "$name" "$(echo "$out" | tail -1)"
  else
    FAILED="$FAILED $name"
    printf "  ✗ %-30s ПРОВАЛ\n" "$name"
    printf '%s\n' "$out" | tail -20 | sed 's/^/      /'
  fi
}

printf "\n\033[1mСамопроверки стандартов Extella\033[0m\n"

run stage_gates          # сам файл стадий обязан быть цел, иначе объём считается неверно

if [ -n "$STAGE" ]; then
  # Стадия задана — гоняем ровно её набор. Ошибку неизвестной стадии выдаёт stage_gates.py.
  LIST="$(python3 "$ROOT/tools/stage_gates.py" --stage "$STAGE" --json)" || exit 1
  printf "  стадия %s\n" "$STAGE"
  for gate in $(printf '%s' "$LIST" | python3 -c "import json,sys; print(' '.join(json.load(sys.stdin)['гейты']))"); do
    run "$gate"
  done
  printf "\n\033[1mИТОГ (стадия %s):\033[0m " "$STAGE"
  if [ -z "$FAILED" ]; then echo "зелёных $OK, провалов нет"; exit 0; fi
  echo "зелёных $OK, ПРОВАЛИЛИСЬ:$FAILED"
  exit 1
fi

run check_agent_passport
run check_automation_passport
run check_state_contract
run check_masking_policy
run check_code_canon
run check_single_source
run check_brand_copy
run check_design_rule
run check_findings_log
run check_agent_drift
run register_new_agents
run check_agent_repo
run check_manifest_copies
run check_surface_classes
run check_edition
run deploy_edition
run build_agent_cabinet
run build_automation_cabinet
run build_capability_registry
run_command store_page_contract node "$ROOT/store_app/test_page_contract.mjs"
run_command store_product python3 "$ROOT/store_app/product/test_product.py"

printf "\n\033[1mИТОГ:\033[0m "
if [ -z "$FAILED" ]; then
  echo "зелёных $OK, провалов нет"
  exit 0
fi
echo "зелёных $OK, ПРОВАЛИЛИСЬ:$FAILED"
exit 1

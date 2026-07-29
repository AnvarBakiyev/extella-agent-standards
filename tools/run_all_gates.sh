#!/usr/bin/env bash
# Одна команда, которая гоняет ВСЕ самопроверки стандартов.
#
# Зачем. Гейтов стало четырнадцать, и каждый со своей командой. Запускать их поодиночке никто не
# будет — а гейт, который никто не гоняет, тихо краснеет и перестаёт защищать. Это не догадка:
# 22.07 гейт account-scope был красным неделю, 28.07 мой собственный гейт канона начал врать
# через несколько часов после написания, потому что правило сменилось, а проверка нет.
#
# Использование:
#   bash tools/run_all_gates.sh            # все самопроверки
#   bash tools/run_all_gates.sh --quiet    # только итог и провалы
#
# Коды выхода: 0 — все зелёные, 1 — есть провалившиеся.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUIET="${1:-}"
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

printf "\n\033[1mСамопроверки стандартов Extella\033[0m\n"

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
run build_agent_cabinet
run build_automation_cabinet
run build_capability_registry

printf "\n\033[1mИТОГ:\033[0m "
if [ -z "$FAILED" ]; then
  echo "зелёных $OK, провалов нет"
  exit 0
fi
echo "зелёных $OK, ПРОВАЛИЛИСЬ:$FAILED"
exit 1

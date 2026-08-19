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
    # Печатаем ХВОСТ вывода, а не только строки со словом FAIL. Прежний фильтр
    # ловил английские отчёты unittest и молча прятал русские: в прогоне на чистой
    # машине гейт падал, а причины не было видно вообще (замер 16.08.2026).
    if [ -z "$out" ]; then
      echo "      (гейт не сказал ни слова — смотри его код выхода)"
    else
      echo "$out" | tail -12 | sed 's/^/      /'
    fi
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
run check_writing_style
run check_waiting_state
run check_self_check
# Не только селфтест: прогоняем правило языка по СВОИМ текстам. Проверка, которая
# умеет падать, но ни к чему не применена, ничего не охраняет.
# ── ПРОВЕРКИ САМОГО КАНОНА ────────────────────────────────────────────────────
# Всё, что выше, спрашивает у гейта «исправна ли ты» (--selftest). Это не то же
# самое, что «канон в порядке». Замер 19.08.2026: при 35 зелёных селфтестах три
# гейта, запущенные ПО-НАСТОЯЩЕМУ, отвечали провалом — расхождение правила по
# дизайну и разъехавшиеся копии обвязки у двух живых продуктов. Полгода зелёного
# статуса ничего про канон не говорили.
# Встроенный снимок содержимого в странице гида. Она обязана рисоваться без сети,
# поэтому несёт копию текста внутри себя — и эта копия отстаёт молча. Замер
# 19.08.2026: content.json обновили до 2026-08-19.1, страница осталась на
# 2026-08-18.1, и поймал это ЧУЖОЙ бот в заявке, а не наш прогон. Проверка
# существовала (build.py --check), но её никто не звал.
run maintainers
run_command "снимок страницы гида" python3 "$ROOT/store_app/build.py" --check
run_command "правило по дизайну" python3 "$ROOT/tools/check_design_rule.py"
run_command "единственный источник" python3 "$ROOT/tools/check_single_source.py"
run_command "журнал находок" python3 "$ROOT/tools/check_findings_log.py"
run_command "копии манифестов" python3 "$ROOT/tools/check_manifest_copies.py"
run_command "копии экрана выбора агента" python3 "$ROOT/tools/check_onboarding_copies.py"
run_command "копии обвязки платформы" python3 "$ROOT/tools/check_platform_client_copies.py"

run_command "язык текстов для покупателя" python3 "$ROOT/tools/check_writing_style.py" \
  "$ROOT/README.md" "$ROOT/WRITING_RULES.md" "$ROOT/store_app/content.json"
run_command "язык инженерных записей" python3 "$ROOT/tools/check_writing_style.py" \
  --без-местоимений "$ROOT/DEPLOY_REQUIREMENTS.md" "$ROOT/AGENT_BUILD_GUIDE.md"
run check_design_rule
run check_findings_log
run check_agent_drift
run register_new_agents
run check_agent_repo
run check_manifest_copies
run check_surface_classes
run check_app_scopes
run check_listing_meta
run platform_client
# Инструменты чата Доски схем: самопроверки у них есть, а в общем прогоне их не было —
# то есть на чистой машине их никто не охранял. Гейт защищает только то, что включено.
run check_local_app
run cut_outbound
run collect_licenses
run deploy_page_product
run set_published
run inject_probe
run make_icon
run build_agent_cabinet
run build_automation_cabinet
run build_capability_registry
# СНЯТО 14.08.2026: этот гейт искал файл по абсолютному пути ВНЕ репозитория
# (рабочая копия автора), поэтому был зелёным ровно на одной машине и падал
# стеком у всех остальных. Проверка, зелёная только у автора, создаёт ложную
# уверенность и приучает пролистывать красное. Вернуть — когда источник будет
# внутри репозитория или гейт научится честно говорить «источника нет».
# run_command store_product_expert node "$ROOT/store_app/product/build_expert.mjs" --check
run_command store_page_contract node "$ROOT/store_app/test_page_contract.mjs"
run_command store_product python3 "$ROOT/store_app/product/test_product.py"

printf "\n\033[1mИТОГ:\033[0m "
if [ -z "$FAILED" ]; then
  echo "зелёных $OK, провалов нет"
  exit 0
fi
echo "зелёных $OK, ПРОВАЛИЛИСЬ:$FAILED"
exit 1

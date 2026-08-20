#!/bin/bash
# Стенд покупателя: чистая установка продукта в одноразовом контейнере.
#
# ЗАЧЕМ. Поломки «у пользователя не работает» не ловятся на машине автора по
# построению: у автора всё стоит, у покупателя — ничего. Стенд делает ровно то,
# что сделает покупатель: чистая машина, покупка, установка, первый запуск,
# самопроверка. Контейнер после прогона уничтожается — следующий прогон снова
# с нуля.
#
# ГДЕ ЖИВЁТ. VPS PS.kz (общая машина): прод-службы снаружи контейнера и не
# затрагиваются. Контейнер LXD, образ ubuntu:24.04.
#
# Имена переменных ЛАТИНИЦЕЙ: bash не принимает кириллические имена — трижды
# проверено на этой неделе (сорванный heredoc, папка «$Р», command not found).
#
#   bash bench_runner.sh <version_id> [--keep]
#     version_id — версия листинга, которую покупает и ставит стенд
#     --keep     — не удалять контейнер после прогона (для разбора руками)
#
# Коды выхода: 0 — продукт готов, 1 — не готов (см. отчёт), 2 — стенд не смог.
set -u

VID="${1:-}"
KEEP="${2:-}"
[ -z "$VID" ] && { echo "нужен version_id: bash bench_runner.sh <vid>"; exit 2; }

STAMP="$(date +%Y%m%d-%H%M%S)"
BOX="bench-$STAMP"
REPORT_DIR="$HOME/extella-bench/runs/$STAMP"
mkdir -p "$REPORT_DIR"

say() { printf '%s\n' "$*" | tee -a "$REPORT_DIR/протокол.txt"; }
fail() { say "СТЕНД НЕ СМОГ: $*"; [ "$KEEP" = "--keep" ] || lxc delete -f "$BOX" 2>/dev/null; exit 2; }

say "стенд: прогон $STAMP, версия $VID"

# ── 1. Чистая коробка ────────────────────────────────────────────────────────
lxc launch ubuntu:24.04 "$BOX" >/dev/null 2>&1 || fail "контейнер не создался"
# Ждём сеть внутри: без этого pip ниже молча зависает.
for i in $(seq 1 30); do
  lxc exec "$BOX" -- sh -c 'ping -c1 -W2 8.8.8.8 >/dev/null 2>&1' && break
  sleep 2
  [ "$i" = 30 ] && fail "в контейнере нет сети"
done
say "  1. контейнер поднят, сеть есть"

# ── 2. То, что есть у любого покупателя: python и pip ────────────────────────
lxc exec "$BOX" -- sh -c 'apt-get update -q && apt-get install -qy python3 python3-pip python3-venv >/dev/null' \
  || fail "python в контейнере не поставился"
say "  2. python3 на месте: $(lxc exec "$BOX" -- python3 --version)"

# ── 3. Листенер Extella под СТЕНДОВЫМ аккаунтом ─────────────────────────────
# Токен стенда лежит на хосте отдельным файлом и в репозиторий не попадает.
# Прод-токен НЕ используется: стендовые таргеты и покупки не должны мешаться
# с живыми (класс «задачи коллег ушли на машину Анвара»).
TOKEN_FILE="$HOME/extella-bench/bench_token.txt"
[ -f "$TOKEN_FILE" ] || fail "нет $TOKEN_FILE — положи токен стендового аккаунта (0600)"
lxc file push "$TOKEN_FILE" "$BOX/root/.extella_token" 2>/dev/null || fail "токен не проброшен"

# Способ установки листенера снимается с прод-машины при развёртывании стенда
# (pip show extella-listener → откуда). До этого шаг честно не работает.
LISTENER_INDEX_FILE="$HOME/extella-bench/listener_index_url.txt"
[ -f "$LISTENER_INDEX_FILE" ] || fail "нет $LISTENER_INDEX_FILE — сними индекс с прод-машины: pip3 config list или pip3 show -f extella-listener"
LISTENER_INDEX="$(cat "$LISTENER_INDEX_FILE")"
lxc exec "$BOX" -- sh -c "pip3 install --break-system-packages -q --index-url '$LISTENER_INDEX' extella-listener" \
  || fail "листенер не поставился из $LISTENER_INDEX"
say "  3. листенер установлен"

# ── 4–7. Регистрация таргета, покупка, установка, самопроверка ──────────────
# Исполняются скриптом внутри коробки: там питон, тут только оркестровка.
lxc file push "$(dirname "$0")/bench_inside.py" "$BOX/root/bench_inside.py" \
  || fail "bench_inside.py не проброшен"
lxc exec "$BOX" -- python3 /root/bench_inside.py "$VID" | tee -a "$REPORT_DIR/протокол.txt"
RC=${PIPESTATUS[0]}

# ── 8. Забрать протокол самопроверки, если продукт его оставил ──────────────
lxc file pull "$BOX/root/selfcheck.json" "$REPORT_DIR/selfcheck.json" 2>/dev/null \
  && say "  протокол самопроверки сохранён: $REPORT_DIR/selfcheck.json"

if [ "$KEEP" = "--keep" ]; then
  say "  контейнер $BOX ОСТАВЛЕН для разбора (lxc exec $BOX -- bash)"
else
  lxc delete -f "$BOX" 2>/dev/null
  say "  контейнер уничтожен: следующий прогон снова с нуля"
fi

say "итог: $([ "$RC" = 0 ] && echo 'ПРОДУКТ ГОТОВ' || echo "НЕ ГОТОВ (код $RC)") · отчёт: $REPORT_DIR"
exit "$RC"

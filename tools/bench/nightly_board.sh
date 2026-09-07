#!/bin/bash
# Ночной прогон доски-каталога: открыть каждое наше публичное приложение как
# посторонний и свести в таблицу. Ставится в cron рядом с канарейкой.
#
#   0 3 * * * /home/ubuntu/extella-bench/nightly_board.sh
#
# Идёт последовательно, по одному Chrome за раз (параллель клала VPS) — на 21
# приложение уходит ~30 минут. Список apps.json обновляется с машины владельца,
# когда меняется состав публичных продуктов: на стенде токена аккаунта владельца
# нет, сам список он не соберёт.
#
# Имена латиницей: cron бывает с локалью POSIX.
set -u
cd /home/ubuntu/extella-bench || exit 2
TS="$(date -u +%Y%m%d-%H%M)"
LOG="board_${TS}.log"

/usr/bin/python3 catalog_board.py --apps apps.json --pause 6 \
  --out board_latest.json > "$LOG" 2>&1
CODE=$?

# Короткая сводка первой строкой лога — чтобы глянуть grep-ом «итог:».
tail -3 "$LOG" | grep -E "итог:" >> board_history.log 2>/dev/null || true
sed -i "1i # прогон $TS UTC, код выхода $CODE" "$LOG"

# Держим последние 14 логов, старые убираем.
ls -1t board_*.log 2>/dev/null | tail -n +15 | xargs -r rm -f
exit "$CODE"

#!/usr/bin/env bash
# Установщик стенда приёмки одной командой.
#
#   curl -fsSL https://files.82-115-42-21.sslip.io/bench/install.sh | \
#     EXTELLA_TOKEN=<токен из панели Extella> bash
#
# На чистой Linux-машине ставит настоящий Chrome (не snap — снап не бежит из
# systemd), скрипты стенда, службу и (по умолчанию) открывает наружу через
# caddy с авто-TLS на <ip>.sslip.io. После этого кнопка «откроется ли у других»
# может гонять приёмку на ЭТОМ стенде. Стенд твой: токен и код остаются у тебя.
#
# Переменные:
#   EXTELLA_TOKEN         — обязателен, токен твоего аккаунта Extella.
#   EXTELLA_BENCH_PUBLIC  — 1 (по умолчанию) открыть наружу; 0 только локально.
#   EXTELLA_BENCH_BASE    — откуда качать скрипты (по умолчанию наш файл-сервер).
#
# Имена переменных латиницей: bash не принимает кириллицу в идентификаторах.
set -euo pipefail

BASE="${EXTELLA_BENCH_BASE:-https://files.82-115-42-21.sslip.io/bench}"
PUBLIC="${EXTELLA_BENCH_PUBLIC:-1}"
DIR="$HOME/extella-bench"

log(){ printf '  · %s\n' "$*"; }
die(){ printf 'СТЕНД НЕ ПОДНЯЛСЯ: %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
# env-префикс, а не инлайновое VAR=val: при пустом $SUDO (root) присваивание
# перед командой ломается («command not found»).
# NEEDRESTART_MODE=a: на Ubuntu 24.04 пост-триггер needrestart ждёт tty и виснет
# в контейнере/по ssh — без этого установка Chrome не завершается.
apt_get(){ $SUDO env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a \
             NEEDRESTART_SUSPEND=1 apt-get "$@"; }
[ -n "${EXTELLA_TOKEN:-}" ] || die "нужен EXTELLA_TOKEN — токен из панели Extella"

# needrestart на Ubuntu 24.04 виснет по ssh/в контейнере. Хук прописан в ДВУХ
# местах — apt (99needrestart) и dpkg (dpkg.cfg.d/needrestart); убираем оба.
$SUDO rm -f /etc/apt/apt.conf.d/99needrestart \
            /etc/dpkg/dpkg.cfg.d/needrestart 2>/dev/null || true

log "зависимости: python3, curl, библиотеки браузера…"
apt_get update -q >/dev/null
# man-db-триггер пересобирает индекс man-страниц и надолго виснет в контейнере
# (состояние D). Стенду man-страницы не нужны — сносим триггер целиком.
apt_get purge -y man-db >/dev/null 2>&1 || true
# Chrome — как standalone «Chrome for Testing» (без .deb: postinst .deb виснет в
# контейнере). Ставим только его рантайм-библиотеки, сам браузер — распаковкой.
# дождаться освобождения apt-замка (на свежей машине cloud-init/автообновления)
for i in $(seq 1 60); do $SUDO fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break; sleep 3; done
apt_get install -qy --no-install-recommends python3 curl ca-certificates openssl unzip \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
  libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
  libpango-1.0-0 libcairo2 libatspi2.0-0 libxext6 libxi6 libx11-6 libxcb1 \
  libxshmfence1 fonts-liberation >/dev/null 2>&1 || true
# libasound меняет имя между 22.04/24.04 — ставим что есть.
apt_get install -qy libasound2t64 >/dev/null 2>&1 || \
  apt_get install -qy libasound2 >/dev/null 2>&1 || true

if [ ! -x "$DIR/chrome/chrome" ]; then
  mkdir -p "$DIR/chrome"
  URL="$(curl -fsSL https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
    | python3 -c 'import sys,json;d=json.load(sys.stdin);print([x["url"] for x in d["channels"]["Stable"]["downloads"]["chrome"] if x["platform"]=="linux64"][0])')"
  [ -n "$URL" ] || die "не нашёл ссылку на Chrome for Testing"
  curl -fsSL -o /tmp/cft.zip "$URL" || die "Chrome не скачался"
  rm -rf /tmp/cft && unzip -q -o /tmp/cft.zip -d /tmp/cft
  cp -a /tmp/cft/chrome-linux64/. "$DIR/chrome/"
  rm -rf /tmp/cft.zip /tmp/cft
fi
log "браузер: $("$DIR/chrome/chrome" --version 2>/dev/null || echo '?')"

log "скрипты стенда → $DIR"
mkdir -p "$DIR/runs"
for f in probe_window.py same_origin_probe.py check_opens_elsewhere.py \
         priemka_service.py panel_priemka.html; do
  curl -fsSL -o "$DIR/$f" "$BASE/$f" || die "не скачался $f"
done

printf '%s' "$EXTELLA_TOKEN" > "$DIR/bench_token.txt"; chmod 600 "$DIR/bench_token.txt"
[ -f "$DIR/bench_service_key.txt" ] || \
  { openssl rand -hex 24 > "$DIR/bench_service_key.txt"; chmod 600 "$DIR/bench_service_key.txt"; }
[ -f "$DIR/bench_panel_slug.txt" ] || \
  { openssl rand -hex 16 > "$DIR/bench_panel_slug.txt"; chmod 600 "$DIR/bench_panel_slug.txt"; }

log "служба extella-priemka…"
$SUDO tee /etc/systemd/system/extella-priemka.service >/dev/null <<UNIT
[Unit]
Description=Extella priemka bench service
After=network.target
[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/priemka_service.py
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now extella-priemka >/dev/null 2>&1 || die "служба не включилась"
sleep 2
curl -fsS --max-time 8 http://127.0.0.1:8799/health >/dev/null || die "служба не отвечает на /health"
log "служба жива (127.0.0.1:8799)"

SLUG="$(cat "$DIR/bench_panel_slug.txt")"
if [ "$PUBLIC" = "1" ]; then
  log "открываю наружу через caddy (авто-TLS)…"
  if ! command -v caddy >/dev/null 2>&1; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
      $SUDO gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | \
      $SUDO tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt_get update -q >/dev/null && apt_get install -qy caddy >/dev/null
  fi
  IP="$(curl -fsSL --max-time 10 https://api.ipify.org)"
  DOMAIN="priemka.${IP//./-}.sslip.io"
  $SUDO mkdir -p /etc/caddy/conf.d
  grep -q 'import conf.d' /etc/caddy/Caddyfile 2>/dev/null || \
    echo 'import conf.d/*.caddy' | $SUDO tee -a /etc/caddy/Caddyfile >/dev/null
  printf '%s {\n\treverse_proxy 127.0.0.1:8799\n}\n' "$DOMAIN" | \
    $SUDO tee /etc/caddy/conf.d/priemka.caddy >/dev/null
  $SUDO systemctl reload caddy 2>/dev/null || $SUDO systemctl restart caddy

  # Кнопка находит свой стенд: кладём в аккаунт пользователя ярлык на ЭТОТ стенд.
  # Идемпотентно — если ярлык на этот же стенд уже есть, не плодим второй.
  log "ярлык на рабочий стол OS…"
  PANEL="https://$DOMAIN/u/$SLUG/"
  python3 - "$EXTELLA_TOKEN" "$PANEL" "https://$DOMAIN" <<'PY' || \
    echo "  (ярлык не создан — можно добавить вручную по адресу ниже)"
import sys, json, urllib.request, urllib.error
T, URL, HOST = sys.argv[1], sys.argv[2], sys.argv[3]
def api(method, path, body=None):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://os.extella.ai" + path, data=d, method=method,
                               headers={"X-Extella-Token": T, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=30).read() or b"{}")
items = api("GET", "/api/desktop/items")
if any(HOST in (s.get("url") or "") for s in items.get("shortcuts", [])):
    print("  ярлык на этот стенд уже есть — оставляю")
else:
    api("POST", "/api/desktop/shortcut",
        {"name": "Приёмка: откроется ли у других", "url": URL, "folder": ""})
    print("  ярлык добавлен на рабочий стол OS")
PY

  echo
  echo "СТЕНД ГОТОВ. Кнопка «Приёмка: откроется ли у других» на твоём столе OS."
  echo "Прямой адрес (на всякий): $PANEL"
  echo "Первый заход может подождать выдачу TLS-сертификата (до минуты)."
else
  echo
  echo "СТЕНД ГОТОВ локально (без публичного адреса)."
  echo "  панель: http://127.0.0.1:8799/u/$SLUG/"
fi

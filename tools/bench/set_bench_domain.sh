#!/usr/bin/env bash
# Переезд стенда на нормальный домен (вместо *.sslip.io).
#
#   bash set_bench_domain.sh priemka.example.com
#
# ЗАЧЕМ. ОС режет хосты вида *.sslip.io и *.nip.io целым классом: эти сервисы
# кодируют адрес в имени и умеют указывать внутрь (замер 23.08.2026:
# 127.0.0.1.sslip.io → 127.0.0.1, 192.168.1.1.sslip.io → 192.168.1.1), то есть
# служат обходом защиты от запросов во внутреннюю сеть. Отличить безопасное имя
# от опасного нельзя, поэтому режется всё семейство — и приложение из витрины
# получает «Blocked host (internal address)», даже если адрес публичный.
#
# ПЕРЕД ЗАПУСКОМ. У регистратора завести запись A: <поддомен> → 82.115.42.21.
# Проверить: dig +short <поддомен> отдаёт этот адрес.
#
# Имена переменных латиницей: bash не принимает кириллицу в идентификаторах.
set -eu

HOST="${1:-}"
[ -n "$HOST" ] || { echo "как звать: bash set_bench_domain.sh <поддомен>"; exit 2; }
case "$HOST" in
  *sslip.io|*nip.io) echo "СТОП: это снова кодирующий адрес сервис, ОС его режет"; exit 2;;
esac

IP="$(curl -fsSL --max-time 10 https://api.ipify.org)"
РЕАЛ="$(dig +short "$HOST" | tail -1)"
if [ "$РЕАЛ" != "$IP" ]; then
  echo "СТОП: $HOST указывает на «$РЕАЛ», а стенд живёт на $IP."
  echo "Заведи запись A: $HOST → $IP и подожди распространения DNS."
  exit 1
fi

sudo tee /etc/caddy/conf.d/priemka.caddy >/dev/null <<CADDY
$HOST {
	encode gzip
	reverse_proxy 127.0.0.1:8799
}
CADDY
sudo systemctl reload caddy
sleep 3
код="$(curl -s -o /dev/null -w '%{http_code}' --max-time 45 "https://$HOST/health" || true)"
echo "проверка https://$HOST/health → $код (первый заход ждёт выдачи сертификата)"

СЛАГ="$(cat "$HOME/extella-bench/bench_panel_slug.txt")"
echo
echo "Новый адрес кнопки приёмки:"
echo "  https://$HOST/u/$СЛАГ/"
echo "Старый ярлык на *.sslip.io нужно заменить: ОС такие хосты больше не пускает."

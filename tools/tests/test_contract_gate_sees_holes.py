#!/usr/bin/env python3
"""Гейт договора обязан ОДНОВРЕМЕННО видеть дыру и не выдумывать её.

ЗАЧЕМ ЭТОТ ТЕСТ. 02.08 гейт ложно обвинил живые маршруты Баги, а первая правка его
ослепила: подставной /api/zzz-does-not-exist он назвал живым. Слепой гейт опаснее
крикливого: крикливый раздражает, слепой молча пропускает релиз. Обе стороны
закреплены здесь.

ПОЧЕМУ БЕЗ ЖИВОГО СЕРВЕРА. 03.08 ловушка по User-Agent доказала: живой пробник гейта
САМ ИСПОЛНЯЛ обработчики — POST {} в nego_start запускал настоящую арену переговоров,
в send_email слал настоящее письмо, и «загадочные волны фоновой работы» на машине
владельца оказались прогонами гейта из preflight. Гейт не имеет права трогать прод,
который проверяет: существование маршрута теперь читается из ИСХОДНИКА сервера, и
тест закрепляет ровно эту механику — плюс запрет на любые сетевые звонки по маршрутам.

Запуск: python3 tools/tests/test_contract_gate_sees_holes.py
Коды выхода: 0 — гейт различает оба случая и честен на нераспознанной поверхности.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "check_ui_api_contract.py"

LIVE = "/api/live-route"      # объявлен в исходнике сервера
HOLE = "/api/no-such-route"   # интерфейс зовёт, сервер про него не знает


def run_gate(server_src, calls):
    d = Path(tempfile.mkdtemp())
    (d / "web").mkdir()
    body = "".join(f'fetch("{c}", {{method:"POST"}});\n' for c in calls)
    (d / "web" / "index.html").write_text(f"<html><script>{body}</script></html>", encoding="utf-8")
    (d / "server.py").write_text(server_src, encoding="utf-8")
    # Порт передаём НАРОЧНО: даже с известным портом гейт не должен звонить —
    # если по нему кто-то слушает, это чужой сервер, и трогать его нельзя.
    r = subprocess.run([sys.executable, str(GATE), str(d), "1"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr


SERVER = 'ROUTES = {"%s": None}\n' % LIVE

# Поверхность, собранная кодом: ни одного literal-маршрута — статике не видно ничего.
SERVER_DYNAMIC = 'PREFIX = "/ap" + "i/"\nROUTES = {PREFIX + n: None for n in ("live-route", "x")}\n'


def main() -> int:
    failures = []

    out = run_gate(SERVER, [LIVE])
    if "✗" in out:
        failures.append("ЛОЖНОЕ ОБВИНЕНИЕ: маршрут, объявленный в исходнике сервера, "
                        "назван отсутствующим:\n" + out)

    out = run_gate(SERVER, [LIVE, HOLE])
    if HOLE not in out or "✗" not in out:
        failures.append("СЛЕПОТА: интерфейс зовёт маршрут, которого нет в исходниках "
                        "сервера, а гейт молчит — пустой экран уехал бы в релиз:\n" + out)
    elif LIVE in out.split("✗", 1)[-1].split("\n", 1)[0]:
        failures.append("вместе: гейт не указал ровно на дыру:\n" + out)

    out = run_gate(SERVER_DYNAMIC, [LIVE, HOLE])
    if "не распознал" not in out and "не сверял" not in out:
        failures.append("на поверхности, собранной кодом, гейт обязан честно сказать "
                        "«не распознал», а не краснеть и не молчать:\n" + out)

    for f in failures:
        print(f"  ✗ {f}")
    if failures:
        print("\nГЕЙТ ДОГОВОРА НЕИСПРАВЕН.")
        return 1
    print("  ✓ гейт видит дыру, не выдумывает её и честен на нераспознанной поверхности")
    return 0


if __name__ == "__main__":
    sys.exit(main())

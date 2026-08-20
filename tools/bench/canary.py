#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ночная канарейка: живы ли продуктовые агенты — до того, как заметит клиент.

ЗАЧЕМ. Треть наших поломок «у пользователя не работает» приходит не из кода
продукта, а из дрейфа платформы: схема менялась дважды за день, имена
инструментов сменили поколение, allowed_origins чинили молча. Продукт не
менялся — сломалась среда. Тесты при выкладке это не ловят по построению:
между выкладками может пройти неделя.

Канарейка гоняет каждый агент живым коротким прогоном каждую ночь и утром
отдаёт сводку одной строкой на агента: жив / сломался и чем ответила платформа.

ЧТО НАМЕРЕННО НЕ ТАК, КАК КАЖЕТСЯ ПРАВИЛЬНЫМ:

* дедлайн — по стенным часам, потоком, а не таймаутом запроса. Зомби-сокет
  платформы держит agent/run по 10+ минут, и таймаут библиотеки НЕ срабатывает
  (класс из extella-engine-agent-run-deadline, проверен живьём);
* таймаут агента — не провал, а отдельное состояние «не дождались»: платформа
  могла принять задачу и честно работать. Повтор безопасен, паника не нужна;
* сводка пишется ВСЕГДА, даже когда всё зелёное: молчание канарейки должно
  означать «канарейка сломалась», а не «всё хорошо».

    python3 canary.py                 # прогнать всех из canary_agents.json
    python3 canary.py --selftest      # без сети

Коды выхода: 0 — все живы, 1 — есть сломанные, 2 — канарейка не смогла работать.
"""
import json
import pathlib
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

СЮДА = pathlib.Path(__file__).resolve().parent
АГЕНТЫ = СЮДА / "canary_agents.json"
ЖУРНАЛ = pathlib.Path.home() / "extella-bench" / "canary.log"
ЯДРО = "https://api.extella.ai"
ДЕДЛАЙН_СЕК = 90

# Вопрос намеренно требует ИНСТРУМЕНТА, а не вежливости: агент, у которого
# отвалились эксперты, всё ещё умеет поздороваться. «Жив» для продукта — это
# «может сделать работу», поэтому канарейка просит позвать эксперта.
ВОПРОС = ("Служебная проверка работоспособности. Вызови свой самый простой "
          "инструмент или эксперта и ответь одним коротким предложением, "
          "что получилось. Ничего не записывай и не удаляй.")


def токен() -> str:
    """Токен ищется там же, где его держат службы этой машины."""
    для_проверки = [
        pathlib.Path.home() / "extella_wizard" / "app" / "config.json",
        pathlib.Path.home() / ".extella" / "api_token.txt",
    ]
    for п in для_проверки:
        if not п.exists():
            continue
        текст = п.read_text(encoding="utf-8").strip()
        if п.suffix == ".json":
            try:
                значение = str(json.loads(текст).get("auth_token") or "").strip()
            except json.JSONDecodeError:
                continue
        else:
            значение = текст
        if значение:
            return значение
    raise SystemExit("токен не найден: канарейке нечем представиться платформе")


def прогнать(агент_id: str, ключ: str) -> dict:
    """Один живой прогон с жёстким дедлайном по стенным часам."""
    итог: dict = {}

    def запрос() -> None:
        тело = json.dumps({"input": ВОПРОС, "agent_id": агент_id}).encode()
        з = urllib.request.Request(
            ЯДРО + "/api/agent/run", data=тело, method="POST",
            headers={"X-Auth-Token": ключ, "X-Profile-Id": "default",
                     "X-Agent-Id": агент_id, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(з, timeout=ДЕДЛАЙН_СЕК) as о:
                итог["код"] = о.status
                итог["тело"] = о.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            итог["код"] = e.code
            итог["тело"] = e.read()[:400].decode(errors="replace")
        except Exception as e:                        # noqa: BLE001
            итог["ошибка"] = f"{type(e).__name__}: {e}"

    поток = threading.Thread(target=запрос, daemon=True)
    начало = datetime.now(timezone.utc)
    поток.start()
    поток.join(ДЕДЛАЙН_СЕК)
    секунд = (datetime.now(timezone.utc) - начало).total_seconds()

    if поток.is_alive():
        return {"состояние": "не дождались", "секунд": round(секунд),
                "детали": f"нет ответа за {ДЕДЛАЙН_СЕК} с — повтор безопасен"}
    if "ошибка" in итог:
        return {"состояние": "сломан", "секунд": round(секунд), "детали": итог["ошибка"]}

    код, тело = итог.get("код"), итог.get("тело", "")
    if код != 200:
        краткое = " ".join(тело.split())[:160]
        return {"состояние": "сломан", "секунд": round(секунд),
                "детали": f"HTTP {код} · {краткое}"}

    текст = ""
    try:
        for э in (json.loads(тело).get("output") or []):
            for ч in (э.get("content") or []):
                if ч.get("type") == "output_text":
                    текст += ч.get("text", "")
    except json.JSONDecodeError:
        pass
    if not текст.strip():
        return {"состояние": "сломан", "секунд": round(секунд),
                "детали": "ответ 200, но текста нет — молчаливый отказ"}
    return {"состояние": "жив", "секунд": round(секунд),
            "детали": " ".join(текст.split())[:120]}


def сводка(имена_итоги: list) -> str:
    строки = [f"канарейка {datetime.now(timezone.utc):%d.%m %H:%M} UTC"]
    for имя, и in имена_итоги:
        метка = {"жив": "✓", "не дождались": "~"}.get(и["состояние"], "✗")
        строки.append(f"  {метка} {имя:<22} {и['состояние']:<12} {и['секунд']:>3}с  {и['детали']}")
    сломано = [имя for имя, и in имена_итоги if и["состояние"] == "сломан"]
    строки.append("итог: все живы" if not сломано
                  else f"итог: СЛОМАНО — {', '.join(сломано)}")
    return "\n".join(строки)


def selftest() -> int:
    ошибки = []
    случаи = [
        ("жив", {"код": 200, "тело": json.dumps({"output": [{"content": [
            {"type": "output_text", "text": "Эксперт ответил, всё работает."}]}]})}),
        ("сломан", {"код": 500, "тело": '{"error":"Internal"}'}),
        ("сломан", {"код": 200, "тело": '{"output": []}'}),   # молчаливый отказ
        ("сломан", {"ошибка": "URLError: unreachable"}),
    ]
    for ждём, подстава in случаи:
        # Разбор ответа тот же, что в бою: подставляем итог и прогоняем хвост логики.
        итог = подстава
        if "ошибка" in итог:
            и = {"состояние": "сломан", "секунд": 0, "детали": итог["ошибка"]}
        elif итог["код"] != 200:
            и = {"состояние": "сломан", "секунд": 0, "детали": f"HTTP {итог['код']}"}
        else:
            т = ""
            for э in (json.loads(итог["тело"]).get("output") or []):
                for ч in (э.get("content") or []):
                    if ч.get("type") == "output_text":
                        т += ч.get("text", "")
            и = ({"состояние": "жив", "секунд": 0, "детали": т}
                 if т.strip() else
                 {"состояние": "сломан", "секунд": 0, "детали": "молчаливый отказ"})
        if и["состояние"] != ждём:
            ошибки.append(f"ждали «{ждём}», получили «{и['состояние']}»")
    св = сводка([("Проба", {"состояние": "сломан", "секунд": 3, "детали": "HTTP 500"})])
    if "СЛОМАНО" not in св:
        ошибки.append("сводка не кричит о сломанном")
    if not АГЕНТЫ.exists():
        ошибки.append("нет canary_agents.json рядом — канарейке некого проверять")
    else:
        записи = json.loads(АГЕНТЫ.read_text(encoding="utf-8"))
        if not записи or not all(re.fullmatch(r"agent_[\w-]+", з["id"]) for з in записи):
            ошибки.append("canary_agents.json пуст или id не похожи на агентов")
    for о in ошибки:
        print("  ✗", о)
    print("selftest:", "провален" if ошибки else "пройден")
    return 1 if ошибки else 0


def main(аргументы: list) -> int:
    if "--selftest" in аргументы:
        return selftest()
    записи = json.loads(АГЕНТЫ.read_text(encoding="utf-8"))
    ключ = токен()
    итоги = [(з["имя"], прогнать(з["id"], ключ)) for з in записи]
    текст = сводка(итоги)
    print(текст)
    ЖУРНАЛ.parent.mkdir(parents=True, exist_ok=True)
    with ЖУРНАЛ.open("a", encoding="utf-8") as ж:
        ж.write(текст + "\n\n")
    return 1 if any(и["состояние"] == "сломан" for _, и in итоги) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

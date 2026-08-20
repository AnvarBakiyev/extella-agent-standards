#!/usr/bin/env python3
"""Локальная модель как ИНСТРУМЕНТ агента — MCP-сервер поверх LM Studio.

ЗАЧЕМ ИМЕННО ТАК. Локальную модель можно подключить двумя способами, и они
решают разные задачи.

  llm_base_url в конфиге листенера — мозгом агента становится локальная модель.
  Всё или ничего: агент дешевеет и одновременно тупеет во всём, включая
  рассуждения, где нужна голова.

  Этот сервер — агент остаётся на сильной модели, а локальную зовёт
  ИНСТРУМЕНТОМ, когда сам решит. Тысяча однотипных классификаций уходит вниз,
  рассуждение остаётся наверху. Тот же приём, что у мостов Claude и Codex:
  делегировать другому движку, а не подменять себя им.

Замеры 20.08.2026 на 32 ГБ Mac (gemma-2-9b): классификация 1.2 с, извлечение
поля 1.6 с, маршрутизация 0.7 с. Та же задача на рассуждающей qwen3.8-27b —
47 секунд. Поэтому инструменты здесь узкие: они для потока, а не для раздумий.

ТОКЕН НЕ НУЖЕН. Сервер ходит только на 127.0.0.1 и не знает ни об Extella, ни
об аккаунте. Секрета в его конфиге нет, поэтому и утечь нечему.

    python3 tools/local_model_mcp.py --selftest     # протокол, без модели
    python3 tools/local_model_mcp.py --проверить    # живой вызов модели
    python3 tools/local_model_mcp.py                # сам сервер, stdio

Подключение: добавить в ~/.extella_mcp/allowlist.json командой
    python3 tools/local_model_mcp.py --подключить
"""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

СЕРВЕР = os.environ.get("EXTELLA_LOCAL_MODEL_URL", "http://127.0.0.1:1234/v1")
ИМЯ = "extella_local_model"
ВЕРСИЯ = "1.0.0"
# Потолок ответа: инструмент для потока, а не для сочинений. Длинный ответ
# означает, что задачу выбрали неправильно — её надо было решать наверху.
ПОТОЛОК = 400


def _модель() -> str:
    """Имя первой загруженной модели. Спрашиваем сервер, а не угадываем: имя
    меняется вместе с тем, что человек загрузил в LM Studio."""
    with urllib.request.urlopen(СЕРВЕР + "/models", timeout=8) as ответ:
        данные = json.loads(ответ.read(65536).decode("utf-8"))
    модели = [str(m.get("id", "")) for m in данные.get("data", []) if m.get("id")]
    if not модели:
        raise RuntimeError("в LM Studio не загружена ни одна модель")
    return модели[0]


def спросить(запрос: str, максимум: int = 200) -> str:
    """Один вызов локальной модели. Ошибки возвращаются словами, а не стеком:
    их прочитает агент, и они должны говорить, что делать."""
    тело = json.dumps({
        "model": _модель(),
        "messages": [{"role": "user", "content": запрос}],
        "max_tokens": max(1, min(int(максимум), ПОТОЛОК)),
        "temperature": 0,
    }).encode("utf-8")
    запрос_http = urllib.request.Request(
        СЕРВЕР + "/chat/completions", data=тело,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(запрос_http, timeout=180) as ответ:
        готово = json.loads(ответ.read(1 << 20).decode("utf-8"))
    выбор = (готово.get("choices") or [{}])[0]
    текст = str((выбор.get("message") or {}).get("content") or "").strip()
    if not текст:
        # Рассуждающая модель кладёт всё в размышления и до ответа не доходит.
        # Замер 19.08.2026: qwen3.8-27b на 30 токенах отвечала пустотой.
        причина = выбор.get("finish_reason")
        raise RuntimeError(
            "модель не дала ответа (finish_reason=" + str(причина) + "). "
            "Похоже, загружена рассуждающая модель: для потока нужна быстрая, "
            "например gemma-2-9b")
    return текст


ИНСТРУМЕНТЫ = [
    {
        "name": "local_classify",
        "description": ("Отнести текст к одной из заданных категорий локальной моделью. "
                        "Бесплатно, ответ за 1–2 секунды, текст не покидает компьютер. "
                        "Для потока однотипных задач: тональность, тип обращения, рубрика."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст, который надо отнести к категории"},
                "categories": {"type": "array", "items": {"type": "string"},
                               "description": "Список категорий, из которых выбрать ровно одну"},
            },
            "required": ["text", "categories"],
        },
    },
    {
        "name": "local_extract",
        "description": ("Извлечь одно поле из текста локальной моделью: телефон, дату, сумму, имя. "
                        "Бесплатно, ответ за 1–2 секунды, текст не покидает компьютер."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст, из которого извлекают"},
                "field": {"type": "string", "description": "Что именно извлечь, словами"},
            },
            "required": ["text", "field"],
        },
    },
    {
        "name": "local_ask",
        "description": ("Задать локальной модели короткий вопрос. Бесплатно и приватно, но "
                        "модель слабее платформенной: для рассуждений и длинных ответов "
                        "используй свою обычную модель, а не этот инструмент."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Вопрос или задание"},
                "max_tokens": {"type": "integer",
                               "description": f"Потолок ответа, не больше {ПОТОЛОК}"},
            },
            "required": ["prompt"],
        },
    },
]


def выполнить(имя: str, аргументы: dict) -> str:
    if имя == "local_classify":
        категории = [str(k) for k in (аргументы.get("categories") or []) if str(k).strip()]
        if not категории:
            raise RuntimeError("не заданы категории")
        ответ = спросить(
            "Отнеси текст ровно к одной категории из списка и ответь ТОЛЬКО названием "
            "категории, без пояснений.\nКатегории: " + ", ".join(категории) +
            "\nТекст: " + str(аргументы.get("text") or ""), 40)
        # Приводим к заданному списку: модель любит добавить точку или падеж.
        низ = ответ.strip().strip(".!\"'").lower()
        for к in категории:
            if к.lower() == низ or к.lower() in низ:
                return к
        return ответ
    if имя == "local_extract":
        return спросить(
            "Извлеки из текста только то, что просят, и ответь ТОЛЬКО этим значением, "
            "без пояснений. Если этого в тексте нет, ответь: нет.\nЧто извлечь: " +
            str(аргументы.get("field") or "") + "\nТекст: " + str(аргументы.get("text") or ""), 80)
    if имя == "local_ask":
        return спросить(str(аргументы.get("prompt") or ""),
                        int(аргументы.get("max_tokens") or 200))
    raise RuntimeError(f"неизвестный инструмент: {имя}")


# ── Протокол MCP поверх stdio: JSON-RPC 2.0 ────────────────────────────────────

def _ответ(идентификатор, результат=None, ошибка=None) -> dict:
    пакет = {"jsonrpc": "2.0", "id": идентификатор}
    if ошибка is not None:
        пакет["error"] = ошибка
    else:
        пакет["result"] = результат
    return пакет


def обработать(пакет: dict):
    """Один запрос → один ответ. None означает уведомление: на него не отвечают."""
    метод = пакет.get("method")
    идентификатор = пакет.get("id")
    if метод == "initialize":
        return _ответ(идентификатор, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": ИМЯ, "version": ВЕРСИЯ},
        })
    if метод in ("notifications/initialized", "initialized"):
        return None
    if метод == "tools/list":
        return _ответ(идентификатор, {"tools": ИНСТРУМЕНТЫ})
    if метод == "tools/call":
        параметры = пакет.get("params") or {}
        try:
            текст = выполнить(str(параметры.get("name") or ""), параметры.get("arguments") or {})
            return _ответ(идентификатор, {"content": [{"type": "text", "text": текст}]})
        except urllib.error.URLError:
            # Отказ обязан называть следующий шаг, а не только проблему.
            return _ответ(идентификатор, {"content": [{"type": "text", "text":
                "Локальная модель недоступна. Откройте LM Studio и загрузите модель "
                "(или выполните: lms server start), затем повторите."}], "isError": True})
        except Exception as сбой:
            return _ответ(идентификатор, {"content": [{"type": "text",
                                                       "text": str(сбой)[:400]}], "isError": True})
    if идентификатор is None:
        return None
    return _ответ(идентификатор, ошибка={"code": -32601, "message": f"нет метода {метод}"})


def служить() -> int:
    """Строка на вход — строка на выход. Ошибка разбора не роняет сервер:
    клиент переживёт кривой пакет, а упавший сервер — нет."""
    for строка in sys.stdin:
        строка = строка.strip()
        if not строка:
            continue
        try:
            пакет = json.loads(строка)
        except Exception:
            continue
        ответ = обработать(пакет)
        if ответ is not None:
            sys.stdout.write(json.dumps(ответ, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def подключить() -> int:
    """Добавить себя в аллоулист внешних MCP Extella. Резервная копия рядом:
    аллоулист общий, и затирать чужие записи нельзя."""
    путь = pathlib.Path.home() / ".extella_mcp" / "allowlist.json"
    путь.parent.mkdir(parents=True, exist_ok=True)
    было = {}
    if путь.is_file():
        было = json.loads(путь.read_text(encoding="utf-8"))
        import time
        (путь.parent / f"allowlist.json.bak_{time.strftime('%Y%m%dT%H%M%S')}").write_text(
            json.dumps(было, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    было[ИМЯ] = {
        "cmd": [sys.executable, str(pathlib.Path(__file__).resolve())],
        "title": "Локальная модель — быстрый поток",
        "tools": [и["name"] for и in ИНСТРУМЕНТЫ],
    }
    путь.write_text(json.dumps(было, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"подключено: {ИМЯ} → {путь} (серверов в списке: {len(было)})")
    return 0


def проверить_живьём() -> int:
    """Настоящий вызов модели. Отдельно от селфтеста: гейт обязан проходить и
    там, где LM Studio не запущена."""
    try:
        имя = _модель()
    except Exception as сбой:
        print("модель недоступна:", str(сбой)[:200])
        return 1
    print("загружена модель:", имя)
    import time
    for инструмент, аргументы in (
        ("local_classify", {"text": "Доставка опоздала на три дня, но деньги вернули.",
                            "categories": ["позитив", "негатив", "нейтрально"]}),
        ("local_extract", {"text": "звоните на +7 708 605 4107 после обеда",
                           "field": "номер телефона"}),
    ):
        начало = time.time()
        ответ = выполнить(инструмент, аргументы)
        print(f"  {инструмент}: {ответ[:60]!r} за {time.time() - начало:.1f} с")
    return 0


def _selftest() -> int:
    ошибки = []
    начало = обработать({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    if (начало or {}).get("result", {}).get("serverInfo", {}).get("name") == ИМЯ:
        print("  ✓ initialize отвечает именем сервера")
    else:
        ошибки.append("initialize")
    if обработать({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None:
        print("  ✓ на уведомление ответа нет")
    else:
        ошибки.append("уведомление получило ответ")
    список = обработать({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    имена = [и["name"] for и in (список or {}).get("result", {}).get("tools", [])]
    if имена == [и["name"] for и in ИНСТРУМЕНТЫ]:
        print("  ✓ tools/list отдаёт", ", ".join(имена))
    else:
        ошибки.append("tools/list")
    # Каждый инструмент обязан объявить схему аргументов: без неё модель не
    # знает, что передавать, и инструмент бесполезен.
    for и in ИНСТРУМЕНТЫ:
        схема = и.get("inputSchema") or {}
        if схема.get("type") != "object" or not схема.get("required"):
            ошибки.append(f"{и['name']}: неполная схема")
    if not any("схема" in о for о in ошибки):
        print("  ✓ у каждого инструмента объявлена схема аргументов")
    # Неизвестный метод — честная ошибка, а не молчание.
    плохой = обработать({"jsonrpc": "2.0", "id": 3, "method": "такого/нет"})
    if (плохой or {}).get("error", {}).get("code") == -32601:
        print("  ✓ неизвестный метод отвечает ошибкой")
    else:
        ошибки.append("неизвестный метод")
    # Токена в сервере быть не должно вовсе.
    # Имена ищем склейкой: иначе проверка находит саму себя и краснеет на
    # исправном файле. Этот класс ошибки — совпадение проверки с собственным
    # текстом — попадался сегодня четырежды.
    текст = "\n".join(l for l in pathlib.Path(__file__).read_text(encoding="utf-8").split("\n")
                      if not l.lstrip().startswith("#"))
    запретные = ["X-Auth" + "-Token", "api" + "_token", "EXTELLA_API" + "_TOKEN"]
    if any(з in текст for з in запретные):
        ошибки.append("в сервере появился токен — он тут не нужен")
    else:
        print("  ✓ сервер не знает ни о токене, ни об аккаунте")
    if ошибки:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(ошибки))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--проверить" in sys.argv:
        sys.exit(проверить_живьём())
    if "--подключить" in sys.argv:
        sys.exit(подключить())
    sys.exit(служить())

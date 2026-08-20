#!/usr/bin/env python3
"""Выложить экспертов локальной модели и сверить записанное с файлом.

ЗАЧЕМ ОТДЕЛЬНЫМ ИНСТРУМЕНТОМ. MCP save_expert писать нельзя: он молча кладёт
эксперта в чужой скоуп (см. комментарий в experts/board_draw_form.py). Пишем
REST-ом на ядро и ПОСЛЕ записи перечитываем: три раза за месяц запись проходила,
а содержимое отличалось от файла.

    python3 tools/deploy_local_model_experts.py            # выложить и сверить
    python3 tools/deploy_local_model_experts.py --selftest # без сети
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import platform_client as пк

ЭКСПЕРТЫ = ("local_model_classify", "local_model_ask")
АГЕНТ = "agent_extella_default"
КОРЕНЬ = pathlib.Path(__file__).resolve().parent.parent


def описание(текст: str) -> str:
    """Первая строка `# description:` — она же описание в списке у агента.
    Без него агент видит имя и гадает, для чего эксперт."""
    for строка in текст.splitlines()[:6]:
        if строка.startswith("# description:"):
            return строка.split(":", 1)[1].strip()
    return ""


def выложить() -> int:
    # X-Agent-Id обязателен: без него ядро отвечает 422 и не говорит, чей это
    # скоуп. Берём агента по умолчанию явно — MCP-путь молча кладёт эксперта в
    # чужой скоуп, и найти его потом нечем.
    заголовки = {"X-Auth-Token": пк.токен(), "X-Profile-Id": "default",
                 "X-Agent-Id": АГЕНТ}
    плохо = 0
    for имя in ЭКСПЕРТЫ:
        путь = КОРЕНЬ / "experts" / f"{имя}.py"
        код = путь.read_text(encoding="utf-8").rstrip()
        оп = описание(код)
        if not оп:
            print(f"  ✗ {имя}: нет строки # description: — агент не поймёт, зачем эксперт")
            плохо += 1
            continue
        код_ответа, сырое = пк.запрос(пк.ЯДРО, "/api/expert/save", тело={
            "name": имя, "description": оп, "code": код,
            "cspl": "fython", "global": True,
        }, заголовки=заголовки, таймаут=90)
        if код_ответа != 200:
            print(f"  ✗ {имя}: не сохранён, HTTP {код_ответа} — {сырое[:200]}")
            плохо += 1
            continue
        код_ответа, сырое = пк.запрос(пк.ЯДРО, "/api/expert/get",
                                      тело={"name": имя, "global": True},
                                      заголовки=заголовки, таймаут=60)
        данные = json.loads(сырое) if сырое.strip().startswith("{") else {}
        # Ядро отдаёт код в expert_code. Первая версия читала "code" — поле
        # всегда пустое, и сверка объявляла провал при исправной записи.
        записано = данные.get("expert_code") or ""
        if записано.strip() != код:
            print(f"  ✗ {имя}: после записи содержимое отличается от файла")
            плохо += 1
            continue
        print(f"  ✓ {имя}: записан и сверен посимвольно ({len(код)} символов)")
    return 1 if плохо else 0


def _selftest() -> int:
    ошибки = []
    for имя in ЭКСПЕРТЫ:
        путь = КОРЕНЬ / "experts" / f"{имя}.py"
        if not путь.is_file():
            ошибки.append(f"нет файла эксперта {имя}")
            continue
        текст = путь.read_text(encoding="utf-8")
        if not описание(текст):
            ошибки.append(f"{имя}: нет строки # description:")
        # Эксперт ходит только на петлю: платформенный токен ему не нужен и
        # взяться в нём неоткуда — проверяем, что никто не принёс.
        for з in ("X-Auth" + "-Token", "api" + "_token", "EXTELLA_API" + "_TOKEN"):
            if з in текст:
                ошибки.append(f"{имя}: в коде эксперта появился токен — он тут не нужен")
        if "127.0.0.1:1234" not in текст:
            ошибки.append(f"{имя}: эксперт не ходит на локальную LM Studio")
        # Отказ обязан называть следующий шаг, а не только причину.
        if "Выбери в запуске своё устройство" not in текст:
            ошибки.append(f"{имя}: отказ не называет, что делать дальше")
        compile(текст, str(путь), "exec")
    if описание("# description: вот так\nостальное") != "вот так":
        ошибки.append("описание читается неверно")
    if ошибки:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(ошибки))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return _selftest()
    return выложить()


if __name__ == "__main__":
    raise SystemExit(main())

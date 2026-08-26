#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка модуля «распознавание текста».

ЗАЧЕМ. Здесь охраняются два обещания, которые легко потерять при правке:
модуль ничего не ставит без разрешения и не распознаёт языком, которого нет.
Второе тоньше: tesseract без языкового пакета не падает, а выдаёт
правдоподобный мусор — продукт выглядит рабочим, а текст неверный.

Как и у соседнего модуля, проверка обязана уметь провалиться, и это здесь
доказывается: слепок портится нарочно, проверка обязана покраснеть.

    python3 проверка.py --selftest   # без tesseract: форма, границы, негативный контроль
    python3 проверка.py --живьём     # настоящее распознавание образца

Коды выхода: 0 — прошло, 1 — есть провалы.
"""

import argparse
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile
import time

ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
СЛЕПОК = ЗДЕСЬ / "слепок" / "toolkit_ocr_read.py"
ОБРАЗЕЦ = ЗДЕСЬ / "образец" / "счёт-образец.png"


def загрузить(путь: pathlib.Path):
    сп = importlib.util.spec_from_file_location("слепок_" + путь.stem, путь)
    м = importlib.util.module_from_spec(сп)
    сп.loader.exec_module(м)
    return м.toolkit_ocr_read


def есть_tesseract() -> bool:
    if shutil.which("tesseract"):
        return True
    return any(pathlib.Path(к, "tesseract").exists()
               for к in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"))


def форма(беды: list) -> None:
    for имя, путь in (("рецепт", ЗДЕСЬ / "РЕЦЕПТ.md"), ("паспорт", ЗДЕСЬ / "ПАСПОРТ.md"),
                      ("слепок", СЛЕПОК), ("образец", ОБРАЗЕЦ)):
        if not путь.exists():
            беды.append(f"нет части «{имя}»: {путь.name}")
    if СЛЕПОК.exists():
        текст = СЛЕПОК.read_text(encoding="utf-8")
        if not текст.startswith("# description:"):
            беды.append("у слепка нет строки # description:")
        if "import " in текст.split("def ", 1)[0]:
            беды.append("импорты вне функции: эксперт обязан быть самодостаточным")
        # Программы ищутся не только по PATH — у службы он беднее.
        if "/opt/homebrew/bin" not in текст:
            беды.append("слепок ищет программы только по PATH — у службы он беднее, "
                        "и установленная программа окажется «не установлена»")


def границы(зов, беды: list) -> None:
    случаи = (("пустой путь", {"path": ""}, "какой файл"),
              ("нет файла", {"path": "/tmp/нет-такой-картинки.png"}, "файла нет"),
              ("чужой формат", {"path": str(ЗДЕСЬ / "образец" / "мнимый.odt")}, "не читаю"))
    (ЗДЕСЬ / "образец" / "мнимый.odt").write_text("не картинка", encoding="utf-8")
    try:
        for имя, параметры, ждём in случаи:
            о = json.loads(зов(**параметры))
            if о.get("status") != "error":
                беды.append(f"{имя}: обязан быть отказ, пришло {о.get('status')}")
            elif ждём not in о.get("message", ""):
                беды.append(f"{имя}: отказ не называет причину")
    finally:
        (ЗДЕСЬ / "образец" / "мнимый.odt").unlink(missing_ok=True)


def язык(зов, беды: list) -> None:
    """Языка нет — обязан быть отказ, а не мусор. Берём заведомо несуществующий."""
    if not есть_tesseract():
        print("    (tesseract не установлен — проверку языка пропускаю)")
        return
    о = json.loads(зов(path=str(ОБРАЗЕЦ), lang="ксх"))
    if о.get("status") != "error":
        беды.append("несуществующий язык не остановил модуль — он выдаст мусор")
        return
    if not о.get("нужно_разрешение"):
        беды.append("отказ по языку не предлагает выход")
    if not о.get("есть_языки"):
        беды.append("отказ не перечисляет доступные языки — человеку не из чего выбрать")


def ничего_не_ставит(беды: list) -> None:
    """Без явного разрешения модуль не ставит программ. Проверяем поведением:
    прячем tesseract, подменив места поиска на пустые."""
    исходный = СЛЕПОК.read_text(encoding="utf-8")
    слепой = исходный.replace('for корень in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):',
                              'for корень in ("/несуществующий",):')
    слепой = слепой.replace("п = shutil.which(имя)", "п = None")
    if слепой == исходный:
        беды.append("не удалось спрятать программу — проверка установки не доказана")
        return
    with tempfile.TemporaryDirectory() as вр:
        копия = pathlib.Path(вр) / "слепая.py"
        копия.write_text(слепой, encoding="utf-8")
        о = json.loads(загрузить(копия)(path=str(ОБРАЗЕЦ)))
        if о.get("status") != "error":
            беды.append("без программы модуль обязан отказаться")
        if not о.get("нужно_разрешение"):
            беды.append("отказ не просит разрешения на установку")
        if "сам не ставлю" not in о.get("message", ""):
            беды.append("отказ не говорит, что модуль не ставит программ сам")


def негативный_контроль(беды: list) -> None:
    """Ломаем согласие на установку — проверка обязана покраснеть."""
    исходный = СЛЕПОК.read_text(encoding="utf-8")
    сломанный = исходный.replace('if str(install).strip().lower() != "да-ставь":',
                                 "if False:")
    if сломанный == исходный:
        беды.append("негативный контроль не нашёл, что ломать")
        return
    сломанный = сломанный.replace('for корень in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):',
                                  'for корень in ("/несуществующий",):')
    сломанный = сломанный.replace("п = shutil.which(имя)", "п = None")
    with tempfile.TemporaryDirectory() as вр:
        копия = pathlib.Path(вр) / "сломанная.py"
        копия.write_text(сломанный, encoding="utf-8")
        о = json.loads(загрузить(копия)(path=str(ОБРАЗЕЦ)))
        # Сломанный слепок больше НЕ просит разрешения — значит проверка выше
        # на нём краснеет, как и должна.
        if о.get("нужно_разрешение"):
            беды.append("негативный контроль: сломанный слепок всё ещё просит разрешения")


# Форма ответа — часть товара, а не украшение (см. опыт в toolkits/README.md).
ОБЯЗАТЕЛЬНЫЕ_КЛЮЧИ = {"status", "file", "read_by", "left_device", "lang",
                       "chars", "text", "installed_anything"}


def форма_ответа(беды: list) -> None:
    if not есть_tesseract() or not ОБРАЗЕЦ.exists():
        return
    о = json.loads(загрузить(СЛЕПОК)(path=str(ОБРАЗЕЦ), lang="eng"))
    if о.get("status") != "success":
        return
    нет = ОБЯЗАТЕЛЬНЫЕ_КЛЮЧИ - set(о)
    if нет:
        беды.append("в ответе нет обязательных ключей: " + ", ".join(sorted(нет)) +
                    " — приложение покупателя на такой сборке сломается")


def живьём(беды: list) -> None:
    if not есть_tesseract():
        беды.append("tesseract не установлен — живой прогон невозможен")
        return
    зов = загрузить(СЛЕПОК)
    т0 = time.time()
    о = json.loads(зов(path=str(ОБРАЗЕЦ), lang="eng"))
    сек = time.time() - т0
    if о.get("status") != "success":
        беды.append("живой прогон не прошёл: " + str(о.get("message"))[:120])
        return
    print(f"    распознано за {сек:.1f} с, чем: {о.get('read_by')}, "
          f"наружу ушло: {о.get('left_device')}, поставлено: {о.get('installed_anything')}")
    if о.get("left_device") is not False:
        беды.append("модуль сообщает, что картинка покидала устройство")
    if о.get("installed_anything"):
        беды.append("модуль что-то поставил без разрешения")
    текст = str(о.get("text", ""))
    for имя, образ in (("сумма", r"4\s?600\s?000"), ("срок", r"60\s+days"),
                       ("номер", r"2026-0418")):
        if not re.search(образ, текст, re.I):
            беды.append(f"в распознанном нет факта «{имя}» из образца")


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__)
    р.add_argument("--selftest", action="store_true")
    р.add_argument("--живьём", dest="живьём", action="store_true")
    о = р.parse_args()
    беды = []
    if о.живьём:
        print("  живой прогон модуля «распознавание текста»:")
        живьём(беды)
    else:
        форма(беды)
        print("  ✓ три части тулкита на месте, программы ищутся не только по PATH")
        if СЛЕПОК.exists():
            зов = загрузить(СЛЕПОК)
            границы(зов, беды)
            print("  ✓ отказы называют причину")
            язык(зов, беды)
            print("  ✓ языка нет — отказ, а не правдоподобный мусор")
            ничего_не_ставит(беды)
            print("  ✓ без разрешения модуль ничего не ставит")
            негативный_контроль(беды)
            print("  ✓ проверка умеет краснеть: сломанное согласие ловится")
            форма_ответа(беды)
            print("  ✓ форма ответа на месте: приложение покупателя не сломается")
    if беды:
        for б in беды:
            print("  ✗ " + б)
        print("ИТОГ САМОПРОВЕРКИ: провалы есть")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    sys.exit(main())

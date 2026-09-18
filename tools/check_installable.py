#!/usr/bin/env python3
"""Гейт доставки: продукт с архивом обязан быть устанавливаемым.

ЗАЧЕМ. Перепись живой витрины 18.09.2026 — 50 продуктов, состав каждой версии
взят из API магазина. Четыре продукта из пятидесяти нельзя установить в
принципе, и ни один из них об этом не сообщает:

    архив есть, установщика нет — 3 (Разработка на Extella 13 загрузок,
                                     Personal Assistant 6, Lawyer 1)
    установщик есть, архива нет — 1 (Recruiter, 8 загрузок)
    ни страницы, ни архива       — 2 (Discussion Agent, Мияу)

Покупатель при этом видит только «The installer did not finish» — без причины и
без следующего шага. Двадцать восемь загрузок ушли в продукты, которые не могли
установиться.

Три правила ниже — из трёх разных поломок, найденных в один день на стенде:

    1. Архив без установщика — платформе некого позвать (Human Atlas, 32 МБ).
    2. Установщик без архива — звать есть кого, а разворачивать нечего (Recruiter).
    3. install.py не в корне архива — установщик его не находит. У Lawyer весь
       продукт вложен в лишнюю папку kazakh-lawyer/, и там ЕСТЬ install.py,
       только уровнем глубже. Никакой эксперт этого не обойдёт (канон B1).

    4. install.py, прибитый к одной ОС. Human Atlas звал launchctl без веток и
       падал на Linux «No such file or directory: 'launchctl'» — продукт мог
       установиться только на Маке, и три года никто этого не замечал, потому
       что авторы на Маках.

    python3 tools/check_installable.py products/пример
    python3 tools/check_installable.py --selftest

Коды выхода: 0 — состав доставки связный, 1 — нет, 2 — проверять было нечего.
"""

import json
import pathlib
import re
import sys
import zipfile

# Вызовы, привязывающие установщик к одной системе. Ищем в install.py архива.
МАКОВЫЕ = re.compile(r"launchctl|LaunchAgents|\.plist\b")
ЛИНУКСОВЫЕ = re.compile(r"systemctl|systemd")
ВИНДОВЫЕ = re.compile(r"schtasks|Startup|winreg|pythonw")
# Признак того, что автор вообще думал о платформах.
ВЕТКА = re.compile(r"sys\.platform|platform\.system|os\.name")


def отказ(беды: list) -> int:
    for б in беды:
        print("  ✗ " + б)
    print(f"ИТОГ: доставка несвязная, бед — {len(беды)}")
    return 1


def _состав(папка: pathlib.Path) -> dict:
    """Что продукт заявил о себе и что реально лежит рядом."""
    установщик = ""
    app = папка / "app.json"
    if app.exists():
        try:
            d = json.loads(app.read_text(encoding="utf-8"))
            установщик = str(d.get("установщик") or d.get("installer")
                             or d.get("installer_expert") or "").strip()
        except Exception:                                    # noqa: BLE001
            pass
    # СПОСОБНОСТЬ — ОТДЕЛЬНЫЙ КАНАЛ, И ТРЕБОВАТЬ С НЕЁ СТРАНИЦУ НЕЛЬЗЯ.
    # Первая редакция гейта дала пять ложных красных на editions/2gis,
    # read-page, kz-listings, to-apps, data-privacy: у них `kind: source`,
    # поставляются экспертом и инструментом, и ни страницы, ни архива у них
    # не бывает по устройству. Ложный красный так же вреден, как пропуск:
    # гейт, который врёт, отключают целиком.
    вид, способность = "", False
    listing = папка / "listing.json"
    if listing.exists():
        try:
            d = json.loads(listing.read_text(encoding="utf-8"))
            вид = str(d.get("kind") or d.get("вид") or "").strip().lower()
            способность = вид == "source" or bool(
                str(d.get("эксперт") or "").strip() or str(d.get("инструмент") or "").strip())
        except Exception:                                    # noqa: BLE001
            pass
    архивы = sorted(p for p in папка.glob("*.zip") if p.is_file())
    страница = (папка / "index.html").exists() or (папка / "page.html").exists()
    return {"установщик": установщик, "архивы": архивы, "страница": страница,
            "вид": вид, "способность": способность}


def проверить(папка: pathlib.Path) -> int:
    if not папка.is_dir():
        print(f"нет такой папки: {папка}")
        return 2
    с = _состав(папка)
    if с["способность"] and not с["архивы"] and not с["установщик"]:
        print("ИТОГ: способность (kind=source) — страница и архив ей не нужны")
        return 0
    if not с["архивы"] and not с["установщик"] and not с["страница"]:
        print("НЕ УСПЕХ: ни страницы, ни архива, ни установщика — "
              "продукта здесь нет. Это не «проверять нечего», это пустая карточка")
        return 1

    беды = []
    if с["архивы"] and not с["установщик"]:
        беды.append(f"архив есть ({с['архивы'][0].name}), а установщика нет: "
                    f"платформе некого позвать. Добавьте «установщик» в app.json")
    if с["установщик"] and not с["архивы"]:
        беды.append(f"установщик объявлен ({с['установщик']}), а архива рядом нет: "
                    f"звать есть кого, разворачивать нечего")

    for архив in с["архивы"]:
        try:
            with zipfile.ZipFile(архив) as z:
                имена = z.namelist()
                корневые = [n for n in имена if "/" not in n.strip("/")]
                if "install.py" not in корневые:
                    глубже = [n for n in имена if n.endswith("/install.py")]
                    если_глубже = (f"; он лежит глубже: {глубже[0]}" if глубже else "")
                    беды.append(f"{архив.name}: в КОРНЕ архива нет install.py — "
                                f"установщик его не найдёт{если_глубже}")
                    continue
                код = z.read("install.py").decode("utf-8", errors="replace")
                мак = bool(МАКОВЫЕ.search(код))
                прочие = bool(ЛИНУКСОВЫЕ.search(код) or ВИНДОВЫЕ.search(код))
                if мак and not прочие and not ВЕТКА.search(код):
                    беды.append(f"{архив.name}: install.py прибит к macOS "
                                f"(launchctl/LaunchAgents без веток по платформе) — "
                                f"на Linux и Windows упадёт")
        except zipfile.BadZipFile:
            беды.append(f"{архив.name}: не zip — витрина отдаст покупателю мусор")

    if беды:
        return отказ(беды)
    что = []
    if с["страница"]:
        что.append("страница")
    if с["архивы"]:
        что.append(f"архив + установщик «{с['установщик']}»")
    print("ИТОГ: доставка связная — " + ", ".join(что))
    return 0


def _selftest() -> int:
    import tempfile

    провалы = []

    def пакет(корневой_install=True, маковый=False, вложенный=False, битый=False) -> bytes:
        import io
        код = ("import subprocess\n"
               "subprocess.run(['launchctl','bootstrap'])\n" if маковый else
               "import sys\nprint(sys.platform)\n")
        буфер = io.BytesIO()
        with zipfile.ZipFile(буфер, "w") as z:
            if вложенный:
                z.writestr("продукт/install.py", код)
            elif корневой_install:
                z.writestr("install.py", код)
            z.writestr("dist/index.html", "<html></html>")
        данные = буфер.getvalue()
        return "не zip вовсе".encode("utf-8") if битый else данные

    def случай(имя, ждём_беду, *, установщик="board_setup", архив=True,
               страница=True, карточка=None, **как):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            if карточка is not None:
                (p / "listing.json").write_text(
                    json.dumps(карточка, ensure_ascii=False), encoding="utf-8")
            if установщик:
                (p / "app.json").write_text(
                    json.dumps({"имя": "Проба", "установщик": установщик}, ensure_ascii=False),
                    encoding="utf-8")
            if страница:
                (p / "index.html").write_text("<html></html>", encoding="utf-8")
            if архив:
                (p / "пакет.zip").write_bytes(пакет(**как))
            код = проверить(p)
            ок = (код != 0) == ждём_беду
            print(("  ✓ " if ок else "  ✗ ") + имя)
            if not ок:
                провалы.append(имя)

    print("Самопроверка check_installable:")
    случай("полный связный продукт проходит", False)
    случай("только страница, без архива — проходит", False, установщик="", архив=False)
    случай("архив без установщика — ловится", True, установщик="")
    случай("установщик без архива — ловится", True, архив=False)
    случай("install.py не в корне — ловится", True, вложенный=True)
    случай("install.py вовсе нет — ловится", True, корневой_install=False)
    случай("install.py только под macOS — ловится", True, маковый=True)
    случай("битый zip — ловится", True, битый=True)
    случай("пусто: ни страницы, ни архива — ловится", True,
           установщик="", архив=False, страница=False)
    случай("способность kind=source — НЕ краснеет", False, установщик="", архив=False,
           страница=False, карточка={"name": "2GIS", "kind": "source",
                                     "инструмент": "источник_2gis.py"})
    случай("способность с экспертом — НЕ краснеет", False, установщик="", архив=False,
           страница=False, карточка={"name": "Reader", "эксперт": "read_web_page"})

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(проверить(pathlib.Path(sys.argv[1])))

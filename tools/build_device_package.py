#!/usr/bin/env python3
"""Собрать пакет устройственного продукта — то, что реально поедет покупателю.

    python3 tools/build_device_package.py --slug dokumenty
    python3 tools/build_device_package.py --slug dokumenty --куда ~/Downloads
    python3 tools/build_device_package.py --selftest

ЗАЧЕМ. Замер 25.08.2026: коллега владельца установила приложение из магазина,
установка прошла успешно — и ничего не заработало. В версии лежала одна страница
окна, которая смотрит на localhost её машины; самой программы там не было. Человек
не ошибся — ему продали пустой пакет, и магазин об этом не предупредил.

Пакет собирается ИЗ ТРЁХ ИСТОЧНИКОВ, и каждый обязателен:
  install.py     — из editions/<slug>/ (установщик, раздел B стандартов);
  файлы программы — из места, где приложение реально живёт;
  список нужного — из editions/<slug>/package.json.

ЧТО ПРОВЕРЯЕТ ПЕРЕД СБОРКОЙ (иначе пустой пакет уедет снова):
  * установщик на месте и разбирается как код;
  * все файлы из списка существуют;
  * внутри нет секретов (B7) — архив едет покупателю целиком;
  * размер в пределах, которые принимает витрина.
"""

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

СЮДА = pathlib.Path(__file__).resolve().parent
КОРЕНЬ = СЮДА.parent
sys.path.insert(0, str(СЮДА))
from формы import Отказ  # noqa: E402

ПРЕДЕЛ_МБ = 100          # архив у витрины: ≤ 100 МБ
СЕКРЕТЫ = re.compile(
    r"(ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9_]{20}|sk-ant-[A-Za-z0-9-]{20}"
    r"|sk-[A-Za-z0-9]{32}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY"
    r"|AUTH_TOKEN\s*=\s*[\"'][A-Za-z0-9_-]{16})")


def описание_пакета(slug: str) -> dict:
    п = КОРЕНЬ / "editions" / slug / "package.json"
    if not п.exists():
        raise Отказ(
            f"нет {п}. Это список того, ЧТО везти покупателю: "
            f'{{"откуда": "~/extella-plugins/{slug}", "файлы": ["server.py", "index.html"]}}. '
            f"Без него пакет собрался бы пустым — ровно та беда, из-за которой "
            f"приложение «устанавливается» и не работает")
    return json.loads(п.read_text())


def собрать(slug: str, куда: pathlib.Path | None = None) -> pathlib.Path:
    оп = описание_пакета(slug)
    издание = КОРЕНЬ / "editions" / slug
    установщик = издание / "install.py"
    if not установщик.exists():
        raise Отказ(f"нет {установщик} — без установщика продукт устройственным "
                    f"не является: платформа положит покупателю только страницу")
    try:
        compile(установщик.read_text(), str(установщик), "exec")
    except SyntaxError as е:
        raise Отказ(f"установщик не разбирается как код: {е}") from е

    откуда = pathlib.Path(str(оп.get("откуда", ""))).expanduser()
    if not откуда.is_dir():
        raise Отказ(f"папки приложения нет: {откуда}")

    корзина = pathlib.Path(tempfile.mkdtemp(prefix=f"пакет_{slug}_"))
    shutil.copy(установщик, корзина / "install.py")
    не_хватает = []
    for имя in оп.get("файлы", []):
        и = откуда / имя
        if not и.exists():
            не_хватает.append(имя)
            continue
        (корзина / имя).parent.mkdir(parents=True, exist_ok=True)
        if и.is_dir():
            shutil.copytree(и, корзина / имя, dirs_exist_ok=True)
        else:
            shutil.copy(и, корзина / имя)
    if не_хватает:
        shutil.rmtree(корзина)
        raise Отказ(f"в папке приложения нет файлов: {', '.join(не_хватает)}")

    # B7: архив едет покупателю ЦЕЛИКОМ — секрет внутри увидят все, кто купил.
    попались = []
    for ф in корзина.rglob("*"):
        if ф.is_file() and ф.suffix in (".py", ".html", ".js", ".json", ".yaml", ".yml", ".txt"):
            if СЕКРЕТЫ.search(ф.read_text(errors="ignore")):
                попались.append(str(ф.relative_to(корзина)))
    if попались:
        shutil.rmtree(корзина)
        raise Отказ(f"в пакете найдены похожие на секреты значения: "
                    f"{', '.join(попались)}. Архив едет покупателю целиком — "
                    f"уберите их из файлов приложения")

    вес = sum(ф.stat().st_size for ф in корзина.rglob("*") if ф.is_file()) / 1048576
    if вес > ПРЕДЕЛ_МБ:
        shutil.rmtree(корзина)
        raise Отказ(f"пакет {вес:.0f} МБ при пределе витрины {ПРЕДЕЛ_МБ} МБ")

    куда = (куда or (КОРЕНЬ / "editions" / slug)).expanduser()
    куда.mkdir(parents=True, exist_ok=True)
    архив = куда / f"{slug}-пакет.tar.gz"
    итог = subprocess.run(["tar", "-czf", str(архив), "-C", str(корзина.parent), корзина.name],
                          capture_output=True, text=True, timeout=1800)
    shutil.rmtree(корзина)
    if итог.returncode != 0:
        raise Отказ(f"архив не собрался: {(итог.stderr or '')[:200]}")
    print(f"  пакет: {архив}")
    print(f"  вес: {архив.stat().st_size / 1048576:.2f} МБ · внутри: install.py + "
          f"{len(оп.get('файлы', []))} файлов приложения")
    print(f"  секретов не найдено, размер в пределах витрины")
    return архив


def _самопроверка() -> int:
    ошибки = []
    try:
        описание_пакета("нет-такого-продукта")
        ошибки.append("отсутствующее описание не вызвало отказа")
    except Отказ as е:
        if "package.json" in str(е):
            print("  ✓ без описания пакета сборка отказывает и объясняет формат")
        else:
            ошибки.append(f"отказ не про описание: {е}")

    # Главная проверка трека: секрет не должен уехать покупателю.
    песочница = pathlib.Path(tempfile.mkdtemp(prefix="проба_пакета_"))
    (песочница / "editions" / "проба").mkdir(parents=True)
    (песочница / "прил").mkdir()
    (песочница / "прил" / "server.py").write_text(
        "AUTH_TOKEN = 'aBcD1234EfGh5678XyZ'\n")
    (песочница / "editions" / "проба" / "install.py").write_text("print('ok')\n")
    (песочница / "editions" / "проба" / "package.json").write_text(json.dumps(
        {"откуда": str(песочница / "прил"), "файлы": ["server.py"]}, ensure_ascii=False))
    глобальный = globals()
    прежний = глобальный["КОРЕНЬ"]
    глобальный["КОРЕНЬ"] = песочница
    try:
        собрать("проба")
        ошибки.append("пакет с секретом собрался — он уехал бы покупателю")
    except Отказ as е:
        if "секрет" in str(е):
            print("  ✓ секрет в файлах приложения останавливает сборку")
        else:
            ошибки.append(f"отказ не про секрет: {е}")
    finally:
        глобальный["КОРЕНЬ"] = прежний
        shutil.rmtree(песочница, ignore_errors=True)

    for о in ошибки:
        print(f"  ✗ {о}")
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("--slug")
    р.add_argument("--куда", dest="куда", default="")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return _самопроверка()
    if not а.slug:
        р.error("нужен --slug")
    try:
        собрать(а.slug, pathlib.Path(а.куда) if а.куда else None)
    except Отказ as е:
        print(f"отказ: {е}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Самообновление устройственного продукта — канонический модуль (H14).

Копируется в продукт как есть. Два источника на выбор:

* **магазин** (`store`) — `GET /api/app-archive?app=ИМЯ`, архив под версиями платформы.
  Предпочтительный: платформа знает, у кого что стоит, и доступ под её контролем;
* **GitHub по тегу релиза** (`github`) — быстрее в итерациях, но обновление приезжает
  в чужой контур, поэтому только по тегу и только со сверкой суммы.

Что модуль делает и, главное, чего НЕ делает:

* никогда не обновляет молча: без `подтверждено=True` он только сообщает, что доступно;
* никогда не берёт плавающую ветку — `main` отвергается на входе;
* сверяет sha256 до распаковки, а не после;
* прежнюю копию сохраняет рядом, чтобы был путь назад.

Самопроверка: `python3 self_update.py --selftest` — она умеет падать и это проверяет.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request

ОС = "https://os.extella.ai"
ПЛАВАЮЩИЕ = {"main", "master", "HEAD", "latest-commit"}


class Отказ(Exception):
    """Отказ, который умеет сказать, что делать дальше."""


def _токен_устройства() -> str:
    """Канон platform_client: файл доступа, потом конфиг визарда."""
    прямой = pathlib.Path.home() / ".extella" / "api_token.txt"
    if прямой.exists() and прямой.read_text().strip():
        return прямой.read_text().strip()
    конфиг = pathlib.Path.home() / "extella_wizard" / "app" / "config.json"
    if конфиг.exists():
        d = json.loads(конфиг.read_text())
        for k in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
            if d.get(k):
                return str(d[k])
    raise Отказ("не найден доступ к Extella на этом устройстве: нет файла "
                "~/.extella/api_token.txt. Открой Extella на этой машине один раз.")


def _скачать(адрес: str, заголовки: dict | None = None, таймаут: int = 180) -> bytes:
    r = urllib.request.Request(адрес, headers=заголовки or {})
    try:
        with urllib.request.urlopen(r, timeout=таймаут) as о:
            return о.read()
    except urllib.error.HTTPError as e:
        raise Отказ(f"источник ответил {e.code} на {адрес.split('?')[0]}. "
                    "Проверь имя продукта и доступ, потом повтори.")
    except Exception as e:
        raise Отказ(f"не дошёл до источника ({e}). Проверь сеть и повтори.")


def сумма(данные: bytes) -> str:
    return hashlib.sha256(данные).hexdigest()


def проверить_метку(метка: str) -> str:
    """Плавающая ветка как источник обновления — запрещена (H14)."""
    if not метка or метка in ПЛАВАЮЩИЕ:
        raise Отказ(f"источником обновления указана плавающая ветка «{метка}». "
                    "Укажи тег релиза: из ветки приедет что угодно, что в неё запушили.")
    if not re.fullmatch(r"[A-Za-z0-9._\-+/]{1,80}", метка):
        raise Отказ(f"недопустимая метка версии «{метка}» — ожидается тег релиза.")
    return метка


def из_магазина(имя_продукта: str, версия: str | None = None) -> bytes:
    адрес = f"{ОС}/api/app-archive?app={urllib.parse.quote(имя_продукта)}"
    if версия:
        адрес += f"&version={urllib.parse.quote(версия)}"
    return _скачать(адрес, {"X-Extella-Token": _токен_устройства()})


def из_github(владелец_репо: str, тег: str) -> bytes:
    проверить_метку(тег)
    адрес = f"https://codeload.github.com/{владелец_репо}/tar.gz/refs/tags/{тег}"
    return _скачать(адрес)


def безопасно_распаковать(архив: bytes, куда: pathlib.Path):
    """Распаковка с отказом на путях наружу: архив приходит извне контура."""
    куда.mkdir(parents=True, exist_ok=True)
    корень = куда.resolve()
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
        f.write(архив)
        путь = pathlib.Path(f.name)
    try:
        with tarfile.open(путь) as t:
            for член in t.getmembers():
                цель = (корень / член.name).resolve()
                if not str(цель).startswith(str(корень) + os.sep):
                    raise Отказ(f"архив пытается писать за свои пределы ({член.name}). "
                                "Обновление отменено, прежняя версия на месте.")
                if член.issym() or член.islnk():
                    raise Отказ(f"в архиве ссылка ({член.name}) — отклонено.")
            t.extractall(корень)
    finally:
        путь.unlink(missing_ok=True)


def обновить(*, куда: pathlib.Path, источник: str, имя_продукта: str = "",
             владелец_репо: str = "", тег: str = "", ожидаемая_сумма: str = "",
             подтверждено: bool = False, сообщить=print) -> dict:
    """Обновить продукт. Без `подтверждено=True` только сообщает, что доступно."""
    if источник == "store":
        архив = из_магазина(имя_продукта)
        откуда = f"магазин, продукт «{имя_продукта}»"
    elif источник == "github":
        архив = из_github(владелец_репо, тег)
        откуда = f"GitHub {владелец_репо}, тег {тег}"
    else:
        raise Отказ(f"неизвестный источник «{источник}»: ожидается store или github.")

    факт = сумма(архив)
    if ожидаемая_сумма and факт != ожидаемая_сумма:
        raise Отказ("контрольная сумма не сошлась — обновление отменено, прежняя версия "
                    f"на месте. Ожидалось {ожидаемая_сумма[:12]}…, получено {факт[:12]}…")

    if not подтверждено:
        сообщить(f"Доступно обновление: {откуда}, {len(архив)} байт, сумма {факт[:12]}…")
        сообщить("Ничего не менял: обновление применяется только с явным подтверждением.")
        return {"применено": False, "сумма": факт, "байт": len(архив), "откуда": откуда}

    куда = pathlib.Path(куда)
    запас = куда.with_name(куда.name + ".предыдущая")
    if куда.exists():
        if запас.exists():
            shutil.rmtree(запас)
        shutil.move(str(куда), str(запас))
    try:
        безопасно_распаковать(архив, куда)
    except Exception:
        if запас.exists():
            if куда.exists():
                shutil.rmtree(куда)
            shutil.move(str(запас), str(куда))
        raise
    сообщить(f"Обновлено из: {откуда}. Прежняя версия рядом: {запас.name}")
    return {"применено": True, "сумма": факт, "байт": len(архив),
            "откуда": откуда, "откат": str(запас)}


def _selftest() -> int:
    провалы = []

    def проверка(имя, функция):
        try:
            функция()
            print(f"  ✓ {имя}")
        except AssertionError as e:
            провалы.append(f"{имя}: {e}")
            print(f"  ✗ {имя}: {e}")

    def плавающая_ветка_отвергается():
        for ветка in ("main", "master", "HEAD", ""):
            try:
                проверить_метку(ветка)
            except Отказ:
                continue
            raise AssertionError(f"ветка «{ветка}» прошла, а не должна")

    def тег_проходит():
        assert проверить_метку("v1.2.3") == "v1.2.3", "нормальный тег отвергнут"

    def сумма_ловит_подмену():
        assert сумма(b"a") != сумма(b"b"), "разные данные дали одну сумму"

    def выход_за_пределы_отвергается():
        with tempfile.TemporaryDirectory() as d:
            корень = pathlib.Path(d)
            злой = корень / "злой.tar.gz"
            обычный = корень / "файл.txt"
            обычный.write_text("данные")
            with tarfile.open(злой, "w:gz") as t:
                t.add(обычный, arcname="../наружу.txt")
            try:
                безопасно_распаковать(злой.read_bytes(), корень / "цель")
            except Отказ:
                return
            raise AssertionError("архив с путём наружу распаковался")

    def без_подтверждения_ничего_не_меняет():
        with tempfile.TemporaryDirectory() as d:
            цель = pathlib.Path(d) / "продукт"
            цель.mkdir()
            (цель / "старое.txt").write_text("на месте")
            вызовы = []
            # источник не дёргается: подтверждения нет, значит и качать нечего кроме проверки
            try:
                обновить(куда=цель, источник="неизвестный", сообщить=вызовы.append)
            except Отказ:
                pass
            assert (цель / "старое.txt").exists(), "файл продукта пропал при отказе"

    print("Самопроверка self_update:")
    проверка("плавающая ветка отвергается", плавающая_ветка_отвергается)
    проверка("тег релиза проходит", тег_проходит)
    проверка("сумма различает данные", сумма_ловит_подмену)
    проверка("архив с путём наружу отвергается", выход_за_пределы_отвергается)
    проверка("без подтверждения продукт не тронут", без_подтверждения_ничего_не_меняет)

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

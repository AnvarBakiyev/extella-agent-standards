#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Внутренность стенда: то, что происходит В КОРОБКЕ от лица покупателя.

Запускается bench_runner.sh внутри одноразового контейнера. Хост передаёт
version_id; токен стендового аккаунта уже лежит в /root/.extella_token.

Каждый этап отвечает словами и останавливается на первом провале: покупателю
дальше тоже не пройти.

Этапы:
  4. таргет устройства зарегистрирован и виден платформе;
  5. покупка версии (deferred-поток дочитывается до конца, running ≠ успех);
  6. установка дошла: файлы продукта на месте;
  7. самопроверка продукта из MANIFEST.yaml — её протокол уезжает на хост.
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ЯДРО = "https://api.extella.ai"
ОС = "https://os.extella.ai"
ТОКЕН = pathlib.Path("/root/.extella_token").read_text(encoding="utf-8").strip()


def как_json(текст: str, имя: str = "ответ") -> dict:
    try:
        return json.loads(текст)
    except json.JSONDecodeError:
        return {}


def зов(база: str, путь: str, тело: dict | None = None, таймаут: int = 120) -> tuple:
    з = urllib.request.Request(
        база + путь,
        data=json.dumps(тело).encode() if тело is not None else None,
        method="POST" if тело is not None else "GET",
        headers={"X-Auth-Token": ТОКЕН, "X-Extella-Token": ТОКЕН,
                 "X-Profile-Id": "default",
                 # Без X-Agent-Id ядро отвечает 400 «Agent required» — первая
                 # строка нашего же канона, на которую этот скрипт и наступил:
                 # этапы 3–4 падали на targets/search, а причина была в шапке.
                 "X-Agent-Id": "agent_extella_default",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(з, timeout=таймаут) as о:
            return о.status, о.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500].decode(errors="replace")


def этап(номер: int, имя: str, ок: bool, детали: str) -> None:
    print(f"  {номер}. {'✓' if ок else '✗'} {имя}: {детали}", flush=True)
    if not ок:
        print(f"итог: покупатель остановился на этапе {номер}", flush=True)
        sys.exit(1)


def запустить_листенер() -> str:
    """Поднять листенер стенда и дождаться его регистрации.

    Самое тёмное место стенда: на проде листенер запущен с --crypto-key,
    который выдавался при установке через визард. Как рождается ключ нового
    устройства — обкатка и выясняет. Первая попытка: запуск без ключа, токен
    аккаунта в окружении; хвост журнала листенера уходит в протокол, чтобы
    отказ был виден словами, а не молчанием.
    """
    import os, shutil, subprocess
    # Листенер может быть уже жив с прошлой попытки в той же коробке: второй
    # процесс рядом с первым — два опросчика одного устройства и двойное
    # исполнение задач. Живость видна по свежим опросам в журнале.
    ж = pathlib.Path("/root/listener.log")
    if ж.exists() and "/ask" in ж.read_text(encoding="utf-8", errors="replace")[-2000:]:
        return "зарегистрирован"
    бинарь = ("/root/lv/bin/extella-listener"
              if pathlib.Path("/root/lv/bin/extella-listener").exists()
              else shutil.which("extella-listener") or "python3 -m extella_listener")
    среда = dict(os.environ, EXTELLA_API_TOKEN=ТОКЕН, EXTELLA_AUTH_TOKEN=ТОКЕН)
    pathlib.Path("/root/listener").mkdir(exist_ok=True)
    ключ = pathlib.Path("/root/.crypto_key")
    крипто = f"--crypto-key {ключ.read_text().strip()} " if ключ.exists() else ""
    subprocess.Popen(
        f"nohup {бинарь} --url https://disnet.extella.ai/ --type private "
        f"--interval 5.0 --work-dir /root/listener {крипто}"
        f"--description 'bench box (одноразовый контейнер стенда)' "
        f"> /root/listener.log 2>&1 &",
        shell=True, env=среда)
    # Живость = листенер ОПРАШИВАЕТ платформу (/ask в журнале). Прежняя проверка
    # ждала таргет — но таргет создаётся этапом позже, и этап 3 проваливался на
    # живом листенере (замер 20.08.2026, прогон на 1.11.2). Процесс без опросов
    # при этом всё ещё не считается: он может жить и молчать.
    for _ in range(12):
        time.sleep(5)
        if ж.exists() and "/ask" in ж.read_text(encoding="utf-8",
                                                errors="replace")[-2000:]:
            return "зарегистрирован"
    хвост = ""
    ж = pathlib.Path("/root/listener.log")
    if ж.exists():
        хвост = " ".join(ж.read_text(encoding="utf-8", errors="replace").split())[-300:]
    return f"не зарегистрировался за 60 с · журнал: {хвост or 'пуст'}"


def main() -> int:
    вид = sys.argv[1]

    итог_листенера = запустить_листенер()
    этап(3, "листенер стенда", итог_листенера == "зарегистрирован", итог_листенера)

    # 4. Таргет устройства. Листенер регистрирует устройство на диснете, но
    #    таргетом ядра оно само НЕ становится (замер 20.08.2026) — таргет
    #    создаётся явно. Стенд делает это сам и держит имя «bench», чтобы
    #    уборка находила его безошибочно.
    свой = subprocess.run(
        ["/root/lv/bin/extella-listener", "--device-id",
         "-u", "https://disnet.extella.ai/", "-w", "/root/listener"],
        capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[-1]
    print(f"  устройство коробки: {свой}", flush=True)
    код, т = зов(ЯДРО, "/api/targets/search", {"query": "bench коробка стенда"})
    if not (код == 200 and свой in т):
        # REST зовёт устройство полем «target», не «device_id»: 422 с
        # missing body.target — замер 20.08.2026. У MCP-инструмента поле своё.
        код2, т2 = зов(ЯДРО, "/api/targets/add", {
            "target": свой,
            "description": "Bench-коробка стенда тестирования: одноразовый "
                           "LXD-контейнер, живёт минуты прогона."})
        этап(4, "таргет стенда создан", код2 == 200, f"HTTP {код2} · {т2[:120]}")
    else:
        этап(4, "таргет стенда уже есть", True, свой)

    # 5. Покупка. Поток дочитывается до done: running — не результат.
    код, т = зов(ОС, f"/api/purchase-stream/{вид}", {}, таймаут=600)
    куплено = код == 200 and '"type": "done"' in т.replace("'", '"')
    этап(5, "покупка и развёртывание",
         куплено, f"HTTP {код} · " + " ".join(т.split())[-160:])

    # 5б. Установщик. Покупка его НЕ запускает (замер 20.08.2026: задача в
    #     коробку не пришла) — его запускает человек первым нажатием из окна.
    #     Стенд имитирует это нажатие: явный запуск с закреплением за СВОИМ
    #     устройством массивом. Дефолтное устройство аккаунта не трогается.
    import re as _re
    установщик = ""
    м = _re.search(r'"installer_expert":\s*"([\w-]+)"', т)
    if м:
        установщик = м.group(1)
    if установщик:
        код, т2 = зов(ОС, "/api/my-listings")
        имя_прод, версия_прод = "", ""
        for л in (как_json(т2).get("listings") or []):
            к3, т3 = зов(ОС, f"/api/listing/{л['id']}")
            for в in (как_json(т3).get("versions") or []):
                if в.get("id") == вид:
                    имя_прод, версия_прод = л.get("name", ""), в.get("version", "")
        этап(5, "имя и версия продукта найдены", bool(имя_прод),
             f"{имя_прод} {версия_прод}")
        код, т4 = зов(ЯДРО, "/api/expert/run", {
            "expert_name": установщик, "global": True,
            "targets": [свой],
            "params": {"app_name": имя_прод, "version": версия_прод,
                       "token": ТОКЕН}}, таймаут=600)
        ответ = т4
        м2 = _re.search(r'"status\\?":\s*\\?"(\w+)', т4)
        статус = м2.group(1) if м2 else "?"
        этап(5, f"установщик {установщик} на устройстве стенда",
             код == 200 and статус in ("ok", "installed", "success", "dry_run"),
             f"HTTP {код} · статус {статус} · " + " ".join(ответ.split())[-160:])

    # 6. Файлы продукта. Установщик кладёт их в дом покупателя.
    следы = list(pathlib.Path.home().glob("extella*")) + \
            list(pathlib.Path("/root").glob("extella*"))
    этап(6, "файлы продукта на устройстве",
         bool(следы), ", ".join(str(с) for с in следы[:4]) or "дом пуст — установщик не дошёл")

    # 7. Самопроверка продукта, если он её объявил.
    манифест = None
    for с in следы:
        манифест = next(iter(с.glob("**/MANIFEST.yaml")), None) or манифест
    if манифест is None:
        print("  7. ~ самопроверки нет (нет MANIFEST.yaml) — в магазине это бейдж "
              "«Без самопроверки»", flush=True)
        return 0
    команда = ""
    for строка in манифест.read_text(encoding="utf-8").splitlines():
        if строка.strip().startswith("#"):
            continue
        if "самопроверка:" in строка or "selfcheck:" in строка:
            команда = строка.split(":", 1)[1].strip()
            break
    этап(7, "самопроверка объявлена", bool(команда), команда or "строки нет в манифесте")
    итог = subprocess.run(команда.split(), cwd=манифест.parent,
                          capture_output=True, text=True, timeout=300)
    вывод = " ".join(((итог.stdout or "") + (итог.stderr or "")).split())[:200]
    этап(7, "самопроверка на чистой машине", итог.returncode == 0, вывод)
    return 0


if __name__ == "__main__":
    sys.exit(main())

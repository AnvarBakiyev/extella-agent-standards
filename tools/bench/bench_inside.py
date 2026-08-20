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
    # Ждём появления таргета, а не просто процесса: процесс может жить и молчать.
    for _ in range(12):
        time.sleep(5)
        код, т = зов(ЯДРО, "/api/targets/search", {"query": "bench"})
        if код == 200 and "bench" in т.lower():
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

    # 4. Таргет: листенер при первом запуске регистрирует устройство сам.
    #    Здесь проверяется ФАКТ: платформа видит это устройство.
    код, т = зов(ЯДРО, "/api/targets/search", {"query": "bench"})
    если_есть = код == 200 and "bench" in т.lower()
    этап(4, "таргет стенда виден платформе",
         если_есть, f"HTTP {код}" + ("" if если_есть else " · таргет не найден — листенер не зарегистрировался"))

    # 5. Покупка. Поток дочитывается до done: running — не результат.
    код, т = зов(ОС, f"/api/purchase-stream/{вид}", {}, таймаут=600)
    куплено = код == 200 and '"type": "done"' in т.replace("'", '"')
    этап(5, "покупка и развёртывание",
         куплено, f"HTTP {код} · " + " ".join(т.split())[-160:])

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

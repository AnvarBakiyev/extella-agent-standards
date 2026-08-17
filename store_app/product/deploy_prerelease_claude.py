#!/usr/bin/env python3
"""Создать ОТДЕЛЬНЫЙ предрелизный листинг гида с кнопкой Claude.

Почему отдельный листинг, а не версия живого: у опубликованного листинга
`published` принадлежит листингу, а не версии (H20), поэтому add-version там —
это публичный релиз, и промежутка «залил, посмотрел, потом опубликовал» не
существует. Предрелиз проверяемого нового делается отдельным листингом.

Живой листинг «Разработка на Extella» этот скрипт не трогает вовсе: его id
здесь используется только для чтения source-agent.

По умолчанию только показывает план. Покупку себе не делает: она создаёт
запись, из-за которой листинг больше нельзя удалить, — это отдельное решение.

    python3 deploy_prerelease_claude.py            — план
    python3 deploy_prerelease_claude.py --выполнить
"""

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

OS_BASE = "https://os.extella.ai"
CORE_BASE = "https://api.extella.ai"
LIVE_LISTING_ID = "880d12e4-f082-486e-b92a-57e4eb09866d"
NAME = "Разработка на Extella — предрелиз 3.1.3"
DESCRIPTION = (
    "Предрелиз для приёмки владельцем. Добавлена кнопка «Подключить Claude» "
    "и исправлен раздел 09. Живой продукт не затронут."
)
VERSION = "3.2.5"
SCOPES = ["expert.run", "device.run"]
# publish-stream требует хотя бы один тег: без него он отвечает HTTP 400.
# У живого листинга теги пустые, потому что он создавался другим путём.
TAGS = ["prerelease", "claude", "codex", "bridge"]
# add-version тоже требует минимум один тег, а у живого листинга они пустые:
# он создавался, когда это поле ещё не было обязательным. Значит теги придётся
# завести, и они видны покупателю — поэтому описательные, а не служебные.
LIVE_TAGS = ["guide", "standards", "codex", "claude"]
# Абсолютный путь к рабочей ветке моста: относительный отсчёт от этого файла
# уводил в соседний каталог и срывал запуск уже после начала записи.
# Слитый main, а не рабочий worktree. Пока путь смотрел в worktree, деплой
# писал в магазин старый Expert, отчитывался «сверено посимвольно» — сверял он
# копию с самой собой — и разошёлся с репозиторием незаметно.
CLAUDE_PLUGIN = (
    pathlib.Path.home()
    / "Documents/Codex/extella-codex-bridge/plugins/extella-claude-bridge"
)
EXPERTS = {
    "extella_claude_product_setup": CLAUDE_PLUGIN / "experts/extella_claude_product_setup.py",
}
HERE = pathlib.Path(__file__).resolve().parent
PAGE = HERE.parent / "index.html"
# Локальная часть: без неё этап bridge не находит рантайм на машине покупателя.
ARCHIVE = CLAUDE_PLUGIN / "dist" / "extella-claude-bridge-archive.zip"


class DeployError(Exception):
    pass


def token() -> str:
    for path in (
        pathlib.Path.home() / ".extella" / "os_token.txt",
        pathlib.Path.home() / ".extella" / "api_token.txt",
    ):
        if path.exists() and path.read_text().strip():
            return path.read_text().strip()
    raise DeployError("не найден локальный токен Extella")


def request(base, path, *, body=None, fields=None, files=None, headers=None, timeout=600):
    request_headers = {"X-Extella-Token": token()}
    request_headers.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    elif fields is not None or files is not None:
        boundary = uuid.uuid4().hex
        chunks = []
        for key, value in (fields or {}).items():
            chunks.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
            )
        for key, path_value in (files or {}).items():
            file_path = pathlib.Path(path_value)
            chunks.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"; "
                f"filename=\"{file_path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
                + file_path.read_bytes() + b"\r\n"
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        data = b"".join(chunks)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(base + path, data=data, headers=request_headers,
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:600]
    except (TimeoutError, urllib.error.URLError):
        return 599, ""


def as_json(raw, label="ответ"):
    try:
        value = json.loads(raw)
    except Exception as error:
        raise DeployError(f"{label} пришёл не в JSON") from error
    if not isinstance(value, dict):
        raise DeployError(f"{label} пришёл неверной формы")
    return value


def stream_done(raw, label):
    done = None
    for line in raw.splitlines():
        if not line.strip().startswith("data:"):
            continue
        event = as_json(line.strip()[5:].strip(), label)
        if event.get("type") == "error":
            raise DeployError(str(event.get("message") or f"{label}: ошибка"))
        if event.get("type") == "done":
            done = event
    if done is None:
        raise DeployError(f"{label}: поток оборвался без done; перечитай состояние, не повторяй")
    return done


def listings():
    status, raw = request(OS_BASE, "/api/my-listings")
    if status != 200:
        raise DeployError(f"список листингов ответил {status}")
    return as_json(raw).get("listings", [])


def source_agent(items):
    live = next((x for x in items if x.get("id") == LIVE_LISTING_ID), None)
    if not live or not live.get("versions"):
        raise DeployError("живой листинг или его версия-источник не найдены")
    agent = str(live["versions"][-1].get("source_id") or "")
    if not agent.startswith("agent_"):
        raise DeployError("канонический source-agent не найден")
    return agent


def expert_code(payload):
    if isinstance(payload, dict):
        for key in ("expert_code", "code"):
            if isinstance(payload.get(key), str):
                return payload[key]
        for key in ("content", "data", "result", "expert"):
            found = expert_code(payload.get(key))
            if found:
                return found
    return ""


def prepare_experts(agent_id):
    """Записать установочные Expert'ы в source-agent и сверить посимвольно.

    Сверка читает содержимое, а не флаг: платформа пишет одним набором полей,
    а отдаёт другим, и проверка «по интуиции» здесь всегда зелёная.
    """
    headers = {"X-Auth-Token": token(), "X-Profile-Id": "default", "X-Agent-Id": agent_id}
    for name, path in EXPERTS.items():
        if not path.is_file():
            raise DeployError(f"нет файла Expert: {path}")
        code = path.read_text(encoding="utf-8").rstrip()
        status, raw = request(CORE_BASE, "/api/expert/save", body={
            "name": name,
            "description": "Установить и проверить локальный мост Extella без запуска модели.",
            "code": code, "cspl": "fython", "global": False,
            "kwargs": {"action": "status", "marketplace_path": ""},
        }, headers=headers)
        if status != 200 or as_json(raw).get("status") == "error":
            raise DeployError(f"{name}: Expert не сохранён, HTTP {status}")
        status, raw = request(CORE_BASE, "/api/expert/get",
                              body={"name": name, "global": False}, headers=headers)
        if status != 200 or expert_code(as_json(raw)).strip() != code:
            raise DeployError(f"{name}: после записи содержимое отличается от файла")
        print(f"  Expert {name}: записан и сверен посимвольно ({len(code)} символов)")


def add_version_to_live(agent_id, items):
    """Добавить версию в живой листинг.

    H20: `published` принадлежит листингу, а не версии, поэтому версия
    становится публичной в момент попадания. Отката «снять с витрины» у версии
    нет — есть только удаление. Поэтому шаг требует явного решения владельца
    и отдельного флага, а не подразумевается.
    """
    live = next(x for x in items if x.get("id") == LIVE_LISTING_ID)
    if any(v.get("version") == VERSION for v in live.get("versions", [])):
        raise DeployError(f"версия {VERSION} уже существует; перечитай состояние, не повторяй")
    fields = {
        "version": VERSION,
        "price_credits": "0",
        "app_scopes": json.dumps(SCOPES),
        "source_id": agent_id,
        "source_type": "agent",
        "attach_agent": "1",
        "tags": json.dumps(LIVE_TAGS, ensure_ascii=False),
    }
    if not ARCHIVE.is_file():
        raise DeployError(f"нет собранного архива {ARCHIVE.name}: сначала build-archive.mjs")
    status, raw = request(OS_BASE, f"/api/add-version-stream/{LIVE_LISTING_ID}",
                          fields=fields, files={"page": PAGE, "archive": ARCHIVE})
    if status != 200:
        raise DeployError(f"добавление версии ответило HTTP {status}: {raw[:200]}")
    return stream_done(raw, "добавление версии")


def verify_live():
    items = listings()
    live = next(x for x in items if x.get("id") == LIVE_LISTING_ID)
    version = next((v for v in live.get("versions", []) if v.get("version") == VERSION), None)
    if version is None:
        raise DeployError("версия не читается обратно")
    scopes = version.get("app_scopes") or []
    if isinstance(scopes, str):
        scopes = json.loads(scopes)
    problems = []
    if set(scopes) != set(SCOPES):
        problems.append(f"права {scopes} вместо {SCOPES}")
    if int(version.get("expert_count") or 0) < 1:
        problems.append("Expert не приложился")
    if not version.get("archive_ext"):
        problems.append("к версии не приложился архив — рантайм не доедет до покупателя")
    status, page = request(OS_BASE, f"/app-page/{LIVE_LISTING_ID}/")
    if status != 200:
        problems.append(f"страница отдаётся с кодом {status}")
    elif "{" + "{app_token" in page:
        problems.append("плейсхолдер токена не подставлен")
    elif 'id="claude-connect"' not in page:
        problems.append("кнопки Claude нет в отданной странице")
    if problems:
        raise DeployError("приёмка не прошла: " + "; ".join(problems))
    print(f"  версия {VERSION} подтверждена чтением: права {sorted(scopes)}, "
          f"Expert приложен, страница отдаётся с кнопкой Claude")


def create_prerelease(agent_id):
    fields = {
        "version": VERSION,
        "price_credits": "0",
        "app_scopes": json.dumps(SCOPES),
        "name": NAME,
        "description": DESCRIPTION,
        "source_id": agent_id,
        "source_type": "agent",
        "attach_agent": "1",
        "tags": json.dumps(TAGS, ensure_ascii=False),
    }
    status, raw = request(OS_BASE, "/api/publish-stream", fields=fields, files={"page": PAGE})
    if status != 200:
        raise DeployError(f"создание листинга ответило HTTP {status}: {raw[:200]}")
    done = stream_done(raw, "создание предрелизного листинга")
    return done


def verify(listing_id):
    items = listings()
    made = next((x for x in items if x.get("id") == listing_id), None)
    if made is None:
        raise DeployError("созданный листинг не читается обратно")
    if made.get("published") is True:
        raise DeployError("листинг оказался опубликованным — это не предрелиз")
    version = (made.get("versions") or [{}])[-1]
    scopes = version.get("app_scopes") or []
    if isinstance(scopes, str):
        scopes = json.loads(scopes)
    problems = []
    if set(scopes) != set(SCOPES):
        problems.append(f"права {scopes} вместо {SCOPES}")
    if int(version.get("expert_count") or 0) < 1:
        problems.append("Expert не приложился")
    status, page = request(OS_BASE, f"/app-page/{listing_id}/")
    if status != 200:
        problems.append(f"страница отдаётся с кодом {status}")
    elif "{" + "{app_token" in page:
        problems.append("плейсхолдер токена не подставлен")
    elif 'id="claude-connect"' not in page:
        problems.append("кнопки Claude нет в отданной странице")
    if problems:
        raise DeployError("приёмка не прошла: " + "; ".join(problems))
    print(f"  предрелиз подтверждён чтением: published={made.get('published')}, "
          f"права {sorted(scopes)}, Expert приложен, страница отдаётся с кнопкой Claude")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--выполнить", action="store_true")
    parser.add_argument("--в-живой-листинг", dest="в_живой", action="store_true",
                        help="добавить версию в опубликованный листинг: она станет "
                             "публичной немедленно (H20)")
    options = parser.parse_args()

    items = listings()
    agent_id = source_agent(items)
    live = next(x for x in items if x.get("id") == LIVE_LISTING_ID)
    twin = [x for x in items if str(x.get("name", "")).startswith("Разработка на Extella —")]

    print(f"живой листинг    : «{live.get('name')}» published={live.get('published')} — НЕ трогаем")
    print(f"source-agent     : {agent_id[:14]}…")
    print(f"страница         : {PAGE.name}, {PAGE.stat().st_size} байт")
    print(f"архив            : {ARCHIVE.name}, {ARCHIVE.stat().st_size if ARCHIVE.is_file() else 0} байт")
    print(f"создать листинг  : «{NAME}» версия {VERSION}, права {SCOPES}, цена 0, теги {TAGS}")
    if twin:
        print(f"ВНИМАНИЕ: похожий предрелиз уже есть ({len(twin)} шт.) — "
              "повтор создаст дубль:")
        for x in twin:
            print(f"   {x.get('id')} published={x.get('published')} «{x.get('name')}»")
    print("покупка себе     : НЕ выполняется (делает листинг неудаляемым)")
    print("публикация       : НЕ выполняется")

    if options.в_живой:
        print(f"\nРЕЖИМ: версия {VERSION} уйдёт в ОПУБЛИКОВАННЫЙ листинг "
              f"«{live.get('name')}» и станет видна всем немедленно.")
        print("Откат — только удаление версии.")
        print(f"Теги листинга: {live.get('tags')} -> {LIVE_TAGS} "
              "(поле стало обязательным, пустым его оставить нельзя)")

    if not options.выполнить:
        print("\nэто план. Повтори с --выполнить")
        return

    if options.в_живой:
        print("\nзаписываю Expert'ы в source-agent…")
        prepare_experts(agent_id)
        print("добавляю версию в живой листинг…")
        done = add_version_to_live(agent_id, items)
        print(f"  версия добавлена · снимок: {done.get('stats')}")
        verify_live()
        print(json.dumps({"status": "version_added", "listing_id": LIVE_LISTING_ID,
                          "version": VERSION, "version_id": done.get("version_id"),
                          "public_immediately": True}, ensure_ascii=False, indent=2))
        return

    if twin:
        raise DeployError("предрелиз с таким именем уже существует; дубль не создаю")
    print("\nзаписываю Expert'ы в source-agent…")
    prepare_experts(agent_id)
    print("создаю предрелизный листинг…")
    done = create_prerelease(agent_id)
    listing_id = done["listing_id"]
    print(f"  листинг создан: {listing_id} · снимок: {done.get('stats')}")
    verify(listing_id)
    print(json.dumps({"status": "prerelease_created", "listing_id": listing_id,
                      "version_id": done.get("version_id"), "published": False,
                      "purchased": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except DeployError as error:
        print(f"deploy_prerelease_claude: {error}", file=sys.stderr)
        sys.exit(1)

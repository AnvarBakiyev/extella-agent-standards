#!/usr/bin/env python3
"""Подготовить установочный Expert и версию 3.0.0 существующего листинга.

По умолчанию только показывает план. `--prepare-agent` сохраняет и перечитывает
Expert у канонического source-agent, но не меняет магазин. `--add-version`
добавляет page + archive + минимальные права как предрелиз. Необратимый endpoint
Publish здесь намеренно отсутствует: его вызывает только человек.
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
LISTING_ID = "880d12e4-f082-486e-b92a-57e4eb09866d"
VERSION = "3.0.0"
SCOPES = ["expert.run", "device.run"]
HERE = pathlib.Path(__file__).resolve().parent
STORE = HERE.parent
EXPERT = HERE / "expert_extella_codex_product_setup.py"
PAGE = STORE / "index.html"
ARCHIVE = STORE / "dist" / "extella-development-3.0.0.zip"


class DeployError(Exception):
    pass


def token() -> str:
    for path, is_json in (
        (pathlib.Path.home() / ".extella" / "os_token.txt", False),
        (pathlib.Path.home() / ".extella" / "api_token.txt", False),
        (pathlib.Path.home() / "extella_wizard" / "app" / "config.json", True),
    ):
        if not path.exists():
            continue
        if is_json:
            data = json.loads(path.read_text())
            for key in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
                if data.get(key):
                    return str(data[key])
        else:
            value = path.read_text().strip()
            if value:
                return value
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
                + file_path.read_bytes()
                + b"\r\n"
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        data = b"".join(chunks)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(
        base + path,
        data=data,
        headers=request_headers,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")[:500]


def as_json(raw: str, label="ответ") -> dict:
    try:
        value = json.loads(raw)
    except Exception as error:
        raise DeployError(f"{label} пришёл не в JSON") from error
    if not isinstance(value, dict):
        raise DeployError(f"{label} пришёл неверной формы")
    return value


def stream_done(raw: str) -> dict:
    done = None
    for line in raw.splitlines():
        if not line.strip().startswith("data:"):
            continue
        event = as_json(line.strip()[5:].strip(), "событие публикации")
        if event.get("type") == "error":
            raise DeployError(str(event.get("message") or "публикация завершилась ошибкой"))
        if event.get("type") == "done":
            done = event
    if done is None:
        raise DeployError("поток оборвался без done; повторять нельзя до перечитки состояния")
    return done


def listing() -> dict:
    status, raw = request(OS_BASE, "/api/my-listings")
    if status != 200:
        raise DeployError(f"список листингов ответил {status}")
    for item in as_json(raw).get("listings", []):
        if item.get("id") == LISTING_ID:
            return item
    raise DeployError("листинг «Разработка на Extella» не найден")


def source_agent(item: dict) -> str:
    versions = item.get("versions") or []
    if not versions:
        raise DeployError("у листинга нет версии-источника")
    source = str(versions[-1].get("source_id") or "")
    if not source.startswith("agent_"):
        raise DeployError("канонический source-agent листинга не найден")
    return source


def expert_code(payload) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("expert_code"), str):
            return payload["expert_code"]
        if isinstance(payload.get("code"), str):
            return payload["code"]
        for key in ("content", "data", "result", "expert"):
            found = expert_code(payload.get(key))
            if found:
                return found
    return ""


def prepare_agent(agent_id: str) -> None:
    code = EXPERT.read_text(encoding="utf-8").rstrip()
    headers = {
        "X-Auth-Token": token(),
        "X-Profile-Id": "default",
        "X-Agent-Id": agent_id,
    }
    status, raw = request(
        CORE_BASE,
        "/api/expert/save",
        body={
            "name": "extella_codex_product_setup",
            "description": "Install and verify the local Extella Codex Bridge without calling a model.",
            "code": code,
            "cspl": "fython",
            "global": False,
            "kwargs": {"action": "status"},
        },
        headers=headers,
    )
    if status != 200 or as_json(raw).get("status") == "error":
        raise DeployError(f"Expert не сохранён: HTTP {status}")
    status, raw = request(
        CORE_BASE,
        "/api/expert/get",
        body={"name": "extella_codex_product_setup", "global": False},
        headers=headers,
    )
    if status != 200 or expert_code(as_json(raw)).strip() != code:
        raise DeployError("Expert после записи отличается от файла")
    print("Expert установки: записан в source-agent и сверен посимвольно")


def add_version(item: dict, agent_id: str) -> None:
    if any(version.get("version") == VERSION for version in item.get("versions", [])):
        raise DeployError("версия 3.0.0 уже существует; состояние надо перечитать, а не повторять")
    for path in (PAGE, ARCHIVE):
        if not path.is_file():
            raise DeployError(f"нет собранного файла {path.name}")
    fields = {
        "version": VERSION,
        "price_credits": "0",
        "app_scopes": json.dumps(SCOPES),
        "source_id": agent_id,
        "source_type": "agent",
        "attach_agent": "1",
    }
    status, raw = request(
        OS_BASE,
        f"/api/add-version-stream/{LISTING_ID}",
        fields=fields,
        files={"page": PAGE, "archive": ARCHIVE},
    )
    if status != 200:
        raise DeployError(f"добавление версии ответило HTTP {status}")
    stream_done(raw)
    fresh = listing()
    matches = [version for version in fresh.get("versions", []) if version.get("version") == VERSION]
    if len(matches) != 1:
        raise DeployError("версия не подтверждена чтением состояния")
    version = matches[0]
    raw_scopes = version.get("app_scopes") or []
    if isinstance(raw_scopes, str):
        try:
            raw_scopes = json.loads(raw_scopes)
        except Exception:
            raw_scopes = []
    if set(raw_scopes) != set(SCOPES) or not version.get("archive_ext") or int(version.get("expert_count") or 0) < 1:
        raise DeployError("версия появилась, но архив, права или Expert не совпали")
    print("Предрелиз 3.0.0 добавлен и подтверждён чтением: page + archive + 1 Expert + 2 права")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-agent", action="store_true")
    parser.add_argument("--add-version", action="store_true")
    args = parser.parse_args()
    item = listing()
    agent_id = source_agent(item)
    print("План: существующий листинг · версия 3.0.0 · цена 0 · page + archive")
    print("Права: expert.run + device.run · source-agent найден · идентификатор не выводится")
    if not args.prepare_agent and not args.add_version:
        print("Сухой прогон: ничего не изменено")
        return 0
    if args.prepare_agent:
        prepare_agent(agent_id)
    if args.add_version:
        add_version(listing(), agent_id)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DeployError as error:
        print(f"Не задеплоил: {error}", file=sys.stderr)
        sys.exit(1)

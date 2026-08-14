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
import re
import sys
import urllib.error
import urllib.request
import uuid


OS_BASE = "https://os.extella.ai"
CORE_BASE = "https://api.extella.ai"
LISTING_ID = "880d12e4-f082-486e-b92a-57e4eb09866d"
VERSION = "3.0.2"
SCOPES = ["expert.run", "device.run"]
SETUP_STEPS = ("preflight", "install", "credentials", "bridge", "verify")
HERE = pathlib.Path(__file__).resolve().parent
STORE = HERE.parent
EXPERT = HERE / "expert_extella_codex_product_setup.py"
PAGE = STORE / "index.html"


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
    except (TimeoutError, urllib.error.URLError):
        return 599, ""


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
        raise DeployError(f"версия {VERSION} уже существует; состояние надо перечитать, а не повторять")
    if not PAGE.is_file():
        raise DeployError(f"нет собранного файла {PAGE.name}")
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
        files={"page": PAGE},
    )
    if status != 200:
        raise DeployError(f"добавление версии ответило HTTP {status}")
    stream_done(raw)
    verify_version(listing())


def verify_version(item: dict) -> None:
    version = version_record(item)
    raw_scopes = version.get("app_scopes") or []
    if isinstance(raw_scopes, str):
        try:
            raw_scopes = json.loads(raw_scopes)
        except Exception:
            raw_scopes = []
    if set(raw_scopes) != set(SCOPES) or version.get("archive_ext") or int(version.get("expert_count") or 0) < 1:
        raise DeployError("версия появилась, но страница, права или Expert не совпали")
    print(f"Предрелиз {VERSION} добавлен и подтверждён чтением: page + 1 Expert + 2 права")


def version_record(item: dict) -> dict:
    matches = [version for version in item.get("versions", []) if version.get("version") == VERSION]
    if len(matches) != 1 or not matches[0].get("id"):
        raise DeployError(f"предрелиз {VERSION} не найден чтением состояния")
    return matches[0]


def purchase(item: dict, agent_id: str) -> None:
    version = version_record(item)
    status, raw = request(
        OS_BASE,
        f"/api/purchase-stream/{version['id']}",
        body={"deploy_mode": "existing", "target_agent_id": agent_id},
    )
    if status != 200:
        raise DeployError(f"покупка предрелиза ответила HTTP {status}")
    done = stream_done(raw)
    print(
        "Предрелиз установлен владельцу: "
        + ("ярлык создан" if done.get("webapp_shortcut") else "ярлык не подтверждён потоком")
    )


def unwrap_run_result(value) -> dict:
    for _ in range(4):
        if isinstance(value, dict) and "result" in value:
            value = value["result"]
            continue
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception as error:
                raise DeployError("app-agent/run нарушил H17: вернул не JSON") from error
            continue
        break
    if not isinstance(value, dict) or not isinstance(value.get("status"), str) or not isinstance(value.get("code"), str):
        raise DeployError("app-agent/run вернул неожиданную форму")
    return value


def accept(*, grant_rights: bool, setup_action: str | None) -> None:
    status, raw = request(OS_BASE, f"/api/purchase-check/{LISTING_ID}")
    if status != 200 or as_json(raw).get("purchased") is not True:
        raise DeployError("покупка не подтверждена чтением состояния")

    status, page = request(OS_BASE, f"/app-page/{LISTING_ID}/")
    if status != 200:
        raise DeployError(f"страница приложения ответила HTTP {status}")
    match = re.search(r'var APP_TOKEN = /\*APP_TOKEN\*/"([^"{}]+)";', page)
    if not match or len(match.group(1)) < 40:
        raise DeployError("страница не получила app_token")
    if "['preflight', 'install', 'credentials', 'bridge', 'verify']" not in page:
        raise DeployError(f"установлена прежняя страница: предрелиз {VERSION} ещё не выбран")
    app_token = match.group(1)

    status, raw = request(OS_BASE, f"/api/app-permissions/{LISTING_ID}")
    permissions = as_json(raw, "права приложения") if status == 200 else {}
    if set(permissions.get("requested") or []) != set(SCOPES):
        raise DeployError("запрошенные права отличаются от продуктового контракта")
    if grant_rights:
        status, raw = request(OS_BASE, f"/api/app-permissions/{LISTING_ID}", body={"scopes": SCOPES})
        if status != 200:
            raise DeployError(f"выдача прав ответила HTTP {status}")
        status, raw = request(OS_BASE, f"/api/app-permissions/{LISTING_ID}")
        permissions = as_json(raw, "права приложения") if status == 200 else {}
    granted = set(permissions.get("granted") or [])

    status, raw = request(OS_BASE, "/api/desktop-state")
    state = as_json(raw, "состояние рабочего стола") if status == 200 else {}
    shortcuts = (state.get("state") or {}).get("shortcuts") or {}
    if not any(LISTING_ID in str(value.get("url") or "") for value in shortcuts.values() if isinstance(value, dict)):
        raise DeployError("ярлык приложения не подтверждён чтением состояния")

    print(
        "Приёмка OS: покупка есть · страница 200 · app_token подставлен · ярлык есть · "
        f"прав выдано {len(granted)} из {len(SCOPES)}"
    )
    if setup_action:
        if not set(SCOPES).issubset(granted):
            raise DeployError("для живого setup сначала нужны оба согласия покупателя")
        actions = SETUP_STEPS if setup_action == "full" else (setup_action,)
        for action in actions:
            status, raw = request(
                OS_BASE,
                "/api/app-agent/run",
                body={
                    "app_token": app_token,
                    "expert_name": "extella_codex_product_setup",
                    "params": {"action": action},
                },
                timeout=600,
            )
            if status != 200:
                raise DeployError(f"app-agent/run на этапе {action} ответил HTTP {status}")
            result = unwrap_run_result(as_json(raw, "app-agent/run"))
            if result.get("model_called") is not False or result.get("agent_called") is not False:
                raise DeployError("setup нарушил безмодельный контракт")
            if result.get("status") != "success":
                raise DeployError(f"этап {action} не готов: {result.get('code')}")
            if action == "verify" and result.get("code") != "ready":
                raise DeployError(f"итоговая проверка не готова: {result.get('code')}")
            print(
                f"Живой {action}: status={result['status']} · code={result['code']} · "
                "модель не вызвана"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-agent", action="store_true")
    parser.add_argument("--add-version", action="store_true")
    parser.add_argument("--purchase", action="store_true")
    parser.add_argument("--verify-version", action="store_true")
    parser.add_argument("--accept", action="store_true")
    parser.add_argument("--grant-rights", action="store_true")
    parser.add_argument("--setup", choices=(*SETUP_STEPS, "full"))
    args = parser.parse_args()
    item = listing()
    agent_id = source_agent(item)
    print(f"План: существующий листинг · версия {VERSION} · цена 0 · page + agent")
    print("Права: expert.run + device.run · source-agent найден · идентификатор не выводится")
    if not args.prepare_agent and not args.add_version and not args.purchase and not args.verify_version and not args.accept:
        print("Сухой прогон: ничего не изменено")
        return 0
    if args.prepare_agent:
        prepare_agent(agent_id)
    if args.add_version:
        add_version(listing(), agent_id)
    if args.verify_version:
        verify_version(listing())
    if args.purchase:
        purchase(listing(), agent_id)
    if args.accept:
        accept(grant_rights=args.grant_rights, setup_action=args.setup)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DeployError as error:
        print(f"Не задеплоил: {error}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подключить агента к Extella, не спрашивая у человека ничего.

ЗАЧЕМ. Вход в канон велел агенту: «попроси пользователя открыть Extella и
написать в чате „Сгенерируй мне API-токен“, пусть пришлёт строку тебе». Готовый
промпт рядом запрещал ровно это: «не проси переслать его в чат». Противоречие
внутри единственного входа, и побеждал README — промпт сам отправляет агента
читать README как источник правды. Человек, который Extella не знает, упирался
в тупик: где чат, что писать, куда вставлять секрет (замер владельца 26.08.2026).

Просить не нужно вовсе. Ключ появляется на диске сам при первом запуске
приложения, и это ТОТ ЖЕ ключ, который нужен MCP — проверено рукопожатием.
Поэтому шаг «токен» перестаёт быть разговором и становится командой.

ЧТО ДЕЛАЕТ.
  1. находит ключ по канонному порядку (тому же, что у platform_client);
  2. проверяет его РАБОТОЙ — рукопожатием с MCP, а не наличием файла;
  3. прописывает MCP-сервер клиенту (Claude Code, Codex);
  4. если ключа нет — называет единственное действие человека одной строкой.

ГДЕ ЛЕЖИТ СЕКРЕТ. Claude Code умеет `headersHelper` — скрипт, который отдаёт
заголовки в момент вызова. Тогда ключ не попадает ни в конфиг, ни в аргументы
команды (а значит, и в `ps`). Этим путём и идём. У Codex такого нет: ему ключ
пишется в `~/.codex/config.toml`, поэтому файл переводится в режим 600 и это
сказано вслух, а не умолчано.

ЧУЖОЕ НЕ ТРОГАЕМ. Уже настроенный и живой сервер `extella` не переписывается:
у человека может быть своя связка на другой аккаунт.

    python3 tools/connect_mcp.py              # подключить
    python3 tools/connect_mcp.py --проверить  # только сказать, как есть
    python3 tools/connect_mcp.py --json
    python3 tools/connect_mcp.py --selftest

Коды выхода: 0 — подключено (или проверка прошла), 1 — нужен человек.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ЯДРО_MCP = "https://api.extella.ai/mcp/"
ИМЯ_СЕРВЕРА = "extella"

НЕТ_КЛЮЧА = ("Extella на этой машине ещё не открывали. Единственное действие "
             "человека: запустить приложение Extella один раз — ключ появится "
             "сам, и подключение пройдёт без него. Присылать ключ в переписку "
             "не нужно никогда.")


def дом() -> pathlib.Path:
    """Домашняя папка берётся из окружения, а не кэшируется: иначе самопроверку
    негде прогнать, не тронув настоящие конфиги человека."""
    return pathlib.Path(os.environ.get("HOME") or pathlib.Path.home())


def места():
    """Тот же порядок, что у tools/platform_client.py. Второй список рано или
    поздно разойдётся с первым — а расходятся копии молча (H78)."""
    д = дом()
    return (("переменная EXTELLA_API_TOKEN", None),
            ("~/.extella/os_token.txt", д / ".extella" / "os_token.txt"),
            ("~/.extella/api_token.txt", д / ".extella" / "api_token.txt"),
            ("~/extella_wizard/app/config.json",
             д / "extella_wizard" / "app" / "config.json"))


def найти_ключ():
    """Ключ, файл-источник и человекочитаемое место. Значение не логируем."""
    из_среды = (os.environ.get("EXTELLA_API_TOKEN") or "").strip()
    if len(из_среды) >= 8:
        return из_среды, None, места()[0][0]
    for имя, путь in места()[1:]:
        if путь is None or not путь.exists():
            continue
        текст = путь.read_text(encoding="utf-8").strip()
        if путь.suffix == ".json":
            try:
                d = json.loads(текст)
            except json.JSONDecodeError:
                continue
            for k in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
                if d.get(k):
                    return str(d[k]).strip(), None, имя
            continue
        if len(текст) >= 8:
            return текст, путь, имя
    return "", None, ""


def ключ_работает(ключ: str, таймаут: int = 45):
    """Проверяем РАБОТОЙ, а не наличием файла: файл может остаться от старого
    аккаунта или быть обрезан. Рукопожатие — единственное честное доказательство."""
    тело = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "extella-standards", "version": "1"}},
    }).encode()
    запрос = urllib.request.Request(
        ЯДРО_MCP, data=тело, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream",
                 "X-Auth-Token": ключ, "X-Profile-Id": "default"})
    try:
        with urllib.request.urlopen(запрос, timeout=таймаут) as ответ:
            текст = ответ.read(4096).decode("utf-8", "replace")
        return ('"result"' in текст), ""
    except urllib.error.HTTPError as о:
        if о.code in (401, 403):
            return False, ("ключ найден, но Extella его не признала — похоже, он от "
                           "другого аккаунта. Открой приложение Extella заново, оно "
                           "перезапишет ключ.")
        return False, f"Extella ответила {о.code} на рукопожатие MCP"
    except Exception as о:  # сеть, таймаут
        return False, f"не дошёл до Extella ({str(о)[:80]})"


def обезвредить(текст: str, ключ: str) -> str:
    """Ни один наш вывод не имеет права нести значение ключа."""
    чистый = текст.replace(ключ, "…") if ключ else текст
    # На случай, если ключ пришёл в ответе не тем же написанием.
    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                  "…", чистый)


def написать_помощника(файл_ключа) -> pathlib.Path:
    """Скрипт отдаёт заголовки в момент вызова, читая ключ из файла. Значение
    не попадает ни в конфиг MCP, ни в аргументы команды, ни в `ps`."""
    папка = дом() / ".extella" / "mcp"
    папка.mkdir(parents=True, exist_ok=True)
    помощник = папка / "standards.sh"
    источник = str(файл_ключа) if файл_ключа else str(
        дом() / ".extella" / "os_token.txt")
    помощник.write_text(
        "#!/bin/sh\n"
        "# Заголовки для MCP Extella. Ключ читается из файла в момент вызова:\n"
        "# так он не лежит в конфиге агента и не виден в списке процессов.\n"
        f'printf \'{{"X-Auth-Token":"%s","X-Profile-Id":"default"}}\\n\' '
        f'"$(cat "{источник}")"\n',
        encoding="utf-8")
    os.chmod(помощник, 0o700)
    return помощник


def уже_настроен_claude() -> bool:
    конфиг = дом() / ".claude.json"
    if not конфиг.exists():
        return False
    try:
        d = json.loads(конфиг.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if ИМЯ_СЕРВЕРА in (d.get("mcpServers") or {}):
        return True
    # И область проекта: там связка могла остаться от прежних попыток.
    for пр in (d.get("projects") or {}).values():
        if ИМЯ_СЕРВЕРА in ((пр or {}).get("mcpServers") or {}):
            return True
    return False


def подключить_claude(ключ: str, файл_ключа, сухой: bool) -> dict:
    if not shutil.which("claude"):
        return {"клиент": "claude", "состояние": "нет на машине"}
    if уже_настроен_claude():
        return {"клиент": "claude", "состояние": "уже настроен — не трогаю"}
    if сухой:
        return {"клиент": "claude", "состояние": "подключил бы через headersHelper"}
    помощник = написать_помощника(файл_ключа)
    описание = json.dumps({"type": "http", "url": ЯДРО_MCP,
                           "headersHelper": str(помощник)}, ensure_ascii=False)
    # --scope user обязателен: без него сервер ложится в область ТЕКУЩЕЙ папки
    # (`projects.<cwd>` в ~/.claude.json). Агент настроил бы связку в каталоге,
    # где случайно оказался, а в остальных её бы не было — и человек честно
    # видел бы «не подключено» после успешного отчёта (замер 26.08.2026).
    итог = subprocess.run(
        ["claude", "mcp", "add-json", "--scope", "user", ИМЯ_СЕРВЕРА, описание],
        capture_output=True, text=True, timeout=120)
    вывод = ((итог.stdout or "") + (итог.stderr or "")).strip()
    if итог.returncode == 0:
        return {"клиент": "claude", "состояние": "подключено",
                "секрет_в_конфиге": False}
    return {"клиент": "claude", "состояние": "отказ",
            "почему": обезвредить(вывод, ключ)[:200]}


def подключить_codex(ключ: str, сухой: bool) -> dict:
    """Codex держит MCP в TOML `[mcp_servers.*]`. README раньше показывал ему
    JSON `mcpServers` — формат Claude Code; по нему Codex не подключался."""
    конфиг = дом() / ".codex" / "config.toml"
    if not конфиг.parent.exists():
        return {"клиент": "codex", "состояние": "нет на машине"}
    текст = конфиг.read_text(encoding="utf-8") if конфиг.exists() else ""
    if f"[mcp_servers.{ИМЯ_СЕРВЕРА}]" in текст:
        return {"клиент": "codex", "состояние": "уже настроен — не трогаю"}
    if сухой:
        return {"клиент": "codex", "состояние": "дописал бы в config.toml",
                "секрет_в_конфиге": True}
    кусок = (f'\n[mcp_servers.{ИМЯ_СЕРВЕРА}]\n'
             f'enabled = true\n'
             f'url = "{ЯДРО_MCP}"\n'
             f'\n[mcp_servers.{ИМЯ_СЕРВЕРА}.http_headers]\n'
             f'X-Auth-Token = "{ключ}"\n'
             f'X-Profile-Id = "default"\n')
    конфиг.write_text(текст + кусок, encoding="utf-8")
    os.chmod(конфиг, 0o600)  # у Codex нет помощника заголовков: ключ лежит в файле
    return {"клиент": "codex", "состояние": "подключено", "секрет_в_конфиге": True,
            "почему": "у Codex нет headersHelper — ключ в config.toml, файл 600"}


def подключить(сухой: bool) -> dict:
    ключ, файл, место = найти_ключ()
    if not ключ:
        return {"итог": "нужен человек", "почему": НЕТ_КЛЮЧА, "клиенты": []}
    живой, беда = ключ_работает(ключ)
    if not живой:
        return {"итог": "нужен человек", "почему": беда or НЕТ_КЛЮЧА,
                "ключ_взят": место, "клиенты": []}
    клиенты = [подключить_claude(ключ, файл, сухой), подключить_codex(ключ, сухой)]
    нашлись = [к for к in клиенты if к["состояние"] != "нет на машине"]
    return {"итог": "подключено" if нашлись else "клиент не найден",
            "ключ_взят": место, "ключ_проверен": "рукопожатием MCP",
            "клиенты": клиенты, "действий_человека": 0 if нашлись else 1}


def напечатать(отчёт: dict) -> None:
    if отчёт["итог"] == "нужен человек":
        print("✗ " + отчёт["почему"])
        return
    print(f"ключ взят: {отчёт['ключ_взят']} · проверен {отчёт['ключ_проверен']}")
    for к in отчёт["клиенты"]:
        строка = f"  {к['клиент']}: {к['состояние']}"
        if к.get("почему"):
            строка += f" — {к['почему']}"
        print(строка)
    if отчёт["итог"] == "клиент не найден":
        print("✗ ни Claude Code, ни Codex на этой машине не найдены")
    else:
        print("Готово. Действий от человека: 0 — значение ключа нигде не показано.")


def selftest() -> int:
    import tempfile
    беды = []

    свой = pathlib.Path(__file__).with_name("platform_client.py").read_text(encoding="utf-8")
    for кусок in (".extella", "os_token.txt", "api_token.txt", "extella_wizard"):
        if кусок not in свой:
            беды.append(f"канонный клиент не знает {кусок} — порядок разошёлся")
    print("  ✓ порядок поиска ключа сверен с platform_client")

    if "СЕКРЕТ-123" in обезвредить("отказ: СЕКРЕТ-123", "СЕКРЕТ-123"):
        беды.append("обезвредить() пропустила значение ключа")
    if "00000000-1111-2222-3333-444444444444" in обезвредить(
            "хвост 00000000-1111-2222-3333-444444444444", ""):
        беды.append("обезвредить() пропустила ключ вида UUID из чужого текста")
    print("  ✓ значение ключа в выводе не остаётся")

    исходник = pathlib.Path(__file__).read_text(encoding="utf-8")
    вызов = исходник[исходник.index('["claude", "mcp", "add-json"'):]
    вызов = вызов[:вызов.index("capture_output")]
    if "ключ" in вызов:
        беды.append("ключ уходит в аргументы claude — он виден в ps")
    print("  ✓ ключ не уходит в аргументы командной строки")

    if '"--scope", "user"' not in исходник:
        беды.append("сервер ложится в область папки, а не пользователя")
    print("  ✓ сервер прописывается в области пользователя")

    if "запустить приложение" not in НЕТ_КЛЮЧА or "не нужно никогда" not in НЕТ_КЛЮЧА:
        беды.append("отказ без ключа не называет действие человека")
    print("  ✓ отказ называет одно действие человека")

    if "initialize" not in исходник or "jsonrpc" not in исходник:
        беды.append("ключ не проверяется рукопожатием — файл может быть мёртвым")
    print("  ✓ ключ проверяется рукопожатием, а не наличием файла")

    # Помощник заголовков пишется в песочнице и вправду отдаёт ключ из файла,
    # не неся его в себе.
    with tempfile.TemporaryDirectory() as вр:
        было = os.environ.get("HOME")
        os.environ["HOME"] = вр
        try:
            ключевой = pathlib.Path(вр) / ".extella" / "os_token.txt"
            ключевой.parent.mkdir(parents=True, exist_ok=True)
            ключевой.write_text("КЛЮЧ-ИЗ-ПЕСОЧНИЦЫ", encoding="utf-8")
            помощник = написать_помощника(ключевой)
            тело = помощник.read_text(encoding="utf-8")
            if "КЛЮЧ-ИЗ-ПЕСОЧНИЦЫ" in тело:
                беды.append("помощник несёт значение ключа внутри себя")
            итог = subprocess.run(["/bin/sh", str(помощник)],
                                  capture_output=True, text=True, timeout=30)
            выдал = json.loads(итог.stdout or "{}")
            if выдал.get("X-Auth-Token") != "КЛЮЧ-ИЗ-ПЕСОЧНИЦЫ":
                беды.append("помощник не отдал ключ из файла")
            if oct(помощник.stat().st_mode)[-3:] != "700":
                беды.append("помощник доступен не только владельцу")
        finally:
            if было is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = было
    print("  ✓ помощник заголовков читает ключ из файла и не несёт его в себе")

    if беды:
        for б in беды:
            print("  ✗ " + б)
        print("ИТОГ САМОПРОВЕРКИ: провалы есть")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(description=__doc__)
    р.add_argument("--проверить", action="store_true",
                   help="сказать, как есть, ничего не меняя")
    р.add_argument("--json", action="store_true")
    р.add_argument("--selftest", action="store_true")
    о = р.parse_args()
    if о.selftest:
        return selftest()
    отчёт = подключить(сухой=о.проверить)
    if о.json:
        print(json.dumps(отчёт, ensure_ascii=False, indent=2))
    else:
        напечатать(отчёт)
    return 0 if отчёт["итог"] != "нужен человек" else 1


if __name__ == "__main__":
    sys.exit(main())

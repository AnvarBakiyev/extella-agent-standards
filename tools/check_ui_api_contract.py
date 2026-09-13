#!/usr/bin/env python3
"""Договорились ли интерфейс и сервер об одном и том же.

ЗАЧЕМ. За один день три поломки одного класса, и все внешне разные:

  • «undefined candidates» на карточке — интерфейс читал candidate_count,
    сервер отдаёт candidates_count. Одна буква;
  • карточка вакансии «не открывалась» — сервер отдаёт {status, pool},
    интерфейс ждал список, и первый же .some() ронял отрисовку;
  • карточки паков обещали панель по путям, которых в архивах нет.

Каждый раз обе стороны были в порядке по отдельности. Расходился ДОГОВОР между ними,
и проверить его было нечем: типы никто не объявлял, а падало это молча — пустой экран,
который человек читает как «продукт сломан», а разработчик — как «у меня работает».

ЧТО ПРОВЕРЯЕТ

  1. Каждый метод, который зовёт интерфейс, существует на сервере.
     Отсутствующий метод не роняет страницу — он даёт пустой блок.
  2. Если интерфейс обращается с результатом как со списком (.map/.some/.filter/.length),
     сервер обязан отдавать список. Именно здесь сломалась база кандидатов.

БЕЗОПАСНОСТЬ. Ни один метод не вызывается: список берётся из объявленной поверхности
сервера, форма ответа — только для методов чтения и только через живой сервер, если он
запущен. Гейт не должен ничего менять в продукте, который проверяет.

Коды выхода: 0 — договор соблюдён, 1 — расхождение.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# Продукт задаётся аргументом, а не зашит: один инструмент на все наши продукты
# с локальной панелью. Порт и файл интерфейса берутся из карточки плагина на устройстве,
# если её не передали руками.
#
#   python3 check_ui_api_contract.py <путь-к-продукту> [порт]
#
# Тулбар и плагины — уходящий канал доставки; канонический — Extella OS (решение
# владельца 12.08.2026). Поэтому источник истины об интерфейсе теперь САМ ПРОДУКТ:
# `ui:` в его паспорте (файл + порт). Реестр карточек остаётся необязательным
# запасным источником для продуктов, которые ещё живут в тулбаре, и его отсутствие
# больше не мешает проверке. Путь переопределяется EXTELLA_CARDS_DIR.
REG_DIR = Path(os.environ.get("EXTELLA_CARDS_DIR")
               or Path.home() / "extella-plugins" / "_registry")


# Объявлены явно: до 17.08.2026 они возникали только внутри main(), и самопроверка
# падала на NameError — гейт не мог проверить сам себя.
ROOT = Path.cwd()
BASE = ""


def из_паспорта(root: Path):
    """Интерфейс и порт, объявленные продуктом. Первый источник, не запасной."""
    for имя in ("docs/automation_passport.yaml", "docs/agent_passport.yaml",
                "automation_passport.yaml", "agent_passport.yaml"):
        путь = root / имя
        if not путь.is_file():
            continue
        try:
            import yaml
            doc = yaml.safe_load(путь.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        ui = (doc.get("ui") or (doc.get("automation") or {}).get("ui") or {})
        файл, порт = str(ui.get("file") or ""), str(ui.get("port") or "")
        if файл and (root / файл).exists():
            return root / файл, порт or None
    return None, None


def guess(root: Path, port_arg: str | None):
    """Файл интерфейса и порт: из паспорта продукта, потом карточка, потом обычные места."""
    port = port_arg
    ui, порт_паспорта = из_паспорта(root)
    port = port or порт_паспорта
    for card in (sorted(REG_DIR.glob("*.json")) if (ui is None and REG_DIR.exists()) else []):
        try:
            d = json.loads(card.read_text(encoding="utf-8"))
        except Exception:
            continue
        rp = str((d.get("ui") or {}).get("rootPath") or "").replace("~", str(Path.home()))
        if not rp:
            continue
        rpp = Path(rp).resolve()
        # Карточка может указывать на подкаталог (…/app), а проверяем мы корень продукта:
        # засчитываем совпадение в обе стороны, иначе порт «не находится» на живом сервере.
        same = rpp == root.resolve() or root.resolve() in rpp.parents or rpp in root.resolve().parents
        if same:
            port = port or str((d.get("ui") or {}).get("port") or "")
            main = (d.get("ui") or {}).get("mainFile") or ""
            if main and (root / main).exists():
                ui = root / main
            break
    if ui is None:
        for rel in ("app/app.html", "app/index.html", "app/onboarding.html",
                    "ui/index.html", "index.html", "web/index.html"):
            if (root / rel).exists():
                ui = root / rel
                break
    return ui, port

# Обращение с результатом как со списком: если так, сервер обязан отдать список.
LIST_USE = re.compile(r"\.(map|some|filter|forEach|find|length|slice|sort)\b")

READ_PREFIXES = ("get_", "list_", "load_", "read_", "check_")


def called_methods(text: str) -> dict:
    """Метод → ждёт ли интерфейс список в ответе.

    Смотрим на ПЕРЕМЕННУЮ, в которую положен результат, а не на соседний код: первая
    версия ловила `SETTINGS_DATA.forEach` в двух строках ниже и обвиняла get_api_keys_status,
    где интерфейс на самом деле читает res.keys правильно. Ложное обвинение приучает
    пролистывать красное.
    """
    out = {}
    for m in re.finditer(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+api\(['\"]([a-z0-9_]+)['\"]", text):
        var, name = m.group(1), m.group(2)
        tail = text[m.end(): m.end() + 400]
        uses_list = bool(re.search(r"\b" + re.escape(var) + r"\.(map|some|filter|forEach|find|slice|sort)\b", tail)) \
                    or bool(re.search(r"Array\.isArray\(\s*" + re.escape(var) + r"\s*\)", tail)) \
                    or bool(re.search(r"for\s*\(\s*(?:const|let|var)\s+\w+\s+of\s+" + re.escape(var) + r"\b", tail))
        # Явная обработка обоих видов ответа — это НЕ дефект, а решённый договор:
        #   Array.isArray(x) ? x : (x && Array.isArray(x.pool) ? x.pool : [])
        # Без этой ветки гейт краснел на уже починенном коде и требовал «исправить»
        # то, что исправлено — верный способ приучить себя его игнорировать.
        handled = bool(re.search(r"Array\.isArray\(\s*" + re.escape(var) + r"\s*\)\s*\?", tail)) \
                  and bool(re.search(re.escape(var) + r"\.\w+", tail))
        out[name] = out.get(name, False) or (uses_list and not handled)
    for m in re.finditer(r"api\(['\"]([a-z0-9_]+)['\"]", text):
        out.setdefault(m.group(1), False)
    # Второй способ обращения, который используют другие наши продукты: прямые пути
    # /api/<метод> в fetch. Без этого гейт находил ноль вызовов и объявлял успех —
    # то есть врал зелёным там, где не проверил ничего.
    # Три способа обращения, которые используют наши продукты:
    #   api('метод')            — RPC (Рекрутёр)
    #   fetch('/api/путь')      — REST (Подключения)
    #   post('/x/имя')          — мост Extella (Юрист, Travel Agency)
    # Первая версия знала только первый и находила ноль вызовов у половины продуктов —
    # то есть объявляла успех, не проверив ничего.
    for m in re.finditer(r"['\"`](/(?:api|x)/[a-z0-9_/-]+)(['\"`])", text):
        raw = m.group(1)
        after = text[m.end(): m.end() + 2]
        # Маршрут с параметром собирается конкатенацией: api('/api/jobs/' + id).
        # Голый «/api/jobs» никто не зовёт, и проверять его — значит обвинять продукт
        # в дыре, которой нет: так первая версия нашла две «поломки» у Таргетолога.
        if raw.endswith("/") or after.strip().startswith("+"):
            continue
        route = raw.rstrip("/")
        if route.count("/") >= 2:
            out.setdefault(route, False)             # «/api/...» или «/x/...» = маршрут
    return out



# --- страницы, которые собирает хост (адаптер, 14.08.2026) --------------------
#
# ЗАЧЕМ. Console и ей подобные не зовут /api/… вовсе: страница шлёт хосту сообщение
# {type:'<канал>', action:'<действие>'} и ждёт ответа. Прежний гейт находил ноль
# вызовов и объявлял успех — то есть врал зелёным там, где не проверил НИЧЕГО.
# Это худший вид проверки: она не может упасть.

def вызовы_к_хосту(text: str) -> set:
    """Действия, которые страница шлёт хосту через свою обёртку."""
    # 1. Находим обёртки: функции, которые постят сообщение с полем action.
    обёртки = set()
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(\s*action\b", text):
        обёртки.add(m.group(1))
    if not обёртки and not re.search(r"postMessage\([^)]*\baction\b", text):
        return set()
    # 2. Собираем имена в местах вызова: request('automation_registry_load', …)
    действия = set()
    for имя in обёртки or {"request", "hostCall", "callHost"}:
        for m in re.finditer(re.escape(имя) + r"\(\s*['\"]([a-z0-9_]{3,60})['\"]", text):
            действия.add(m.group(1))
    return действия


def поверхность_хоста(root: Path) -> set:
    """Что умеет та сторона: ключи диспетчера в адаптере или обработчики хоста."""
    имена = set()
    файлы = [f for f in list(root.rglob("*adapter*.py")) + list(root.rglob("*handler*.py"))
             + list(root.rglob("*adapter*.js")) if f.is_file()][:20]
    for f in файлы:
        try:
            текст = f.read_text(errors="ignore")
        except Exception:
            continue
        имена |= set(re.findall(r"действие\s*==\s*['\"]([a-z0-9_]{3,60})['\"]", текст))
        имена |= set(re.findall(r"action\s*==\s*['\"]([a-z0-9_]{3,60})['\"]", текст))
        имена |= set(re.findall(r"case\s+['\"]([a-z0-9_]{3,60})['\"]\s*:", текст))
        имена |= set(re.findall(r"^\s*['\"]([a-z0-9_]{3,60})['\"]\s*:\s*(?:self\.)?_?[a-z]",
                                текст, re.M))
    return имена


def проверить_хост_контракт(root: Path, страница: Path, сказать=print) -> int:
    """Договор страницы с хостом. Возвращает 0/1; 2 — проверять нечего."""
    текст = страница.read_text(errors="ignore")
    зовёт = вызовы_к_хосту(текст)
    if not зовёт:
        return 2
    умеет = поверхность_хоста(root)
    сказать(f"  страница зовёт хост: {len(зовёт)} действий")
    if not умеет:
        сказать("  ✗ не нашёл, ЧЕМ они обслуживаются: ни адаптера, ни обработчиков. "
                "Договор проверить нечем — это не успех, а отсутствие второй стороны")
        return 1
    нет = sorted(зовёт - умеет)
    if нет:
        сказать(f"  ✗ страница зовёт то, чего у адаптера нет: {нет}")
        сказать("    каждое такое действие — пустой блок на экране, а не ошибка: "
                "человек прочитает это как «продукт сломан»")
        return 1
    сказать(f"  договор сходится: все {len(зовёт)} действий обслуживаются")
    return 0


def server_methods() -> set:
    """Публичная поверхность сервера — без единого вызова бизнес-метода."""
    if not BASE:
        return set()
    # Живость проверяем несколькими адресами: /api/state есть не у всех продуктов,
    # и по одному адресу живой сервер объявлялся мёртвым — а тогда гейт молча
    # пропускает самую ценную часть проверки, форму ответов.
    alive = False
    for probe in ("/api/state", "/api/health", "/"):
        try:
            with urllib.request.urlopen(BASE + probe, timeout=8) as r:
                r.read(1)
                alive = True
                break
        except Exception:
            continue
    if not alive:
        return None          # сервер не отвечает — это одна причина
    # Поверхность собрана не из одного файла: часть методов живёт в main.py (окно),
    # часть в api.py. Смотреть только в api.py — значит объявить существующий метод
    # пропавшим: первая версия так и сделала с analyze_cv, который на живом сервере
    # отвечает. Гейт, который врёт о причине, хуже отсутствующего.
    names = set()
    # Поверхность ищем шире одного файла: у продуктов она лежит по-разному
    # (app/api.py, src/<пакет>/server.py, plugin/server.py).
    for src in list(ROOT.rglob("api.py")) + list(ROOT.rglob("main.py")) + list(ROOT.rglob("server.py")):
        if any(part in {".venv", "node_modules", "__pycache__", ".git", "dist"} for part in src.parts):
            continue
        names |= set(re.findall(r"^\s{4}def ([a-z0-9_]+)\s*\(",
                                src.read_text(encoding="utf-8", errors="ignore"), re.M))
    return {n for n in names if not n.startswith("_")}   # пустое множество ≠ мёртвый сервер


def served_routes() -> set:
    """Маршруты, которые сервер объявляет В ИСХОДНИКЕ, — без единого живого вызова.

    Прежняя версия проверяла живой сервер POST-ом с пустым телом — и тем самым
    ИСПОЛНЯЛА обработчики: nego_start запускал настоящую арену переговоров,
    send_email слал настоящее тестовое письмо, а рождённые ими платформенные задачи
    без закрепления разлетались по устройствам аккаунта. Три «загадочные волны
    фоновой работы» 03.08 — с ареной, письмом и паспортом TESTOVA на экране
    владельца — оказались прогонами ЭТОГО гейта (пойманы ловушкой по User-Agent:
    Python-urllib, обход маршрутов по алфавиту). Гейт не имеет права трогать прод,
    который проверяет: существование маршрута читается из исходника, как и вся
    остальная поверхность.
    """
    routes = set()
    for src in list(ROOT.rglob("*.py")):
        if any(part in {".venv", "node_modules", "__pycache__", ".git", "dist", "tests"}
               for part in src.parts):
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"['\"](/(?:api|x)/[a-z0-9_/-]+)['\"]", text):
            routes.add(m.group(1).rstrip("/"))
    return routes


def response_shape(method: str):
    """Форма ответа — только для методов чтения и только если сервер запущен."""
    if not BASE or not method.startswith(READ_PREFIXES):
        return None
    try:
        req = urllib.request.Request(
            f"{BASE}/api/{method}", data=json.dumps({"args": []}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None



# --- сколько аргументов шлёт интерфейс и сколько принимает сервер ---------------
#
# ЗАЧЕМ. Живой дефект 17.08.2026 в панели Рекрутёра: кнопка «Создать» передавала
# методу ПЯТЬ аргументов (добавился язык), метод принимал ЧЕТЫРЕ. Сервер спотыкался,
# а интерфейс показывал «Приложение не ответило» — то есть человек видел «не работает»
# вместо причины. Имена методов при этом совпадали, форма ответа тоже, и гейт
# контракта был зелёным. Одна цифра, которую никто не сверял.

def арность_вызовов(text: str) -> dict:
    """Метод → наибольшее число аргументов, которое интерфейс ему передаёт."""
    out = {}
    for m in re.finditer(r"api\(\s*['\"]([a-z0-9_]+)['\"]\s*(,?)", text):
        имя, есть_запятая = m.group(1), m.group(2)
        if not есть_запятая:
            out[имя] = max(out.get(имя, 0), 0)
            continue
        # Аргументы идут списком: api('метод', [a, b, c]). Считаем запятые ВЕРХНЕГО
        # уровня: вложенные вызовы и объекты внутри аргумента — это один аргумент.
        хвост = text[m.end():]
        нач = хвост.find("[")
        if нач < 0 or нач > 40:
            continue
        глубина, счёт, элементы = 0, 0, 0
        for c in хвост[нач:]:
            if c in "[({":
                глубина += 1
                if глубина == 1:
                    элементы = 1
            elif c in "])}":
                глубина -= 1
                if глубина == 0:
                    break
            elif c == "," and глубина == 1:
                элементы += 1
            счёт += 1
            if счёт > 4000:
                break
        # Пустой список — ноль аргументов, а не один.
        внутри = хвост[нач + 1: нач + 1 + счёт].strip()
        out[имя] = max(out.get(имя, 0), 0 if not внутри else элементы)
    return out


def подписи_сервера() -> dict:
    """Метод → (сколько принимает, есть ли *args/**kwargs)."""
    подписи = {}
    for src in list(ROOT.rglob("api.py")) + list(ROOT.rglob("main.py")) + list(ROOT.rglob("server.py")):
        if any(part in {".venv", "node_modules", "__pycache__", ".git", "dist"} for part in src.parts):
            continue
        текст = src.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^\s{4}def ([a-z0-9_]+)\s*\(([^)]*)\)", текст, re.M):
            имя, аргументы = m.group(1), m.group(2)
            if имя.startswith("_"):
                continue
            части = [ч.strip() for ч in аргументы.split(",") if ч.strip()]
            части = [ч for ч in части if ч not in ("self", "cls")]
            свободно = any(ч.startswith("*") for ч in части)
            подписи[имя] = (len([ч for ч in части if not ч.startswith("*")]), свободно)
    return подписи


def сверить_арность(ui: str, сказать=print) -> list:
    """Красное только на явном перевесе: интерфейс шлёт БОЛЬШЕ, чем метод берёт."""
    беды = []
    шлёт = арность_вызовов(ui)
    берёт = подписи_сервера()
    if not шлёт or not берёт:
        return беды
    сверено = 0
    for имя, сколько in sorted(шлёт.items()):
        если = берёт.get(имя)
        if если is None:
            continue
        принимает, свободно = если
        сверено += 1
        if свободно:
            continue
        if сколько > принимает:
            беды.append(f"{имя}: интерфейс передаёт {сколько} аргументов, "
                        f"метод принимает {принимает}")
    сказать(f"  сверено по числу аргументов: {сверено}")
    for б in беды:
        сказать(f"  ✗ {б}")
    return беды

def проверить_etb_мост(text: str) -> list[str] | None:
    """Канонический iframe-мост H62; None означает другой транспорт."""
    if "etb_run_expert" not in text:
        return None
    беды = []
    требования = (
        ("etb_expert_result", "нет обратной половины etb_expert_result"),
        ("allowedExperts", "нет явного allowlist экспертов"),
        ("setTimeout", "нет конечного ожидания ответа"),
    )
    for признак, сообщение in требования:
        if признак not in text:
            беды.append(сообщение)
    if not re.search(r"event\.source\s*!==\s*window\.parent", text):
        беды.append("ответы не ограничены родительским окном")
    if not re.search(r"type\s*:\s*['\"]etb_run_expert['\"]", text):
        беды.append("исходящее сообщение не имеет точного типа etb_run_expert")
    if not re.search(r"\btarget\s*[,}]", text):
        беды.append("вызов не закреплён singular target")
    return беды

def main(argv) -> int:
    root = Path(argv[0]).expanduser().resolve() if argv else Path.cwd()
    port_arg = argv[1] if len(argv) > 1 else None
    ui_path, port = guess(root, port_arg)
    if ui_path is None:
        print(f"{root.name}: файл интерфейса не найден — пропускаю")
        return 0
    global ROOT, BASE
    ROOT = root
    BASE = f"http://127.0.0.1:{port}" if port else ""
    ui = ui_path.read_text(encoding="utf-8", errors="ignore")
    # Логика часто вынесена в отдельный файл: <script src="/app.js">. Читая только HTML,
    # гейт находил у Баги ноль вызовов и честно писал «проверять нечего» — но проверять
    # было ЧТО, просто не там. Дочитываем локальные скрипты страницы.
    extra = 0
    for m in re.finditer(r"""<script[^>]+src=['"]([^'"]+)['"]""", ui):
        rel = m.group(1).split("?")[0].lstrip("/")
        if rel.startswith(("http://", "https://", "//")):
            continue
        for cand in (ui_path.parent / rel, root / rel):
            if cand.exists() and cand.is_file():
                ui += "\n" + cand.read_text(encoding="utf-8", errors="ignore")
                extra += 1
                break
    if extra:
        print(f"  дочитано подключённых скриптов: {extra}")
    print(f"{root.name} ({ui_path.name}" + (f", порт {port}" if port else ", сервер не найден") + ")")
    etb_беды = проверить_etb_мост(ui)
    if etb_беды is not None:
        print("Договор панели с обёрткой Extella H62\n")
        if etb_беды:
            for беда in etb_беды:
                print(f"  ✗ {беда}")
            print("\nДОГОВОР ETB РАСХОДИТСЯ")
            return 1
        print("  ✓ etb_run_expert → etb_expert_result, allowlist, timeout, parent guard, target")
        return 0

    called = called_methods(ui)
    served = server_methods()
    problems = []

    print("Договор интерфейса и сервера\n")
    print(f"  интерфейс зовёт методов: {len(called)}")

    # Страница может не звать /api вовсе, а говорить с хостом сообщениями (Console).
    # Тогда счёт вызовов равен нулю, и прежний гейт объявлял успех, ничего не проверив.
    # Число аргументов сверяем ВСЕГДА: для этого сервер поднимать не нужно,
    # достаточно исходников. Именно эта проверка ловит дефект 17.08.2026.
    problems += сверить_арность(ui)

    итог_хоста = проверить_хост_контракт(root, ui_path)
    if итог_хоста == 1:
        problems.append("договор с хостом не сходится")
    if not called and итог_хоста == 2:
        print("\n  ✗ проверять нечего: страница не зовёт ни сервер, ни хост.")
        print("    Это НЕ успех. Либо вызовы собираются кодом и статика их не видит,")
        print("    либо указан не тот файл интерфейса. Проверка, которая не может")
        print("    упасть, не защищает ничего.")
        return 1

    if served is None:
        print("  ~ сервер не отвечает — проверил только состав вызовов")
    elif not served:
        print("  ~ поверхность сервера не найдена в исходниках — форму ответов не сверял")
    routes = sorted(m for m in called if m.startswith("/"))
    # Родительский путь — не маршрут: в коде есть /api/connections/sync и /authorize,
    # а самого /api/connections нет и быть не должно. Без этого гейт объявлял дырой
    # путь, который никто не зовёт, — и человек шёл чинить несуществующее.
    routes = [r for r in routes if not any(o != r and o.startswith(r + "/") for o in routes)]
    rpc = {m: v for m, v in called.items() if not m.startswith("/")}
    if routes:
        surface = served_routes()
        # Ложный запрет дороже пропущенного нарушения: если поверхность сервера
        # написана не литералами (собирается кодом), статика не увидит НИЧЕГО — и
        # обвинять каждый маршрут нельзя. Признак нераспознанной поверхности —
        # пусто ИЛИ «мёртвы все до одного» при заметном их числе: продукт, у
        # которого не работает ни один маршрут, не дожил бы до гейта. Точечные
        # пропажи — настоящие дыры (порог «треть» съедал дыру из двух маршрутов —
        # поймано самопроверкой).
        dead = [r for r in routes
                if surface and r not in surface
                and not any(sv == r or sv.startswith(r + "/") or r.startswith(sv + "/")
                            for sv in surface)]
        if not surface or (len(routes) >= 3 and len(dead) == len(routes)):
            print("  ~ поверхность маршрутов сервера не распозналась в исходниках — "
                  "состав маршрутов не сверял")
        else:
            for r in dead:
                problems.append(f"маршрут «{r}» интерфейс зовёт, в исходниках сервера его нет — "
                                f"этот раздел останется пустым")
            if not dead:
                print(f"  ✓ все {len(routes)} маршрутов объявлены сервером")

    if served and rpc:
        missing = sorted(m for m in rpc if m not in served)
        if missing:
            for m in missing:
                problems.append(f"метод «{m}» интерфейс зовёт, сервер его не отдаёт — "
                                f"человек увидит пустой блок вместо данных")
        else:
            print(f"  ✓ все {len(rpc)} вызываемых методов есть на сервере")

    checked = 0
    for method, wants_list in sorted(called.items()):
        if not wants_list:
            continue
        data = response_shape(method)
        if data is None:
            continue
        checked += 1
        if isinstance(data, list):
            continue
        if isinstance(data, dict):
            lists = [k for k, v in data.items() if isinstance(v, list)]
            hint = f" (список лежит в поле «{lists[0]}»)" if lists else ""
            problems.append(f"«{method}»: интерфейс работает с ответом как со списком, "
                            f"а сервер отдаёт объект{hint}")
    if checked:
        print(f"  проверено форм ответа: {checked}")

    if not called:
        print("  ~ вызовов к серверу не найдено — способ обращения не распознан.")
        print("    Это НЕ значит «всё в порядке»: проверять было нечего.")
        print()
        return 0

    print()
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        print("\nДОГОВОР РАСХОДИТСЯ — это падает молча: пустой экран без ошибки.")
        return 1
    print("Интерфейс и сервер договорились об одном и том же.")
    return 0



def _selftest() -> int:
    """Самопроверка договора с хостом.

    Прежняя самопроверка этого гейта ПРОПУСКАЛАСЬ, если не находила файл интерфейса,
    и выходила нулём — то есть не могла упасть. Проверка, которая не может упасть,
    не защищает ничего; это ровно тот дефект, который гейт ищет у других.
    """
    import tempfile
    провалы = []

    СТРАНИЦА = """<script>
      function request(action, payload){
        parent.postMessage(Object.assign({type:'etb_x', reqId:1, action:action}, payload), '*');
      }
      request('registry_load'); request('cabinet_get');
    </script>"""
    АДАПТЕР = """
def обработать(действие, payload):
    if действие == "registry_load": return {}
    if действие == "cabinet_get":   return {}
"""

    def случай(имя, страница, адаптер, ждём):
        with tempfile.TemporaryDirectory() as d:
            к = Path(d)
            (к / "index.html").write_text(страница)
            if адаптер is not None:
                (к / "my_adapter.py").write_text(адаптер)
            код = проверить_хост_контракт(к, к / "index.html", сказать=lambda *_: None)
            ок = код == ждём
            print(("  ✓ " if ок else f"  ✗ ({код} вместо {ждём}) ") + имя)
            if not ок:
                провалы.append(имя)

    print("Самопроверка check_ui_api_contract:")
    случай("полный договор сходится", СТРАНИЦА, АДАПТЕР, 0)
    случай("нехватка действия у адаптера ловится",
           СТРАНИЦА, АДАПТЕР.replace('if действие == "cabinet_get":   return {}', ''), 1)
    случай("отсутствие второй стороны — не успех", СТРАНИЦА, None, 1)
    случай("страница без вызовов к хосту: проверять нечего",
           "<script>console.log(1)</script>", АДАПТЕР, 2)


    # --- сверка арности: живой дефект 17.08.2026 --------------------------------
    def случай_арности(имя, страница, сервер, ждём_беду):
        with tempfile.TemporaryDirectory() as d:
            к = Path(d)
            (к / "api.py").write_text(сервер)
            global ROOT
            прежний = ROOT
            ROOT = к
            try:
                беды = сверить_арность(страница, сказать=lambda *_: None)
            finally:
                ROOT = прежний
            ок = bool(беды) == ждём_беду
            print(("  ✓ " if ок else "  ✗ ") + имя)
            if not ок:
                провалы.append(имя)

    БЕРЁТ_ЧЕТЫРЕ = """
class API:
    def create_job_text(self, job_id, title, level, notes):
        return {}
"""
    БЕРЁТ_СВОБОДНО = """
class API:
    def create_job_text(self, *args):
        return {}
"""
    ШЛЁТ_ПЯТЬ = "const r = await api('create_job_text', [id, title, level, notes, lang]);"
    ШЛЁТ_ТРИ = "const r = await api('create_job_text', [id, title, level]);"

    случай_арности("перевес аргументов ловится (5 против 4)",
                   ШЛЁТ_ПЯТЬ, БЕРЁТ_ЧЕТЫРЕ, True)
    случай_арности("недостача аргументов НЕ красная (3 против 4)",
                   ШЛЁТ_ТРИ, БЕРЁТ_ЧЕТЫРЕ, False)
    случай_арности("метод со *args не сверяется",
                   ШЛЁТ_ПЯТЬ, БЕРЁТ_СВОБОДНО, False)

    etb_good = """const allowedExperts=[]; setTimeout(()=>{},1);
    window.parent.postMessage({type:'etb_run_expert', target}, '*');
    if (event.source !== window.parent) return;
    if (data.type === 'etb_expert_result') return data;"""
    if проверить_etb_мост(etb_good) == []:
        print("  ✓ канонический etb-мост H62 проходит")
    else:
        провалы.append("канонический etb-мост H62 не распознан")
    if проверить_etb_мост(etb_good.replace("event.source !== window.parent", "true")):
        print("  ✓ etb-мост без parent guard падает")
    else:
        провалы.append("etb-мост без parent guard прошёл")

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(main(sys.argv[1:]))

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
REG_DIR = Path.home() / "extella-plugins" / "_registry"


def guess(root: Path, port_arg: str | None):
    """Файл интерфейса и порт: из карточки плагина, иначе по обычным местам."""
    port = port_arg
    ui = None
    for card in sorted(REG_DIR.glob("*.json")) if REG_DIR.exists() else []:
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
    called = called_methods(ui)
    served = server_methods()
    problems = []

    print("Договор интерфейса и сервера\n")
    print(f"  интерфейс зовёт методов: {len(called)}")

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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

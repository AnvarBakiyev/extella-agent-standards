#!/usr/bin/env python3
"""Гейт прав приложения: объявлено ровно то, что код действительно зовёт.

Два тихих отказа, оба стоили дня и оба невидимы глазом:

* **прав не хватает** — страница откроется целой, а каждый вызов вернёт `403`.
  Продукт выглядит работающим и не работает;
* **прав лишку** — покупатель видит список ДО покупки. `api.full` у продукта,
  которому хватает своего агента, — причина не купить, а не мелочь.

Гейт читает код страницы и приложенных Expert, выводит нужный набор и сверяет с объявленным.

    python3 tools/check_app_scopes.py editions/founder
    python3 tools/check_app_scopes.py --selftest
"""

import pathlib
import re
import sys

# Что в коде страницы означает какое право. Составлено по H12/H15 и живым замерам.
ПРИЗНАКИ = [
    (r"app-agent/run",            "expert.run",
     "страница запускает эксперта"),
    (r"app-agent/message",        "agent.run",
     "страница разговаривает с агентом"),
    (r"subprocess\.(run|Popen|call|check_call|check_output)", "device.run",
     "Expert запускает процесс на устройстве покупателя"),
    (r"[\"']?targets[\"']?\s*[:=]", "device.run",
     "страница закрепляет вызов за устройством покупателя"),
    (r"/api/ext/core",            "api.full",
     "страница ходит в ядро через прокси"),
    (r"expert\.(list|get|search)|['\"]op['\"]\s*:\s*['\"]expert\.(list|get|search)",
     "expert.read", "страница читает определения экспертов"),
    (r"['\"]op['\"]\s*:\s*['\"]kv\.(get|list|search)", "kv.read",
     "страница читает key-value"),
    (r"['\"]op['\"]\s*:\s*['\"]kv\.(set|delete)", "kv.write",
     "страница пишет в key-value"),
    (r"['\"]op['\"]\s*:\s*['\"]rules\.(add|update|delete)", "rules.write",
     "страница меняет правила агента"),
    (r"['\"]op['\"]\s*:\s*['\"]concept\.(add|update|delete)", "concept.write",
     "страница меняет память агента"),
]
СИЛЬНЫЕ = {"api.full", "kv.write", "rules.write", "concept.write", "device.run"}


def отказ(беды):
    print("ПРАВА НЕ СХОДЯТСЯ:")
    for b in беды:
        print("  ✗", b)
    return 1


def нужные_права(код: str):
    """Что код действительно зовёт. Комментарии выкидываем: в них бывают примеры."""
    # Комментарий может стоять и в середине строки. Отрицательный просмотр назад
    # спасает адреса: в «https://…» перед слэшами стоит двоеточие.
    без_комментариев = re.sub(r"(?<!:)//[^\n]*", "", код)
    без_комментариев = re.sub(r"/\*.*?\*/", "", без_комментариев, flags=re.S)
    нужно = {}
    for шаблон, право, почему in ПРИЗНАКИ:
        if re.search(шаблон, без_комментариев):
            нужно[право] = почему
    # device.run без запуска эксперта бессмыслен — это добавка к нему.
    if "device.run" in нужно and "expert.run" not in нужно:
        нужно["expert.run"] = "закрепление за устройством работает поверх запуска эксперта"
    return нужно


def объявленные(папка: pathlib.Path):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    паспорт = папка / "edition.yaml"
    if паспорт.exists():
        import check_edition
        d = check_edition.разобрать_yaml(паспорт.read_text())
        узел = d.get("права_приложения")
        if isinstance(узел, dict):
            return set(узел.get("_список", []))
        return set()
    лист = папка / "listing.json"
    if лист.exists():
        import json
        return set(json.loads(лист.read_text()).get("права", []))
    return None


def проверить(папка: pathlib.Path) -> int:
    страницы = list(папка.glob("index.html")) + list(папка.glob("*/index.html"))
    if not страницы:
        print("страницы нет — права приложения не нужны, проверять нечего")
        return 0
    эксперты = [
        п for п in папка.rglob("expert_*.py")
        if not any(часть in {"__pycache__", "migrations", "tests"} for часть in п.parts)
    ]
    код = "\n".join(п.read_text() for п in страницы + эксперты)

    объявлено = объявленные(папка)
    if объявлено is None:
        return отказ(["нет ни edition.yaml, ни listing.json — нечем узнать объявленные права"])

    нужно = нужные_права(код)
    беды = []

    не_хватает = set(нужно) - объявлено
    for право in sorted(не_хватает):
        беды.append(f"не объявлено «{право}»: {нужно[право]}. "
                    f"Без него страница откроется целой, а вызов вернёт 403")

    лишние = объявлено - set(нужно)
    for право in sorted(лишние):
        строгость = "СИЛЬНОЕ право" if право in СИЛЬНЫЕ else "право"
        беды.append(f"объявлено {строгость} «{право}», но код его не зовёт — "
                    f"покупатель видит список до покупки, лишнее отпугивает")

    if беды:
        return отказ(беды)
    print(f"Права сходятся: {sorted(объявлено) or 'нет'} — ровно то, что зовёт код")
    for право, почему in sorted(нужно.items()):
        print(f"  {право}: {почему}")
    return 0


def _selftest() -> int:
    import tempfile, json
    провалы = []

    СТРАНИЦА = """<script>
      fetch('https://os.extella.ai/api/app-agent/run', {body: JSON.stringify({
        app_token: EXT.app_token, expert_name: 'x', params: {}, targets: [У]})});
    </script>"""

    def случай(имя, страница, права, ждём_провал, эксперт=""):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "index.html").write_text(страница)
            (p / "listing.json").write_text(json.dumps({"права": права}, ensure_ascii=False))
            if эксперт:
                (p / "expert_install.py").write_text(эксперт)
            код = проверить(p)
            ок = (код != 0) if ждём_провал else (код == 0)
            print(("  ✓ " if ок else "  ✗ ") + имя)
            if not ок:
                провалы.append(имя)

    print("Самопроверка check_app_scopes:")
    случай("верный набор проходит", СТРАНИЦА, ["expert.run", "device.run"], False)
    случай("нехватка device.run ловится", СТРАНИЦА, ["expert.run"], True)
    случай("нехватка expert.run ловится", СТРАНИЦА, ["device.run"], True)
    случай("лишнее api.full ловится", СТРАНИЦА, ["expert.run", "device.run", "api.full"], True)
    случай("пустые права при живом коде ловятся", СТРАНИЦА, [], True)
    случай("право из комментария не считается нужным",
           "<script>// пример: /api/ext/core тут только в комментарии\n"
           "fetch('/api/app-agent/run')</script>", ["expert.run"], False)
    случай("локальный процесс в Expert требует device.run",
           "<script>fetch('/api/app-agent/run')</script>",
           ["expert.run", "device.run"], False,
           "def expert_install():\n    return subprocess.run(['true'])\n")

    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(проверить(pathlib.Path(sys.argv[1])))

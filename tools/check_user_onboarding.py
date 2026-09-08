#!/usr/bin/env python3
"""Встречающий тур на странице продукта: разметка по USER_ONBOARDING_CANON.md.

ЗАЧЕМ. Приёмка требует «онбординг встречает», но до 08.09.2026 требование жило
одной строкой без проверки — и продукт мог пройти к Publish вовсе без тура.
Гейт проверяет КЛАСС (атрибуты data-onboarding), а не имена конкретного
продукта, поэтому один и тот же гейт годится любому страничному приложению.

Правила:
1. Есть контейнер подсказки: data-onboarding="tour".
2. Есть кнопка следующего шага (data-onboarding="next") и «Пропустить»
   (data-onboarding="skip").
3. Есть элемент повторного запуска (data-onboarding="restart") — подсказки
   нужны и второму человеку за тем же экраном.
4. Прохождение сохраняется: в странице есть ключ с суффиксом tour_done.
5. Каждое обращение к localStorage обёрнуто в try: хранилище бывает недоступно
   (приватное окно, предпросмотр), и страница обязана это переживать.

Использование:
    python3 tools/check_user_onboarding.py <страница.html> [ещё страницы]
    python3 tools/check_user_onboarding.py --selftest

Коды выхода: 0 — зелёный, 1 — есть нарушения, 2 — неверный вызов.
"""
import re
import sys
from pathlib import Path


def check(html: str):
    errors = []
    for attr, human in (("tour", "контейнер подсказки"),
                        ("next", "кнопка следующего шага"),
                        ("skip", "кнопка «Пропустить»"),
                        ("restart", "элемент повторного запуска")):
        if not re.search(r'data-onboarding="%s"' % attr, html):
            errors.append("нет разметки data-onboarding=\"%s\" (%s)" % (attr, human))
    if "tour_done" not in html:
        errors.append("нет сохранения прохождения: ключ с суффиксом tour_done не найден")
    for m in re.finditer(r"localStorage", html):
        window = html[max(0, m.start() - 160):m.start()]
        if "try" not in window:
            line = html.count("\n", 0, m.start()) + 1
            errors.append("localStorage без try (строка %d): недоступное хранилище "
                          "уронит страницу" % line)
            break
    return errors


GOOD = """<!DOCTYPE html><html><body>
<button data-onboarding="restart">Как пользоваться</button>
<div data-onboarding="tour" hidden>
  <button data-onboarding="next">Далее</button>
  <button data-onboarding="skip">Пропустить</button>
</div>
<script>
function done(){ try { localStorage.setItem('demo_tour_done','1'); } catch(e){} }
function seen(){ try { return localStorage.getItem('demo_tour_done'); } catch(e){ return '1'; } }
</script></body></html>"""


def selftest():
    base = check(GOOD)
    if base:
        print("SELFTEST: образец соответствия красный, чинить гейт:")
        for e in base:
            print(" -", e)
        return False
    breaks = {
        "без кнопки «Пропустить»": GOOD.replace('data-onboarding="skip"', 'data-x="skip"'),
        "без повторного запуска": GOOD.replace('data-onboarding="restart"', 'data-x="restart"'),
        "без контейнера тура": GOOD.replace('data-onboarding="tour"', 'data-x="tour"'),
        "без сохранения прохождения": GOOD.replace("tour_done", "tour_seen"),
        "localStorage без try": GOOD.replace(
            "function done(){ try { localStorage",
            "function done(){ if(1) { localStorage"),
    }
    ok = True
    for name, html in breaks.items():
        errs = check(html)
        status = "ловит" if errs else "ПРОПУСТИЛ"
        if not errs:
            ok = False
        print("  [%s] %s" % (status, name))
    return ok


def main(argv):
    if "--selftest" in argv:
        good = selftest()
        print("SELFTEST:", "OK — гейт умеет падать" if good else "ПРОВАЛ")
        return 0 if good else 1
    pages = [a for a in argv if not a.startswith("-")]
    if not pages:
        print(__doc__)
        return 2
    failed = False
    for p in pages:
        path = Path(p)
        if not path.is_file():
            print("✗ %s — файл не найден" % p)
            failed = True
            continue
        errs = check(path.read_text(encoding="utf-8", errors="replace"))
        if errs:
            failed = True
            print("✗ %s (%d):" % (p, len(errs)))
            for e in errs:
                print("   -", e)
        else:
            print("✓ %s — встречающий тур размечен по канону" % p)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

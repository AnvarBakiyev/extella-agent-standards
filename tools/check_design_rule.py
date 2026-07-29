#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт правила по дизайну: копия в гиде не должна разъехаться с источником.

Правило пишет Элла, а работает оно в промпте генерации — значит абзац обязан лежать прямо
в `AGENT_BUILD_GUIDE.md`, иначе Codex его не увидит. Копия и источник — два места, а два места
неизбежно разъезжаются: сегодня это наш самый частый класс аварий (описания экспертов разошлись
с аккаунтом, документ архитектуры за час разошёлся с шаблоном паспорта).

Поэтому проверяем два свойства:

1. **Абзац на месте и полон.** Все токены палитры и все запреты присутствуют. Это работает
   везде, даже если репозитория витрины рядом нет — а его нет у Гульжан и у любого, кому
   правило отдали одним файлом.
2. **Копия совпадает с источником.** Если `extella-toolbar-src` лежит рядом, сверяем слово
   в слово с `HANDOFF/DESIGN_RULE_FOR_APPS.md`. Нет репозитория — честно говорим «сверить
   не с чем», а не делаем вид, что проверили.

Как пользоваться:
  python3 check_design_rule.py --selftest
  python3 check_design_rule.py                  # проверить гид рядом с собой

Коды выхода: 0 — совпадает, 1 — расхождение.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "AGENT_BUILD_GUIDE.md")
# Витрина лежит соседним репозиторием — так у всех, кто ведёт обе части.
SOURCE = os.path.join(os.path.dirname(ROOT), "extella-toolbar-src",
                      "HANDOFF", "DESIGN_RULE_FOR_APPS.md")

# Обязательное содержимое абзаца. Не косметика: без токена цвет уедет мимо палитры,
# без запрета вернутся эмодзи и капс, без контракта темы окно заведёт свой тумблер.
REQUIRED = [
    "Source Serif 4", "Source Sans 3", "JetBrains Mono",
    "#FAF9F5", "#FFFFFF", "#F5F3EC", "#0A0A0A", "#C57E33", "#2F6B66", "#D7E0DC",
    "#141414", "#181818", "#F5F3EE", "#D4944A",
    "без градиентов", "без эмодзи", "без капса",
    "etb_theme", "etb_init", "data-lm",
]


def _quote(text):
    """Абзац-цитата: строки, начинающиеся с '>'. В обоих файлах он оформлен одинаково."""
    lines = [l.strip()[1:].strip() for l in text.splitlines() if l.strip().startswith(">")]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def check(guide_text, source_text=None):
    """Возвращает (список проблем, сверялись ли с источником)."""
    problems = []
    quote = _quote(guide_text)
    if not quote:
        return (["в гиде нет абзаца-цитаты с правилом по дизайну"], False)
    for token in REQUIRED:
        if token not in quote:
            problems.append("в абзаце нет обязательного «%s»" % token)
    if source_text is None:
        return (problems, False)
    src = _quote(source_text)
    if not src:
        problems.append("в источнике не нашёлся абзац-цитата — сверять не с чем")
    elif src != quote:
        problems.append("копия в гиде разошлась с источником "
                        "(HANDOFF/DESIGN_RULE_FOR_APPS.md) — перенеси текст заново")
    return (problems, bool(src))


def selftest():
    print("Самопроверка правила по дизайну:")
    ok = True
    good = "> Используй только эти токены: " + ", ".join(REQUIRED)
    cases = [
        ("полный абзац проходит", good, None, 0),
        ("нет абзаца вовсе — поймано", "просто текст без цитаты", None, 1),
        ("пропал токен палитры — поймано", good.replace("#C57E33", ""), None, 1),
        ("пропал запрет — поймано", good.replace("без эмодзи", ""), None, 1),
        ("совпадение с источником проходит", good, good, 0),
        ("расхождение с источником — поймано", good, good + " и ещё кое-что", 1),
    ]
    for label, guide, source, expect_problems in cases:
        problems, _ = check(guide, source)
        got = (len(problems) > 0) == (expect_problems > 0)
        print(("PASS: " if got else "FAIL: ") + label)
        ok = ok and got

    # Отсутствие витрины рядом не должно выглядеть как успешная сверка.
    _, compared = check(good, None)
    if not compared:
        print("PASS: без репозитория витрины честно говорим, что не сверяли")
    else:
        ok = False
        print("FAIL: сверка без источника выдана за успешную")

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if not os.path.exists(GUIDE):
        print("ОШИБКА: не найден %s" % GUIDE)
        return 1
    with open(GUIDE, encoding="utf-8") as fh:
        guide = fh.read()
    source = None
    if os.path.exists(SOURCE):
        with open(SOURCE, encoding="utf-8") as fh:
            source = fh.read()
    problems, compared = check(guide, source)
    for p in problems:
        print("ОШИБКА: " + p)
    if problems:
        return 1
    print("правило по дизайну: абзац полон, " +
          ("совпадает с источником" if compared else "источника рядом нет — не сверял"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

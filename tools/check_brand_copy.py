#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверялка бренда Extella в интерфейсе и текстах агента.

Проверяет то, что можно проверить машиной: запрещённые слова, имя бренда,
цвета из палитры, запрещённые пары контраста, приветствия в интерфейсе.

Как пользоваться:
  python3 check_brand_copy.py файл1.js файл2.html ...
  python3 check_brand_copy.py --selftest

Коды выхода: 0 — бренд соблюдён, 1 — есть нарушения, 2 — файлы не прочитаны.

Источник правил: BRAND_FOR_AGENTS.md (выжимка брендбука для разработчиков).
Что сознательно НЕ проверяется: скругления, тени, градиенты и «острые углы» —
визуальные запреты брендбука §8.4-8.5 приостановлены до новой визуальной
спецификации, и проверять приостановленное правило нельзя.
"""
import os
import re
import sys

# --- палитра брендбука §8.2 (единственные допустимые цвета) ---
GOLD = {"C57E33", "D4984F", "A5632A", "D4944A", "E0A85E"}
LOGO_ONLY = {"C49C70"}
PETROL = {"2F6B66", "3D8078", "24544F", "B7CEC9", "5FA8A0", "6BB3AA"}
INK = {"0A0A0A", "1A1A1A", "2A2A2A", "F0F0F0", "D8D8D8", "B0B0B0"}
SURFACE = {"8C8C8C", "AAAAAA", "FAFAF8", "F5F3EE", "EBE8E1", "D4B896",
           "0E0E0E", "181818", "222222", "000000"}
PALETTE = GOLD | LOGO_ONLY | PETROL | INK | SURFACE
DARK_BG = {"0A0A0A", "0E0E0E", "181818", "222222", "000000"}
SILVER = "8C8C8C"

# --- запрещённая лексика брендбука §13.3 (с учётом обновления июля 2026:
#     «агент», «агентная платформа», «мультиагентные команды» разрешены) ---
FORBIDDEN = [
    (r"\bпомощник\w*\b", "«помощник» — не наша категория; пиши: система, платформа, Эксперт, агент"),
    (r"\bассистент\w*\b", "«ассистент» — не наша категория; пиши: система, платформа, агент"),
    (r"\bчат-?бот\w*\b", "«чат-бот» — запрещено; мы исполняем, а не переписываемся"),
    (r"\bбот(?:ы|а|ов|у|ом|е|ам|ами|ах)?\b", "«бот» — запрещено; пиши: Эксперт, агент"),
    (r"\bнейросет\w*\b", "«нейросеть» — технически неточно; пиши: AI, LLM, оркестрация"),
    (r"\bAGI\b", "«AGI» — хайп, запрещено"),
    (r"\bсознани\w*\b", "«сознание» — запрещено, не обещаем субъектность"),
    (r"\bпомо(?:га(?:ет|ем|ю|ть|я)|гу|жет|жем|чь)\b",
     "«помогает / помогу / поможет» — слабая позиция; пиши: выполняет, исполняет, сделает"),
    (r"\bhelps?\s+(?:you|with)\b", "«helps you/with» — слабая позиция; пиши: executes, completes, runs"),
    (r"\bsmart\s+assistant\b", "«smart assistant» — commodity; пиши: execution platform, AI system"),
]

BRAND_NAME = [
    (r"\bExtella\s+AI\b", "«Extella AI» в тексте продукта запрещено — только «Extella» "
                          "(вариант с AI допустим лишь в юр. документах и в handle @extella_ai)"),
]

# «the Extella» — предупреждение, а не ошибка: «the Extella team» и «the Extella platform»
# по-английски законны (Extella там определение, а не имя с артиклем).
BRAND_NAME_SOFT = [
    (r"\bthe\s+Extella\b(?!\s+[a-z])", "артикль с именем бренда не используется — просто «Extella»"),
]

# Сторонние продукты называются их собственными словами: Telegram-бот и @BotFather —
# это не мы, и переименовывать чужую сущность нельзя.
THIRD_PARTY_BOT = re.compile(r"telegram|botfather|@bot", re.I)

GREETINGS = [
    (r"Чем\s+(?:могу|я\s+могу)\s+помочь", "приветствие-заглушка в интерфейсе запрещено — "
                                          "интерфейс говорит действиями, а не «Чем могу помочь?»"),
    (r"How\s+can\s+I\s+help\s+you", "приветствие-заглушка в интерфейсе запрещено"),
]

HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
FG_RE = re.compile(r"(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{3,8})", re.I)
BG_RE = re.compile(r"background(?:-color)?\s*:[^;{}]*?(#[0-9a-fA-F]{3,8})", re.I)
SHORT_STR_RE = re.compile(r"""(['"])([^'"\n]{0,60}![^'"\n]{0,60})\1""")
# `!=`, `!==` и `!important` — это код и CSS, а не восклицание в тексте интерфейса
NOT_EXCLAMATION = ("!=", "!important")


def norm_hex(raw):
    """Приводит #abc / #aabbccdd к шести заглавным символам; None — если не цвет."""
    h = raw.lstrip("#").upper()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) in (6, 8):
        return h[:6]
    return None


def check_text(name, text, strict=False):
    """Проверяет один текст, возвращает (ошибки, предупреждения).

    strict=True — цвета вне палитры считаются ошибкой. По умолчанию это
    предупреждение: в палитре брендбука нет цветов состояний (успех, ошибка,
    предупреждение), поэтому продукты вынужденно вводят свои. Пока Анвар не
    утвердил цвета состояний, делать из этого гейт нельзя — гейт, который
    невозможно пройти честно, сам является дефектом (BRAND_FOR_AGENTS.md §7).
    """
    errors, warns = [], []

    def loc(match):
        return "%s:%d" % (name, text.count("\n", 0, match.start()) + 1)

    lines = text.split("\n")

    def line_of(match):
        return lines[text.count("\n", 0, match.start())]

    def scan(rules, bucket):
        """Первое неисключённое нарушение каждого правила — в свой список."""
        for pattern, reason in rules:
            flags = re.I if re.search(r"[a-z]", pattern) else 0
            for m in re.finditer(pattern, text, flags):
                is_bot_rule = "«бот»" in reason
                if is_bot_rule and THIRD_PARTY_BOT.search(line_of(m)):
                    continue  # Telegram-бот / @BotFather — чужая сущность, не наше имя
                bucket.append("%s: %s (найдено: «%s»)" % (loc(m), reason, m.group(0).strip()))
                break

    # Правило 1: запрещённая лексика и имя бренда
    scan(FORBIDDEN + BRAND_NAME + GREETINGS, errors)
    scan(BRAND_NAME_SOFT, warns)

    # Правило 2: цвета только из палитры
    unknown = {}
    for m in HEX_RE.finditer(text):
        h = norm_hex(m.group(0))
        if h and h not in PALETTE and h not in unknown:
            unknown[h] = loc(m)
    for h, where in sorted(unknown.items()):
        message = ("%s: цвет #%s не из палитры Extella — заменить на цвет из BRAND_FOR_AGENTS.md §2"
                   % (where, h))
        (errors if strict else warns).append(message)

    # Правило 3 и 4: запрещённые пары контраста внутри одного блока стилей
    for block in re.split(r"[{}]", text):
        fg = {norm_hex(x) for x in FG_RE.findall(block)}
        bg = {norm_hex(x) for x in BG_RE.findall(block)}
        if (fg & GOLD and bg & PETROL) or (fg & PETROL and bg & GOLD):
            errors.append("%s: Gold и Petrol друг на друге — контраст 1.9:1, запрещено брендбуком "
                          "(разделять нейтральным фоном)" % name)
        if SILVER in fg and bg & DARK_BG:
            errors.append("%s: Silver #8C8C8C как текст на тёмном фоне — не проходит WCAG AA; "
                          "для читаемого текста бери Paper #FAFAF8" % name)

    # Правило 5: восклицательные знаки в коротких строках интерфейса
    for m in SHORT_STR_RE.finditer(text):
        value = m.group(2)
        if any(token in value for token in NOT_EXCLAMATION):
            continue
        warns.append("%s: восклицательный знак в строке интерфейса («%s») — системные сообщения "
                     "пишутся без него" % (loc(m), value[:40]))

    # Правило 6: логотипный цвет не используется в интерфейсе
    for m in re.finditer(r"#C49C70\b", text, re.I):
        warns.append("%s: #C49C70 — цвет знака логотипа, в интерфейсе его быть не должно" % loc(m))

    return errors, warns


GOOD_TEXT = """
/* Extella · панель запуска */
.badge { color: #C57E33; background: #FAFAF8; }
.status { color: #FAFAF8; background: #0E0E0E; }
.meta   { color: #8C8C8C; background: #FAFAF8; }
const RU = "Эксперт выполнен за 1.2 с";
const EN = "Expert executed in 1.2s";
const NOTE = "Extella исполняет задачу и оставляет квитанцию";
"""

BAD_TEXT = """
.a { color: #C57E33; background: #2F6B66; }
.b { color: #8C8C8C; background: #0A0A0A; }
.c { color: #FF00AA; }
.d { color: #C49C70; }
const T1 = "Привет! Я ваш помощник по задачам";
const T2 = "Умный ассистент разберётся";
const T3 = "Наш чат-бот ответит";
const T4 = "Этот бот запустит эксперта";
const T5 = "Под капотом нейросеть";
const T6 = "Шаг к AGI и сознанию";
const T7 = "Extella помогает с отчётами";
const T8 = "Extella helps you with reports";
const T9 = "A smart assistant for your team";
const T10 = "Extella AI — платформа";
const T11 = "Try the Extella.";
const T12 = "Чем могу помочь?";
const T13 = "How can I help you today";
"""

RULE_CHECKS = [
    ("«помощник»", "«помощник»"),
    ("«ассистент»", "«ассистент»"),
    ("«чат-бот»", "«чат-бот»"),
    ("«бот»", "«бот» —"),
    ("«нейросеть»", "«нейросеть»"),
    ("«AGI»", "«AGI»"),
    ("«сознание»", "«сознание»"),
    ("«помогает/помогу»", "«помогает / помогу"),
    ("«helps you/with»", "helps you/with"),
    ("«smart assistant»", "smart assistant"),
    ("имя «Extella AI»", "«Extella AI» в тексте продукта"),
    ("приветствие RU", "«Чем могу помочь?»"),
    ("приветствие EN", "How can I help"),
    ("цвет вне палитры", "не из палитры Extella"),
    ("Gold на Petrol", "Gold и Petrol друг на друге"),
    ("Silver на тёмном", "Silver #8C8C8C как текст на тёмном"),
]


def selftest():
    print("Самопроверка проверялки бренда (примеры встроены, файлы не нужны):")
    ok = True
    errs, warns = check_text("good.js", GOOD_TEXT)
    if errs:
        ok = False
        print("FAIL: правильный текст — лишние ошибки:")
        for e in errs:
            print("      - " + e)
    else:
        print("PASS: правильный текст проходит без ошибок")
    if warns:
        ok = False
        print("FAIL: правильный текст — лишние предупреждения: %s" % warns)
    else:
        print("PASS: правильный текст без предупреждений")

    bad_errs, bad_warns = check_text("bad.js", BAD_TEXT, strict=True)
    for label, needle in RULE_CHECKS:
        if any(needle in e for e in bad_errs):
            print("PASS: %s — нарушение поймано" % label)
        else:
            ok = False
            print("FAIL: %s — нарушение НЕ поймано" % label)
    if not any("восклицательный знак" in w for w in bad_warns):
        ok = False
        print("FAIL: восклицательный знак в строке интерфейса — не поймано")
    else:
        print("PASS: восклицательный знак — предупреждение выдано")
    if not any("цвет знака логотипа" in w for w in bad_warns):
        ok = False
        print("FAIL: логотипный цвет в интерфейсе — не поймано")
    else:
        print("PASS: логотипный цвет в интерфейсе — предупреждение выдано")

    soft_errs, soft_warns = check_text("bad.js", BAD_TEXT)
    if any("не из палитры" in e for e in soft_errs):
        ok = False
        print("FAIL: без --strict цвет вне палитры не должен быть ошибкой (палитра неполная)")
    elif not any("не из палитры" in w for w in soft_warns):
        ok = False
        print("FAIL: без --strict цвет вне палитры должен быть предупреждением")
    else:
        print("PASS: без --strict цвет вне палитры — предупреждение, с --strict — ошибка")
    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if ok else "есть провалы"))
    return 0 if ok else 1


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    strict = "--strict" in argv
    paths = [a for a in argv if a != "--strict"]
    if not paths or any(a.startswith("-") for a in paths):
        print("Как пользоваться:")
        print("  python3 check_brand_copy.py файл1.js файл2.html ...")
        print("  python3 check_brand_copy.py --strict файл.js   (цвета вне палитры = ошибка)")
        print("  python3 check_brand_copy.py --selftest")
        return 2
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print("ОШИБКА: файлы не найдены: %s" % ", ".join(missing))
        return 2
    all_errors, all_warns = [], []
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            errs, warns = check_text(os.path.basename(path), fh.read(), strict=strict)
        all_errors += errs
        all_warns += warns
    for e in all_errors:
        print("ОШИБКА: " + e)
    for w in all_warns:
        print("ВНИМАНИЕ: " + w)
    if all_errors:
        print("ИТОГ: БРЕНД НАРУШЕН — исправь ошибки выше (правила: BRAND_FOR_AGENTS.md)")
        return 1
    print("ИТОГ: БРЕНД СОБЛЮДЁН (проверено файлов: %d%s)"
          % (len(paths), ", строгий режим" if strict else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

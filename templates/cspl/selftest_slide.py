# -*- coding: utf-8 -*-
"""Самопроверка языка slide: грамматика, политика класса, смена оформления."""
from __future__ import annotations
import copy, pathlib, sys
from handler_slide import run_expert, DEFAULT_POLICY

ошибки: list[str] = []
def проба(имя, о, ждём_ok, ждём_код=None, ещё=None):
    ok, код = о.get("ok"), (о.get("error") or {}).get("code")
    хорошо = (ok == ждём_ok) and (ждём_код is None or код == ждём_код)
    if хорошо and ещё: хорошо = ещё(о)
    if not хорошо: ошибки.append(f"{имя}: ok={ok} код={код}")
    print(f"  {'✓' if хорошо else '✗'} {имя:46} ok={str(ok):5} {код or ''}")
    return о

ИСХОДНИК = """# CSPL: язык вместо доступа

## Проблема не в возможностях
- Клиент не боится, что агент не сможет
- Клиент боится, что агент сможет лишнего
> Доверие, а не функциональность

## Что делает CSPL
- Модель присылает имя операции, а не код
- Эффект известен до выполнения
- Права лежат у клиента и в промпт не входят

## Цена расширения
!число 81 | процента кода не зависит от области
| домен | строк |
| файлы | 128 |
| почта | 130 |

## Язык — это граница прав
- В языке sql нет слова UPDATE
- Запрещать нечего: сказать это невозможно
"""

print("── язык работает ──")
о = проба("презентация собирается", run_expert(ИСХОДНИК, {}), True,
          ещё=lambda о: о["result"]["slides"] == 4)
print("     слайдов:", о["result"]["slides"], "| байт:", о["result"]["bytes"])

print("── грамматика: опасное невыразимо ──")
о = проба("разметка внутри текста экранируется",
          run_expert("# Т\n## С\n- <script>alert(1)</script>", {}), True,
          ещё=lambda о: "<script>" not in о["result"]["html"])
проба("внешняя ссылка запрещена политикой",
      run_expert("# Т\n## С\n- http://example.com/картинка.png", {}), False, "SCOPE_DENIED")
проба("содержимое до первого слайда",
      run_expert("- пункт без слайда", {}), False, "SCHEMA_REJECTED")
проба("пустой исходник", run_expert("", {}), False, "SCHEMA_REJECTED")

print("── политика класса ──")
тесная = copy.deepcopy(DEFAULT_POLICY); тесная["scope"]["maxSlides"] = 2
проба("слайдов больше разрешённого", run_expert(ИСХОДНИК, {}, тесная), False, "SCOPE_DENIED")
без = copy.deepcopy(DEFAULT_POLICY); без["capabilities"]["slide.render"] = False
проба("право отозвано", run_expert(ИСХОДНИК, {}, без), False, "POLICY_DENIED")

print("── смена обработчика меняет ВЕСЬ класс ──")
светлая = run_expert(ИСХОДНИК, {})
тёмный = copy.deepcopy(DEFAULT_POLICY); тёмный["theme"] = "dark"; тёмный["footer"] = "Extella · CSPL"
тёмная = run_expert(ИСХОДНИК, {}, тёмный)
поменялось = ("#141310" in тёмная["result"]["html"]) and ("#141310" not in светлая["result"]["html"])
подвал = "Extella · CSPL" in тёмная["result"]["html"]
отпечаток_другой = светлая["planHash"] != тёмная["planHash"]
for имя, ок in (("оформление сменилось", поменялось), ("подвал добавлен всем слайдам", подвал),
                ("отпечаток отражает правку обработчика", отпечаток_другой)):
    print(f"  {'✓' if ок else '✗'} {имя}")
    if not ок: ошибки.append(имя)

pathlib.Path("презентация.html").write_text(тёмная["result"]["html"], encoding="utf-8")
print("\n     сохранено: презентация.html")
print("САМОПРОВЕРКА SLIDE:", "провалена — " + "; ".join(ошибки) if ошибки else "пройдена")
sys.exit(1 if ошибки else 0)

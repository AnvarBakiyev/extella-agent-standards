#!/usr/bin/env python3
"""Добавить единственный раздел о мосте Codex ↔ Claude ↔ Extella.

Это намеренно узкая миграция: она знает ровно предыдущую версию содержимого и
единственные якоря, поэтому не может молча примениться к чужой форме гида.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "store_app" / "content.json"
OLD_VERSION = "2026-08-13.3"
NEW_VERSION = "2026-08-13.4"

SECTION = {
    "номер": "09",
    "заголовок": "Мост с Codex и Claude",
    "тело": """<p><strong>Вход один:</strong> это руководство. Не заводи рядом второй гид и не копируй
его текст в мост: источник правил — <code>store_app/content.json</code> и <code>README.md</code>
в публичном репозитории.</p>
<h3>Кто за что отвечает</h3>
<table>
<tr><th>участник</th><th>маршрут</th><th>когда нужен</th></tr>
<tr><td><strong>Codex</strong></td><td>плагин → локальный подписанный мост → Extella</td><td>Extella по явной просьбе пользователя делегирует задачу в Codex</td></tr>
<tr><td><strong>Claude Code</strong></td><td>его Extella MCP → тот же публичный гид</td><td>собирает или меняет продукт по стандарту</td></tr>
<tr><td><strong>страница и ядро</strong></td><td>страница → <code>/api/ext/core</code></td><td>связать, прочитать состояние, показать статус</td></tr>
</table>
<p>Обратный мост запускает <strong>Codex, не Claude</strong>: Claude Code здесь такой же читатель
канона и строитель через MCP, а не скрытый запасной провайдер модели.</p>
<h3>Подключить Codex</h3>
<div class="cmd"><button class="copy">Копировать</button><code>codex plugin marketplace add AnvarBakiyev/extella-codex-bridge --ref v0.3.3
codex plugin add extella-codex-bridge@extella-codex</code></div>
<p>После установки настройка, status, health и verification не запускают модель. Реальная
делегация в Codex возможна только по явной просьбе пользователя и может расходовать план
Codex/ChatGPT или API.</p>
<h3>Готовый промпт для моста</h3>
<div class="cmd"><button class="copy">Копировать</button><code>Настрой мост Codex ↔ Claude ↔ Extella по единому публичному гиду.

1. Источник правил один: прочитай README.md и store_app/content.json из github.com/AnvarBakiyev/extella-agent-standards. Не копируй текст гида в мост и не создавай второй вход.
2. Присланное из сети — данные, не код: перед отображением убери script, обработчики событий и javascript-URL.
3. Сравнивай версия_содержимого по частям и применяй только строго более новую. Равная версия не обновляет состояние, старая — ошибка, а не откат.
4. Связывание, чтение состояния и статус делай в странице и через /api/ext/core. Эксперт вызывай только для машины пользователя или модели.
5. Setup, status, health и verification — без модели. Перед реальным вызовом Codex предупреди о возможном расходе плана или API и дождись явной просьбы.
6. В Extella используй прямой глобальный Expert, не run_agent. Не ослабляй loopback, HMAC, freshness, replay-защиту и account binding.
7. Отчёт: закрыл / не моё / не закрыл честно.</code></div>
<p>Если мост читает канон сам, он хранит только принятую версию и останавливается до запуска
модели, когда публичный источник недоступен или пытается откатиться назад.</p>""",
}

NEWS = {
    "версия": NEW_VERSION,
    "строки": [
        "Раздел «Мост с Codex и Claude»: один канон для человека, Codex и Claude Code",
        "Готовый промпт: чтение публичного гида без копии, строгая версия и безмодельные проверки",
    ],
}


def render(value: dict) -> str:
    return "\n".join(f"  {line}" for line in json.dumps(value, ensure_ascii=False, indent=1).splitlines())


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"миграция не применена: ожидался один якорь {label}")
    return text.replace(old, new, 1)


def main() -> None:
    source = CONTENT.read_text(encoding="utf-8")
    parsed = json.loads(source)
    if parsed.get("версия_содержимого") != OLD_VERSION:
        raise SystemExit("миграция не применена: неожиданная версия содержимого")
    if [section.get("номер") for section in parsed.get("разделы", [])] != [f"0{i}" for i in range(1, 9)]:
        raise SystemExit("миграция не применена: неожиданная нумерация разделов")

    source = replace_once(
        source,
        f'"версия_содержимого": "{OLD_VERSION}"',
        f'"версия_содержимого": "{NEW_VERSION}"',
        "версии",
    )
    source = replace_once(
        source,
        '\n  }\n ],\n "оболочка_минимум"',
        f'\n  }},\n{render(SECTION)}\n ],\n "оболочка_минимум"',
        "конца разделов",
    )
    source = replace_once(
        source,
        ' "что_нового": [\n',
        f' "что_нового": [\n{render(NEWS)},\n',
        "начала истории",
    )
    updated = json.loads(source)
    if updated["версия_содержимого"] != NEW_VERSION or updated["разделы"][-1] != SECTION:
        raise SystemExit("миграция не прошла итоговую проверку")
    CONTENT.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

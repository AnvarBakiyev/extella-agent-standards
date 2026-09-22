#!/usr/bin/env python3
"""Быстрые проверки, которые предотвращают типовые ошибки Extella."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = {p.name: p.read_text(encoding='utf-8') for p in (ROOT / 'app').glob('*') if p.is_file()}
required = {'index.html', 'styles.css', 'app.js', 'extella-bridge.js'}
errors = []
if missing := required - files.keys(): errors.append(f'Нет файлов: {sorted(missing)}')
all_text = '\n'.join(files.values())
for forbidden in ('prompt(', 'alert(', 'confirm(', 'fetch("http://127.', "fetch('http://127.", 'fetch("http://localhost', "fetch('http://localhost"):
    if forbidden in all_text: errors.append(f'Запрещённый путь: {forbidden}')
# H106: в окне ОС нет ни моста etb_*, ни доступа к parent.extellaDesktop (песочница).
# Работает только ключ окна {{app_token}} и прямой вызов /api/app-agent/run.
# Ищем ОБРАЩЕНИЕ, а не упоминание: комментарии, объясняющие запрет, — не нарушение.
code = re.sub(r'/\*.*?\*/|<!--.*?-->|^\s*//.*$', '', all_text, flags=re.S | re.M)
for dead in ('etb_run_expert', 'extellaDesktop'):
    if dead in code: errors.append(f'H106: {dead} в окне ОС не работает — звать экспертов через app-agent/run')
if '{{app_token}}' not in files.get('index.html', ''): errors.append('H106: в index.html нет {{app_token}} — ОС не выдаст странице ключ')
bridge = files.get('extella-bridge.js', '')
for need in ('/api/app-agent/run', 'targets'):
    if need not in bridge: errors.append(f'H106: мост без {need}')
deploy = (ROOT / 'tools' / 'deploy_prerelease.py').read_text(encoding='utf-8')
for scope in ('expert.run', 'device.run'):
    if scope not in deploy: errors.append(f'H106: выкладка не просит право {scope}')
# Эксперт, которого зовёт страница, обязан лежать в experts/ — иначе на аккаунте покупателя
# первый же вызов ответит «Expert not found» (правило «код зовёт — эксперт в поставке»).
for name in re.findall(r"(?:routeExpert|allowedExperts)\s*:\s*\[?\s*'([a-z0-9_]+)'", files.get('app.js', '')):
    if not (ROOT / 'experts' / f'{name}.py').is_file(): errors.append(f'Страница зовёт эксперта {name}, а experts/{name}.py нет')
if errors:
    print('НЕ ГОТОВО\n' + '\n'.join(f'- {item}' for item in errors)); raise SystemExit(1)
print('ГОТОВО: структура, мост, права и запреты проверены')

#!/usr/bin/env python3
"""Быстрые проверки, которые предотвращают типовые ошибки Extella."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = {p.name: p.read_text(encoding='utf-8') for p in (ROOT / 'app').glob('*') if p.is_file()}
required = {'index.html', 'styles.css', 'app.js', 'extella-bridge.js'}
errors = []
if missing := required - files.keys(): errors.append(f'Нет файлов: {sorted(missing)}')
all_text = '\n'.join(files.values())
for forbidden in ('prompt(', 'alert(', 'confirm(', 'fetch("http://127.', "fetch('http://127.", 'fetch("http://localhost', "fetch('http://localhost"):
    if forbidden in all_text: errors.append(f'Запрещённый путь: {forbidden}')
# H106: toolbar postMessage протокол удалён из Extella OS. Страница получает
# короткоживущий app_token и вызывает scoped endpoint напрямую.
if '{{app_token}}' not in files.get('index.html', ''): errors.append('H106: нет {{app_token}} в index.html')
if 'app-agent/run' not in all_text: errors.append('H106: нет вызова app-agent/run')
for legacy in ('etb_run_expert', 'parent.extellaDesktop'):
    if legacy in all_text: errors.append(f'H106: найден удалённый мост {legacy}')
if 'targets' not in files.get('extella-bridge.js', ''): errors.append('H106: последующие вызовы не закрепляются targets')
if errors:
    print('НЕ ГОТОВО\n' + '\n'.join(f'- {item}' for item in errors)); raise SystemExit(1)
print('ГОТОВО: структура, мост и запреты проверены')

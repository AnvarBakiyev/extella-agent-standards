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
if "type:'etb_run_expert'" not in all_text: errors.append('Нет единого вызова etb_run_expert')
if 'etb_expert_result' not in all_text: errors.append('Нет ожидания etb_expert_result')
if errors:
    print('НЕ ГОТОВО\n' + '\n'.join(f'- {item}' for item in errors)); raise SystemExit(1)
print('ГОТОВО: структура, мост и запреты проверены')

#!/usr/bin/env python3
"""Собрать безопасный zip: index.html лежит в корне архива."""
from __future__ import annotations
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP, DIST = ROOT / 'app', ROOT / 'dist'
REQUIRED = ('index.html', 'styles.css', 'app.js', 'extella-bridge.js')

def main() -> None:
    missing = [name for name in REQUIRED if not (APP / name).is_file()]
    if missing: raise SystemExit(f'Нет файлов: {", ".join(missing)}')
    DIST.mkdir(exist_ok=True)
    output = DIST / 'extella-app.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in APP.rglob('*'):
            if path.is_file(): archive.write(path, path.relative_to(APP))
    with zipfile.ZipFile(output) as archive:
        if 'index.html' not in archive.namelist(): raise SystemExit('index.html должен быть в корне zip')
    print(f'{output}  sha256={hashlib.sha256(output.read_bytes()).hexdigest()}')

if __name__ == '__main__': main()

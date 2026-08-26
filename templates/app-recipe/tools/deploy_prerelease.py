#!/usr/bin/env python3
"""Шаблон закрытой выкладки. Не публикует приложение в магазин."""
from __future__ import annotations
import argparse, json, os, urllib.request, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OS = 'https://os.extella.ai'

def multipart(fields: dict[str,str], page: Path) -> tuple[bytes,str]:
    boundary = '----extella' + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items(): chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks += [f'--{boundary}\r\nContent-Disposition: form-data; name="page"; filename="{page.name}"\r\nContent-Type: application/zip\r\n\r\n'.encode(), page.read_bytes(), b'\r\n', f'--{boundary}--\r\n'.encode()]
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'

def request(path: str, token: str, data: bytes | None = None, content_type: str | None = None) -> str:
    req = urllib.request.Request(OS + path, data=data, method='POST' if data else 'GET')
    req.add_header('X-Extella-Token', token)
    if content_type: req.add_header('Content-Type', content_type)
    with urllib.request.urlopen(req, timeout=120) as response: return response.read().decode('utf-8', 'replace')

def sse_done(raw: str) -> dict:
    """publish-stream отвечает событиями, а не одним JSON."""
    for line in raw.splitlines():
        if not line.startswith('data:'): continue
        event=json.loads(line.split('data:',1)[1].strip())
        if event.get('type') == 'error': raise RuntimeError(event.get('message','Extella вернула ошибку'))
        if event.get('type') == 'done': return event
    raise RuntimeError('Extella не прислала завершающее событие')

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--source-agent',required=True); args=parser.parse_args()
    token=os.environ.get('EXTELLA_TOKEN')
    if not token: raise SystemExit('Укажи токен только в переменной окружения EXTELLA_TOKEN.')
    page=ROOT/'dist'/'extella-app.zip'
    if not page.is_file(): raise SystemExit('Сначала запусти python3 tools/build.py')
    card=json.loads((ROOT/'listing.json').read_text())
    fields={'name':card['name'],'description':card['description'],'version':card['version'],'price_credits':'0','source_type':'agent','source_id':args.source_agent,'attach_agent':'1','app_scopes':'[]','tags':json.dumps(card.get('tags',[])),'allowed_origins':json.dumps(['null',OS])}
    body, content_type=multipart(fields,page)
    # Важно: этот endpoint создаёт черновик. Не добавляй публичный Publish без отдельного решения владельца.
    result=sse_done(request('/api/publish-stream',token,body,content_type))
    print(json.dumps({'listing_id':result.get('listing_id'),'version_id':result.get('version_id'),'published':False},ensure_ascii=False))

if __name__ == '__main__': main()

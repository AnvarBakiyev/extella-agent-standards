"""Замер второй версии: ключ из {{token}} в странице → эксперт на машине.
Ключ держится в памяти процесса и НЕ печатается; наружу — длина, отпечаток, коды."""
import importlib.util, json, pathlib, re, sys, hashlib, urllib.request, urllib.error
ЗДЕСЬ = pathlib.Path(__file__).resolve().parent
КОРЕНЬ = pathlib.Path("/private/tmp/claude-501/-Users-anvarbakiyev-Extella-Claude-Bridge/115cc8f9-27a8-4fc2-ac5c-6f53d8a48bc2/scratchpad/std")
сп = importlib.util.spec_from_file_location("d", КОРЕНЬ / "store_app/product/deploy_prerelease_claude.py")
d = importlib.util.module_from_spec(сп); sys.argv = ["x"]; сп.loader.exec_module(d)
ч = json.loads((ЗДЕСЬ / "draft.json").read_text())

_, стр = d.request(d.OS_BASE, f"/app-page/{ч['listing_id']}")
пропуск = re.search(r'var APP_TOKEN = /\*APP_TOKEN\*/"([^"]*)"', стр).group(1)
м = re.search(r'var КЛЮЧ = "([^"]*)";', стр)
ключ = м.group(1) if м else ""
подставлен = bool(ключ) and not ключ.startswith("{{")
отп = lambda з: hashlib.sha256(з.encode()).hexdigest()[:8]
диск = (pathlib.Path.home() / ".extella/api_token.txt").read_text().strip()
print("страница отдана версии 0.2.0:", "Подключить мой редактор" in стр)
print("{{token}} подставлен:", подставлен, "| длина:", len(ключ) if подставлен else 0,
      "| совпадает с ключом на Mac:", подставлен and ключ == диск)

def окно(эксперт, params, dev):
    тело = {"app_token": пропуск, "expert_name": эксперт, "params": params, "targets": [dev]}
    r = urllib.request.Request("https://os.extella.ai/api/app-agent/run", data=json.dumps(тело).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=120) as о: к, с = о.status, о.read().decode()
    except urllib.error.HTTPError as e: к, с = e.code, e.read().decode()[:300]
    try:
        о = json.loads(с)
        for _ in range(4):
            if isinstance(о, dict) and "result" in о:
                в = о["result"]; о = json.loads(в) if isinstance(в, str) else в
    except Exception: о = {"сырое": с[:200]}
    if isinstance(о, dict):
        for лишнее in ("отпечаток_ключа_на_диске", "файл"): о.pop(лишнее, None)
    return к, о

МАШИНЫ = {"Mac": "24f37e45-8c9f-4896-b64f-0dcd0cd8b0e4", "VPS": "85800354-f7b7-449f-b526-9357cd91f780"}
if len(sys.argv) == 3: МАШИНЫ = {sys.argv[1]: sys.argv[2]}
for имя, dev in МАШИНЫ.items():
    к, о = окно("dev_connect_probe", {"token": ключ, "метка": f"{имя}/ключ_из_страницы"}, dev)
    print(f"\n{имя} · проба с ключом из страницы: HTTP {к}\n   ", json.dumps(о, ensure_ascii=False)[:420])
    к, о = окно("dev_connect_assistant", {"проверить_только": "да"}, dev)
    print(f"{имя} · «Только проверить»: HTTP {к}\n   ", json.dumps(о, ensure_ascii=False)[:300])

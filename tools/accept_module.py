#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приём модуля от стороннего разработчика архивом.

ЗАЧЕМ. Пока модули пишет одна команда, библиотека растёт медленно. Разработчик со стороны
может прислать готовый модуль архивом, но архив пришёл из-за периметра, и верить ему
нельзя. Приёмка отвечает на один вопрос: встанет ли модуль в библиотеку в той же форме,
что модули в extella-plugins/modules, и пройдёт ли он тот же гейт паспорта.

Что проверяется, по порядку:
  1. архив безопасен: пути только внутрь, без «..» и абсолютных путей, размер и число
     файлов в пределах, чтобы архивная бомба не распаковалась;
  2. в архиве ровно один модуль, то есть одна папка с docs/automation_passport.yaml;
  3. форма папки: MANIFEST.yaml, README.md, manifest_check.py, docs/automation_passport.yaml,
     experts/;
  4. паспорт проходит check_automation_passport.py и объявлен как kind: module;
  5. имя папки совпадает с automation_id;
  6. manifest_check.py совпадает с каноном templates/manifest_check.py байт в байт;
  7. у каждого эксперта из паспорта есть файл, файл разбирается как Python, и первая
     функция верхнего уровня называется именем эксперта: рантайм зовёт первую функцию
     файла (H94 в DEPLOY_REQUIREMENTS.md);
  8. в experts/ нет файлов без записи в паспорте;
  9. если указана библиотека, модуль с тем же id сравнивается по версии.

Приёмка ничего из архива не исполняет: код модуля не импортируется, его самопроверка
и его копия manifest_check.py не запускаются. Исполняется только код стандартов.
Запустить модуль можно после приёмки, на пробном агенте.

Запуск:
  python3 tools/accept_module.py модуль.zip
  python3 tools/accept_module.py модуль.zip --библиотека ../extella-plugins/modules
  python3 tools/accept_module.py модуль.zip --библиотека ../extella-plugins/modules --распаковать
  python3 tools/accept_module.py модуль.zip --json
  python3 tools/accept_module.py --selftest

Коды выхода: 0 — модуль принят; 1 — отказ с причинами; 2 — неверный запуск.
"""
import ast
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_agent_passport import load_passport              # noqa: E402  единый разбор паспорта
from check_automation_passport import check_report          # noqa: E402  тот же гейт, что у библиотеки

CANON_MANIFEST_CHECK = HERE.parent / "templates" / "manifest_check.py"
REQUIRED = ("MANIFEST.yaml", "README.md", "manifest_check.py", "docs/automation_passport.yaml")
PASSPORT_TAIL = "docs/automation_passport.yaml"
# Пределы архива. Модули библиотеки весят десятки килобайт; предел в тысячу раз выше
# не мешает честному модулю и не даёт распаковать бомбу.
MAX_FILES = 500
MAX_TOTAL_BYTES = 50 * 1024 * 1024
JUNK_NAMES = {".DS_Store", "Thumbs.db"}


def _issue(bucket, code, path, ru, en, detail=None):
    item = {"code": code, "path": path, "message_ru": ru, "message_en": en}
    if detail:
        item["detail"] = detail
    bucket.append(item)


def _note(rep, code, ru, en):
    rep["notes"].append({"code": code, "message_ru": ru, "message_en": en})


def _norm(name):
    return name.replace("\\", "/")


def _junk(name):
    """Мусор архиваторов macOS и Windows в модуль не входит и отказа не вызывает."""
    n = _norm(name)
    return (n.startswith("__MACOSX/") or PurePosixPath(n).name in JUNK_NAMES
            or "/__pycache__/" in "/" + n or n.endswith(".pyc"))


def _unsafe(name):
    """Путь из архива опасен, если ведёт наружу. Молча чистить его нельзя: архив с таким
    путём принимается как исправный, и немой отказ хуже громкой ошибки."""
    n = _norm(name)
    if n.startswith("/") or (len(n) > 1 and n[1] == ":"):
        return True
    return ".." in PurePosixPath(n).parts


def _parse_expert(text):
    """Директивы платформы вида $extens(...) не являются Python. Их строки убираются перед
    разбором, иначе канонный эксперт с include получил бы ложный отказ."""
    clean = "\n".join("" if ln.lstrip().startswith("$") else ln for ln in text.splitlines())
    return ast.parse(clean)


def _version_key(v):
    return [(0, int(p)) if p.isdigit() else (1, p) for p in str(v or "").split(".")]


def _check_module(mod, root, rep, library):
    errors, warnings = rep["errors"], rep["warnings"]

    missing = [r for r in REQUIRED if not (mod / r).is_file()]
    if not (mod / "experts").is_dir():
        missing.append("experts/")
    for m in missing:
        _issue(errors, "ACCEPT_LAYOUT_MISSING", m,
               "нет обязательного %s: модуль собирается в той же форме, что модули библиотеки" % m,
               "required %s is missing: a module keeps the layout of library modules" % m)

    pp = mod / PASSPORT_TAIL
    if not pp.is_file():
        return
    doc = load_passport(str(pp))
    if not isinstance(doc, dict):
        _issue(errors, "ACCEPT_PASSPORT_UNREADABLE", PASSPORT_TAIL,
               "паспорт не читается", "the passport cannot be read")
        return

    a = doc.get("automation") if isinstance(doc.get("automation"), dict) else {}
    rep["module_id"] = str(a.get("automation_id") or "").strip() or None
    rep["version"] = str(a.get("version") or "").strip() or None
    v = a.get("verified")
    rep["verified"] = isinstance(v, dict) and bool(str(v.get("at") or "").strip())

    if str(a.get("kind") or "").strip().lower() != "module":
        _issue(errors, "ACCEPT_NOT_MODULE", "automation.kind",
               "паспорт не объявлен как kind: module, а автоматизация принимается другим путём",
               "the passport is not declared kind: module, and an automation is accepted another way")
    for e in check_report(doc)["errors"]:
        _issue(errors, "ACCEPT_PASSPORT_GATE", e.get("path") or "",
               "гейт паспорта: " + str(e.get("message_ru") or e.get("code")),
               "passport gate: " + str(e.get("message_en") or e.get("code")), detail=e.get("code"))

    folder = PurePosixPath(root).name
    if root != "." and rep["module_id"] and folder != rep["module_id"]:
        _issue(errors, "ACCEPT_FOLDER_NAME", root,
               "папка «%s» не совпадает с automation_id «%s»: в библиотеке папка называется по id"
               % (folder, rep["module_id"]),
               "folder %r does not match automation_id %r: in the library a folder is named by id"
               % (folder, rep["module_id"]))

    copy = mod / "manifest_check.py"
    if copy.is_file() and copy.read_bytes() != CANON_MANIFEST_CHECK.read_bytes():
        _issue(errors, "ACCEPT_MANIFEST_CHECK_NOT_CANON", "manifest_check.py",
               "manifest_check.py отличается от канона templates/manifest_check.py: такой модуль "
               "останавливал бы установку там, где другие её продолжают",
               "manifest_check.py differs from templates/manifest_check.py: such a module would "
               "stop an install where others continue")

    comps = doc.get("components") if isinstance(doc.get("components"), dict) else {}
    declared_files = set()
    mod_real = mod.resolve()
    for e in comps.get("experts") or []:
        if not isinstance(e, dict) or not str(e.get("name") or "").strip():
            continue
        name = str(e["name"]).strip()
        rep["experts"].append(name)
        src = _norm(str(e.get("source") or "experts/%s.py" % name))
        f = mod / src
        if not f.resolve().is_relative_to(mod_real):
            _issue(errors, "ACCEPT_EXPERT_SOURCE_OUTSIDE", src,
                   "source эксперта «%s» указывает за пределы модуля" % name,
                   "the source of expert %r points outside the module" % name)
            continue
        declared_files.add(f.resolve())
        if not f.is_file():
            _issue(errors, "ACCEPT_EXPERT_FILE_MISSING", src,
                   "нет файла эксперта «%s»" % name, "the file of expert %r is missing" % name)
            continue
        try:
            tree = _parse_expert(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as ex:
            _issue(errors, "ACCEPT_EXPERT_SYNTAX", src,
                   "эксперт «%s» не разбирается как Python в UTF-8: %s" % (name, ex),
                   "expert %r does not parse as UTF-8 Python: %s" % (name, ex))
            continue
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not funcs or funcs[0] != name:
            first = funcs[0] if funcs else "нет ни одной"
            _issue(errors, "ACCEPT_EXPERT_FIRST_FUNCTION", src,
                   "первая функция верхнего уровня в %s называется «%s», а не «%s»: рантайм зовёт "
                   "первую функцию файла (H94), и вызов уйдёт не туда" % (src, first, name),
                   "the first top-level function in %s is %r, not %r: the runtime calls the first "
                   "function of the file (H94), so the call goes elsewhere" % (src, first, name))
        elif len(funcs) > 1:
            _issue(warnings, "ACCEPT_EXPERT_EXTRA_FUNCTIONS", src,
                   "кроме «%s» на верхнем уровне есть %s: по H94 вспомогательные держат вложенными"
                   % (name, ", ".join(funcs[1:])),
                   "besides %r the top level has %s: per H94 helpers stay nested"
                   % (name, ", ".join(funcs[1:])))
        loose = [n for n in tree.body
                 if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Import, ast.ImportFrom))
                 and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        if loose:
            _issue(warnings, "ACCEPT_EXPERT_TOP_LEVEL_CODE", src,
                   "в %s есть код вне функций: он исполняется при каждой загрузке эксперта" % src,
                   "%s has code outside functions: it runs on every expert load" % src)

    experts_dir = mod / "experts"
    for f in sorted(experts_dir.glob("*.py")) if experts_dir.is_dir() else []:
        if f.resolve() not in declared_files:
            _issue(errors, "ACCEPT_EXPERT_UNDECLARED", "experts/" + f.name,
                   "файл experts/%s не объявлен в паспорте: код без «что делает» поиск не найдёт, "
                   "и границ у него нет" % f.name,
                   "experts/%s is not declared in the passport: code without «what» is unfindable "
                   "and has no limits" % f.name)

    if library and rep["module_id"]:
        old_pp = Path(library) / rep["module_id"] / PASSPORT_TAIL
        if old_pp.is_file():
            old = load_passport(str(old_pp)) or {}
            old_v = str((old.get("automation") or {}).get("version") or "")
            rep["library"] = {"exists": True, "version": old_v}
            if _version_key(rep["version"]) <= _version_key(old_v):
                _issue(errors, "ACCEPT_VERSION_NOT_NEWER", "automation.version",
                       "в библиотеке уже есть «%s» версии %s, присланная версия %s не новее"
                       % (rep["module_id"], old_v, rep["version"]),
                       "the library already has %r version %s, the sent version %s is not newer"
                       % (rep["module_id"], old_v, rep["version"]))
            else:
                _note(rep, "ACCEPT_UPDATE", "обновление с %s до %s" % (old_v, rep["version"]),
                      "update from %s to %s" % (old_v, rep["version"]))
        else:
            rep["library"] = {"exists": False}
            _note(rep, "ACCEPT_NEW_MODULE", "в библиотеке такого модуля ещё нет",
                  "the library has no such module yet")

    if not rep["verified"]:
        _note(rep, "ACCEPT_NOT_VERIFIED",
              "метки «проверено живьём» нет: модуль входит в покрытие по гейту, но не в число проверенных",
              "no «verified live» mark: the module counts by the gate but not among verified ones")


def inspect_archive(archive, library=None, unpack=False):
    rep = {"accepted": False, "module_id": None, "version": None, "verified": False,
           "experts": [], "errors": [], "warnings": [], "notes": [], "root": None, "library": None}
    errors = rep["errors"]
    try:
        zf = zipfile.ZipFile(archive)
    except (zipfile.BadZipFile, OSError) as ex:
        _issue(errors, "ACCEPT_NOT_ZIP", str(archive),
               "файл не читается как zip-архив: %s" % ex, "the file is not a readable zip archive: %s" % ex)
        return rep

    with zf:
        infos = [i for i in zf.infolist() if not _junk(i.filename)]
        if len(infos) > MAX_FILES:
            _issue(errors, "ACCEPT_TOO_MANY_FILES", str(archive),
                   "в архиве %d файлов, предел %d" % (len(infos), MAX_FILES),
                   "the archive has %d files, the limit is %d" % (len(infos), MAX_FILES))
            return rep
        total = sum(i.file_size for i in infos)
        if total > MAX_TOTAL_BYTES:
            _issue(errors, "ACCEPT_TOO_LARGE", str(archive),
                   "распакованный архив займёт %d байт, предел %d" % (total, MAX_TOTAL_BYTES),
                   "the unpacked archive takes %d bytes, the limit is %d" % (total, MAX_TOTAL_BYTES))
            return rep
        bad = [i.filename for i in infos if _unsafe(i.filename)]
        if bad:
            _issue(errors, "ACCEPT_UNSAFE_PATH", bad[0],
                   "путь в архиве ведёт за его пределы: %s" % bad[0],
                   "a path in the archive leads outside it: %s" % bad[0])
            return rep

        roots = sorted({str(PurePosixPath(_norm(i.filename)).parent.parent)
                        for i in infos if _norm(i.filename).endswith(PASSPORT_TAIL)})
        if not roots:
            _issue(errors, "ACCEPT_NO_PASSPORT", str(archive),
                   "в архиве нет docs/automation_passport.yaml: без паспорта модуль не найти и не проверить",
                   "the archive has no docs/automation_passport.yaml: without a passport the module "
                   "cannot be found or checked")
            return rep
        if len(roots) > 1:
            _issue(errors, "ACCEPT_MANY_MODULES", ", ".join(roots),
                   "в одном архиве несколько модулей: %s. Один архив содержит один модуль" % ", ".join(roots),
                   "one archive holds several modules: %s. One archive holds one module" % ", ".join(roots))
            return rep
        root = rep["root"] = roots[0]

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            for i in infos:
                if i.is_dir():
                    continue
                dest = (base / _norm(i.filename)).resolve()
                if not dest.is_relative_to(base):
                    _issue(errors, "ACCEPT_UNSAFE_PATH", i.filename,
                           "путь в архиве ведёт за его пределы: %s" % i.filename,
                           "a path in the archive leads outside it: %s" % i.filename)
                    return rep
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(i) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)

            mod = base if root == "." else base / root
            _check_module(mod, root, rep, library)
            rep["accepted"] = not errors

            if unpack and rep["accepted"] and library and rep["module_id"]:
                target = Path(library) / rep["module_id"]
                if target.exists():
                    _issue(errors, "ACCEPT_TARGET_EXISTS", str(target),
                           "папка %s уже есть: старую версию убирают через git, чтобы замена "
                           "была видна в запросе на слияние" % target,
                           "folder %s already exists: remove the old version through git so the "
                           "replacement shows in the pull request" % target)
                    rep["accepted"] = False
                else:
                    shutil.copytree(mod, target, ignore=shutil.ignore_patterns("__pycache__", *JUNK_NAMES))
                    _note(rep, "ACCEPT_UNPACKED", "модуль распакован в %s" % target,
                          "the module is unpacked into %s" % target)
    return rep


def print_report(archive, rep):
    print("Архив: %s" % archive)
    print("Модуль: %s %s · проверено живьём: %s" % (rep["module_id"] or "id не прочитан",
                                                     rep["version"] or "", "да" if rep["verified"] else "нет"))
    if rep["experts"]:
        print("Эксперты: %s" % ", ".join(rep["experts"]))
    for title, key, mark in (("Ошибки", "errors", "✗"), ("Предупреждения", "warnings", "!")):
        if rep[key]:
            print("\n%s:" % title)
            for e in rep[key]:
                extra = " [%s]" % e["detail"] if e.get("detail") else ""
                print("  %s %s%s  %s: %s" % (mark, e["code"], extra, e["path"], e["message_ru"]))
    if rep["notes"]:
        print()
        for n in rep["notes"]:
            print("  · %s" % n["message_ru"])
    print("\nИтог: %s" % ("модуль принят" if rep["accepted"] else "отказ"))
    if rep["accepted"] and rep["module_id"]:
        print("Место в библиотеке: extella-plugins/modules/%s" % rep["module_id"])


def selftest():
    import copy
    from check_automation_passport import GOOD_MODULE
    global MAX_TOTAL_BYTES
    print("Самопроверка приёма модуля:")
    failed = []
    reports = []

    def expect(label, cond):
        print(("  ✓ " if cond else "  ✗ ") + label)
        if not cond:
            failed.append(label)

    def codes(rep, key="errors"):
        return {e["code"] for e in rep[key]}

    canon = CANON_MANIFEST_CHECK.read_bytes()
    mid = GOOD_MODULE["automation"]["automation_id"]

    def files(root=mid, passport=None, expert_code=None, extra=None):
        out = {
            root + "/" + PASSPORT_TAIL: json.dumps(passport or GOOD_MODULE, ensure_ascii=False),
            root + "/MANIFEST.yaml": 'checks:\n  - kind: python\n    min_version: "3.10"\n'
                                     '    fix_ru: "поставь Python 3.10+"\n',
            root + "/README.md": "# проба\n",
            root + "/manifest_check.py": canon,
            root + "/experts/%s.py" % mid: (expert_code if expert_code is not None
                                            else 'def %s(text=""):\n    return text\n' % mid),
        }
        out.update(extra or {})
        return out

    def run(tmp, name, content, **kw):
        path = os.path.join(tmp, name)
        with zipfile.ZipFile(path, "w") as z:
            for arc, data in content.items():
                z.writestr(arc, data if isinstance(data, bytes) else data.encode("utf-8"))
        rep = inspect_archive(path, **kw)
        reports.append(rep)
        return rep

    with tempfile.TemporaryDirectory() as tmp:
        r = run(tmp, "good.zip", files())
        expect("исправный модуль принят", r["accepted"] and not r["errors"])
        expect("модуль без метки проверки принят, и это видно", "ACCEPT_NOT_VERIFIED" in codes(r, "notes"))

        r = run(tmp, "slip.zip", files(extra={"../evil.py": "x"}))
        expect("путь через «..» отвергнут", "ACCEPT_UNSAFE_PATH" in codes(r))
        r = run(tmp, "abs.zip", files(extra={"/abs/evil.py": "x"}))
        expect("абсолютный путь отвергнут", "ACCEPT_UNSAFE_PATH" in codes(r))

        saved = MAX_TOTAL_BYTES
        try:
            MAX_TOTAL_BYTES = 10
            r = run(tmp, "big.zip", files())
        finally:
            MAX_TOTAL_BYTES = saved
        expect("архив больше предела отвергнут до распаковки", "ACCEPT_TOO_LARGE" in codes(r))

        both = files()
        both.update(files(root="vtoroy"))
        expect("два модуля в одном архиве отвергнуты",
               "ACCEPT_MANY_MODULES" in codes(run(tmp, "two.zip", both)))

        expect("папка не по automation_id отвергнута",
               "ACCEPT_FOLDER_NAME" in codes(run(tmp, "folder.zip", files(root="drugoe_imya"))))

        pp = copy.deepcopy(GOOD_MODULE)
        del pp["automation"]["kind"]
        expect("паспорт без kind: module отвергнут",
               "ACCEPT_NOT_MODULE" in codes(run(tmp, "kind.zip", files(passport=pp))))

        pp = copy.deepcopy(GOOD_MODULE)
        pp["components"]["experts"][0].pop("what")
        r = run(tmp, "what.zip", files(passport=pp))
        expect("эксперт без «что делает» отвергнут тем же гейтом, что у библиотеки",
               "MODULE_EXPERT_WHAT_REQUIRED" in {e.get("detail") for e in r["errors"]})

        bad_copy = files()
        bad_copy[mid + "/manifest_check.py"] = canon + "\n# подделка\n".encode("utf-8")
        expect("копия manifest_check.py не по канону отвергнута",
               "ACCEPT_MANIFEST_CHECK_NOT_CANON" in codes(run(tmp, "copy.zip", bad_copy)))

        helper_first = "def _pomoshnik():\n    pass\n\ndef %s():\n    return 1\n" % mid
        expect("вспомогательная функция перед экспертом отвергнута (H94)",
               "ACCEPT_EXPERT_FIRST_FUNCTION" in codes(run(tmp, "h94.zip", files(expert_code=helper_first))))

        marker = os.path.join(tmp, "исполнено.txt")
        runs_code = "open(%r, 'w').write('x')\ndef %s():\n    return 1\n" % (marker, mid)
        r = run(tmp, "exec.zip", files(expert_code=runs_code))
        expect("код из архива не исполняется: метка на диске не появилась", not os.path.exists(marker))
        expect("код вне функций даёт предупреждение", "ACCEPT_EXPERT_TOP_LEVEL_CODE" in codes(r, "warnings"))

        directive = '$extens("include.py")\ndef %s():\n    return 1\n' % mid
        expect("директива $extens не даёт ложного отказа",
               run(tmp, "extens.zip", files(expert_code=directive))["accepted"])

        extra_expert = files(extra={mid + "/experts/lishniy.py": "def lishniy():\n    pass\n"})
        expect("файл эксперта без записи в паспорте отвергнут",
               "ACCEPT_EXPERT_UNDECLARED" in codes(run(tmp, "undeclared.zip", extra_expert)))

        pp = copy.deepcopy(GOOD_MODULE)
        pp["components"]["experts"][0]["source"] = "../evil.py"
        expect("source эксперта за пределами модуля отвергнут",
               "ACCEPT_EXPERT_SOURCE_OUTSIDE" in codes(run(tmp, "source.zip", files(passport=pp))))

        junk = files(extra={"__MACOSX/%s/docs/._automation_passport.yaml" % mid: "x",
                            mid + "/.DS_Store": "x"})
        expect("мусор архиваторов не мешает приёму", run(tmp, "junk.zip", junk)["accepted"])

        lib = os.path.join(tmp, "lib")
        os.makedirs(os.path.join(lib, mid, "docs"))
        with open(os.path.join(lib, mid, PASSPORT_TAIL), "w", encoding="utf-8") as f:
            json.dump(GOOD_MODULE, f, ensure_ascii=False)
        expect("та же версия, что в библиотеке, отвергнута",
               "ACCEPT_VERSION_NOT_NEWER" in codes(run(tmp, "same.zip", files(), library=lib)))
        pp = copy.deepcopy(GOOD_MODULE)
        pp["automation"]["version"] = "0.2.0"
        r = run(tmp, "newer.zip", files(passport=pp), library=lib)
        expect("более новая версия принята как обновление", r["accepted"] and "ACCEPT_UPDATE" in codes(r, "notes"))

        fresh = os.path.join(tmp, "fresh")
        os.makedirs(fresh)
        r = run(tmp, "unpack.zip", files(), library=fresh, unpack=True)
        expect("принятый модуль распакован в библиотеку",
               r["accepted"] and os.path.isfile(os.path.join(fresh, mid, PASSPORT_TAIL)))
        r = run(tmp, "unpack2.zip", files(), library=fresh, unpack=True)
        expect("повторная распаковка поверх папки не затирает её",
               not r["accepted"] and "ACCEPT_VERSION_NOT_NEWER" in codes(r))

        every = [x for rep in reports for key in ("errors", "warnings", "notes") for x in rep[key]]
        expect("каждое сообщение на двух языках (§3.26)",
               bool(every) and all(x.get("message_ru") and x.get("message_en") for x in every))

    print("ИТОГ САМОПРОВЕРКИ: " + ("все проверки прошли" if not failed else "есть провалы"))
    return 0 if not failed else 1


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # консоль Windows с cp1251 иначе падает на «✓»
    except Exception:
        pass
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    if argv[0] == "--selftest":
        return selftest()
    archive, library = argv[0], None
    if "--библиотека" in argv:
        i = argv.index("--библиотека")
        if i + 1 >= len(argv):
            print("после --библиотека нужен путь к папке модулей")
            return 2
        library = argv[i + 1]
        if not Path(library).is_dir():
            print("папки библиотеки нет: %s" % library)
            return 2
    unpack = "--распаковать" in argv
    if unpack and not library:
        print("--распаковать работает только вместе с --библиотека")
        return 2
    rep = inspect_archive(archive, library, unpack)
    if "--json" in argv:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_report(archive, rep)
    return 0 if rep["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# expert: wz_capability_find
# description: Дверь агента к способностям Extella. По задаче словами возвращает 3-5 подходящих способностей из живого Capability Registry (эксперты, автоматизации, модули, блоки композитора, CSPL, установленное) с требованиями и границами из паспортов. Честно говорит «не нашёл» и «границы неизвестны» вместо выдумки. Ничего не запускает и не ставит — только находит.
#
# Исходник в git: extella-agent-standards/experts/wz_capability_find.py (03.09.2026). До этого дня
# код жил только в общем пространстве платформы — там, откуда его нельзя пересобрать.
# Изменение 03.09: требования к машине (`needs`) берутся ещё и из реестра паспортов, куда
# сборщик кладёт их из MANIFEST.yaml модуля.

def wz_capability_find(task="", limit="5", api_token="", api_base="https://api.extella.ai") -> dict:
    """Единственный способ для агента узнать, ЧТО он умеет.

    Зачем эксперт, а не прямой вызов платформы: `experts_db/list` показывает каждому агенту свой
    мир (Travel 343 записи, Строитель 716, agent_extella_default 5096 — живая проверка 28.07), и
    агент турагентства не видит НИ ОДНОГО своего ta_-эксперта. Реестр читается под ОДНИМ
    фиксированным агентом, поэтому все агенты получают ОДИНАКОВЫЙ ответ.

    Как читается реестр (перенос 28.07.2026): по СВОБОДНОМУ имени `capability:registry:v2`
    обычным общим чтением. Опыт того дня показал, что `global: true` работает исправно, если у
    имени нет истории; ломали его близнецы старого ключа — записи с тем же именем в разных
    областях, из которых kv/get отдавал не ту. Старое имя оставлено запасным путём для
    установок, где реестр ещё не пересобирался (docs/INCIDENT_KV_SCOPE_SHADOWING.md).
    """
    import json, base64, re, urllib.request
    from pathlib import Path

    # ПЕРЕНОС 28.07.2026: читаем СВОБОДНОЕ имя обычным общим чтением. Закрепление агента больше
    # не нужно — опыт показал, что `global: true` работает у имени без истории, а ломали его
    # близнецы старого ключа. Старое имя оставлено запасным: у коллег с прежней установкой
    # реестр ещё пишется по нему.
    REG_AGENT = "agent_extella_default"          # запасной путь по старому имени
    REG_KEY = "capability:registry:v2"
    REG_KEY_LEGACY = "capability:registry"

    def _blank(v):
        return (not v) or str(v).startswith("{{")

    if _blank(task):
        return {"status": "error", "code": "empty_task",
                "message_ru": "не сказано, какую задачу надо закрыть",
                "message_en": "the task to solve is not stated"}
    if _blank(api_base):
        api_base = "https://api.extella.ai"
    try:
        top = max(1, min(int(str(limit)), 20))
    except Exception:
        top = 5

    cfg = {}
    try:
        p = Path.home() / "extella_wizard" / "app" / "config.json"
        cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        cfg = {}
    if _blank(api_token):
        api_token = cfg.get("auth_token", "")
    if not api_token:
        return {"status": "error", "code": "no_api_token",
                "message_ru": "нет токена доступа к платформе",
                "message_en": "no platform api token"}

    def api(path, payload, timeout=60):
        req = urllib.request.Request(
            api_base.rstrip("/") + path, data=json.dumps(payload).encode("utf-8"),
            headers={"X-Auth-Token": api_token, "Content-Type": "application/json",
                     "X-Profile-Id": "default", "X-Agent-Id": REG_AGENT}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    # ---------- 1. Живой реестр (b64-шарды: kv/set строит эмбеддинг, крупное значение не влезает).
    # Реестр уже на 19 шардов, и тянуть их на КАЖДЫЙ вопрос агента — это 19 сетевых вызовов и
    # десятки секунд ожидания. Кэшируем на устройстве по метке generated_at: в обычном случае
    # выходит один вызов. Кэш одноразовый: удалили — скачается заново, ничего не теряется.
    cache_path = Path.home() / "extella_wizard" / "registry" / "capability_registry_cache.json"
    items, reg_error, stale_stamp = [], None, None
    try:
        meta = json.loads(api("/api/kv/get", {"key": REG_KEY, "global": True}).get("value") or "{}")
        if not meta.get("chunks"):
            # Свободного имени ещё нет (реестр на этой установке не пересобирался) — честно
            # уходим на старое, а не делаем вид, что способностей нет.
            meta = json.loads(api("/api/kv/get", {"key": REG_KEY_LEGACY}).get("value") or "{}")
            key_used = REG_KEY_LEGACY
        else:
            key_used = REG_KEY
        stamp = str(meta.get("generated_at") or "")
        cached = {}
        try:
            if cache_path.exists():
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cached = {}
        if stamp and cached.get("generated_at") == stamp and isinstance(cached.get("capabilities"), list):
            items = cached["capabilities"]
        else:
            parts = []
            for i in range(int(meta.get("chunks") or 0)):
                parts.append(api("/api/kv/get", {"key": "%s:%d" % (key_used, i),
                                                 "global": True}).get("value") or "")
            raw = json.loads(base64.b64decode("".join(parts)).decode("utf-8")) if parts else []
            # Писатель кладёт список под ключом capabilities; items оставлен для старых сборок.
            items = raw if isinstance(raw, list) else (raw.get("capabilities") or raw.get("items") or [])
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({"generated_at": stamp, "capabilities": items},
                                                 ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass                              # кэш — удобство; не записался, значит не записался
    except Exception as ex:
        reg_error = str(ex)[:160]
        # Платформа недоступна, а кэш есть — отвечаем по нему и говорим об этом прямо,
        # а не выдаём вчерашние данные за сегодняшние.
        try:
            if cache_path.exists():
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached.get("capabilities"), list) and cached["capabilities"]:
                    items, reg_error = cached["capabilities"], None
                    stale_stamp = cached.get("generated_at")
        except Exception:
            pass

    # ---------- 2. Паспорта: требования, границы, эффекты. Их в реестре нет, а решение без них слепое
    declared = {}
    declared_src = None
    try:
        cat = Path.home() / "extella_wizard" / "registry" / "capabilities_declared.json"
        doc = {}
        if cat.exists():
            doc = json.loads(cat.read_text(encoding="utf-8"))
            declared_src = "file"
        # Файл — только там, где его собрали из git; эксперт же исполняется где угодно (по
        # умолчанию — на VPS, живой случай 04.09.2026). Поэтому сборщик кладёт зеркало в KV
        # (build_capability_registry.py --publish), и берём его, если оно свежее локального.
        # Ошибка KV не ломает ответ: остаёмся на том, что есть, и говорим об этом.
        try:
            dmeta = json.loads(api("/api/kv/get", {"key": "capability:declared:v1",
                                                   "global": True}).get("value") or "{}")
            if dmeta.get("chunks") and str(dmeta.get("built_at") or "") > str(doc.get("built_at") or ""):
                parts = [api("/api/kv/get", {"key": "capability:declared:v1:%d" % i,
                                             "global": True}).get("value") or ""
                         for i in range(int(dmeta["chunks"]))]
                fetched = json.loads(base64.b64decode("".join(parts)).decode("utf-8"))
                if isinstance(fetched, dict) and fetched.get("automations") is not None:
                    doc, declared_src = fetched, "kv"
                    try:
                        cat.parent.mkdir(parents=True, exist_ok=True)
                        cat.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass                      # кэш — удобство; не записался, значит не записался
        except Exception:
            pass
        if doc:
            for a in (doc.get("automations") or []):
                needs, effect = [], "read"
                for it in (a.get("integrations") or []):
                    if it.get("scopes"):
                        needs.append("%s: %s" % (it.get("kind"), ", ".join(it["scopes"])))
                    if it.get("external_writes"):
                        effect = "external_write"
                # Требования к машине (03.09.2026): сборщик реестра берёт их из MANIFEST.yaml
                # модуля — «нужна программа tesseract», «желателен модуль sglang». Без них
                # сборщик знал бы границы, но не знал бы, на какой машине модуль вообще запустится.
                for n in (a.get("needs") or []):
                    if n not in needs:
                        needs.append(n)
                nm = a.get("name") or {}
                # Имя и цель автоматизации — единственный человеческий текст, который есть у
                # объявленной способности. Без него синтетическая карточка не находится словами.
                about = " · ".join([x for x in [nm.get("ru"), nm.get("en"), a.get("business_goal")]
                                    if x])
                base = {"owner": a.get("automation_id"), "limits": a.get("limits") or [],
                        "needs": needs, "effect": effect, "about": about,
                        "kind": a.get("kind") or "automation",
                        "declared": bool(a.get("passport_ok"))}
                whats = a.get("experts_what") or {}
                for name in (a.get("experts") or []):
                    rec = dict(base)
                    rec["what"] = whats.get(name)        # что делает СЛОВАМИ КЛИЕНТА
                    declared[name] = rec
                aid = a.get("automation_id")
                # У модуля с одним экспертом id модуля и имя эксперта совпадают (toolkit_ocr_read).
                # Запись эксперта уже лежит и несёт `what`; затирать её записью без `what` —
                # значит показать сборщику склейку вместо «что делает» (поймано 04.09.2026).
                if aid and aid not in declared:
                    declared[aid] = dict(base)
    except Exception:
        declared = {}

    # ---------- 2б. Слияние: объявленное в паспортах ОБЯЗАНО попасть в ответ, даже если реестр
    # его не видит. Живой случай 28.07: реестр строится под agent_extella_default, а тот не видит
    # НИ ОДНОГО ta_-эксперта турагентства — значит без этого слияния верный ответ выпадает вовсе.
    # Паспорт лежит в git и от скоупа платформы не зависит, поэтому он и закрывает дыру.
    known = {str(i.get("capability_id") or "") for i in items}
    for cid, d in declared.items():
        if cid and cid not in known:
            items.append({"capability_id": cid, "type": "declared_capability",
                          "title": d.get("what") or d.get("about") or cid,
                          "description": " · ".join([x for x in [d.get("what"), d.get("about"), cid,
                                                                 *(d.get("limits") or [])] if x]),
                          "surfaces": [], "source": "passport"})
            known.add(cid)

    # ---------- 3. Кандидаты. Семантика платформы решает языковой разрыв: задача по-русски,
    # описания в реестре в основном английские, поэтому пословное совпадение тут слабое.
    # Берём именно score, а не порядковый номер: выдача не пуста НИКОГДА, и по позиции
    # бессмыслица неотличима от попадания. Живой замер: осмысленный запрос даёт 40-55,
    # «запустить ракету на Марс» — 24-25. Порог 30 разделяет их чисто.
    SEM_FLOOR, SEM_FULL = 30.0, 60.0
    sem_score, sem_error = {}, None
    try:
        res = api("/api/blocks/search", {"query": task, "limit": 50})
        for m in (res.get("matches") or res.get("experts") or []):
            n = m.get("name") or m.get("expert_name")
            try:
                sc = float(m.get("score") or 0)
            except Exception:
                sc = 0.0
            if n and sc > sem_score.get(n, 0):
                sem_score[n] = sc
    except Exception as ex:
        sem_error = str(ex)[:160]

    STOP = {"и", "в", "на", "по", "для", "с", "как", "что", "мне", "нужно", "надо", "хочу",
            "the", "a", "an", "of", "to", "for", "in", "on", "and", "with", "i", "need", "want"}
    words = {w for w in re.findall(r"[\w\-]{3,}", str(task).lower()) if w not in STOP}

    def score(it):
        """Оба сигнала нормируются в 0..1, иначе семантика с её порядковым номером подавляет
        словесное совпадение полностью и объявленная способность не всплывает никогда."""
        cid = str(it.get("capability_id") or "")
        sem = 0.0
        if cid in sem_score:
            sem = max(0.0, min(1.0, (sem_score[cid] - SEM_FLOOR) / (SEM_FULL - SEM_FLOOR)))
        wrd = 0.0
        if words:
            title = str(it.get("title") or "").lower()
            desc = str(it.get("description") or "").lower()
            hit_t = sum(1 for w in words if w in title)
            hit_d = sum(1 for w in words if w in desc)
            wrd = min(1.0, (2.0 * hit_t + hit_d) / (2.0 * len(words)))
        # Одно случайно совпавшее слово — не доказательство. Совпадение засчитывается, только
        # если семантика подтвердила ИЛИ совпала половина слов задачи. Иначе «запустить ракету
        # на Марс» находит всё, где есть слово «запустить», и обещание честности рушится.
        if sem <= 0.0 and wrd < 0.5:
            return 0.0
        # Объявленное чуть выше при прочих равных: у него известны границы и требования.
        return 0.6 * sem + 0.6 * wrd + (0.15 if cid in declared else 0.0)

    # Порог, а не «больше нуля»: иначе «не нашёл» не наступает никогда и обещание честности
    # превращается в ложь — семантика всегда что-нибудь вернёт.
    MATCH_FLOOR = 0.15
    ranked = sorted(items, key=score, reverse=True)
    picked = [it for it in ranked if score(it) >= MATCH_FLOOR][:top]

    def card(it):
        cid = str(it.get("capability_id") or "")
        d = declared.get(cid)
        # У объявленной способности «что делает» — это ровно текст паспорта, а не склейка,
        # которую мы собирали для поиска. Клеим для матчинга, показываем — человеческое.
        passport_what = str((d or {}).get("what") or "").strip()
        desc = passport_what or str(it.get("description") or "").strip()
        # description == title означает «описания нет» — но к тексту паспорта это не относится.
        if not passport_what and desc == str(it.get("title") or "").strip():
            desc = ""
        return {
            "capability_id": cid,
            "type": it.get("type"),
            "kind": (d or {}).get("kind"),
            "title": it.get("title"),
            "what": desc or None,
            "surfaces": it.get("surfaces") or [],
            "source": it.get("source"),
            "owner": (d or {}).get("owner"),
            "needs": (d or {}).get("needs"),
            "limits": (d or {}).get("limits"),
            "effect": (d or {}).get("effect"),
            "declared": bool(d and d.get("declared")),
            # Честность вместо подстановки: паспорта нет — так и говорим.
            "note_ru": None if d else "паспорта нет: границы, требования и эффекты неизвестны",
            "note_en": None if d else "no passport: limits, requirements and effects are unknown",
        }

    out = {"status": "success", "task": task, "checked": len(items),
           "found": len(picked), "capabilities": [card(it) for it in picked],
           # Откуда взяты паспорта: file | kv | None. None — на этом устройстве паспортов нет
           # вовсе, и все declared: false ниже говорят об этом, а не о самих способностях.
           "passports_from": declared_src, "passports": len(declared)}

    # ---------- 4. Честные отказы. Пустой реестр — дефект, а не тишина.
    if reg_error:
        out["status"] = "error"
        out["code"] = "registry_unreachable"
        out["message_ru"] = "реестр способностей не прочитан: " + reg_error
        out["message_en"] = "the capability registry could not be read: " + reg_error
        return out
    if not items:
        out["status"] = "success_with_defect"
        out["code"] = "registry_empty"
        out["message_ru"] = ("реестр способностей пуст — это дефект, а не отсутствие способностей. "
                             "Пересобери: run_expert wz_registry_rebuild")
        out["message_en"] = ("the capability registry is empty — that is a defect, not an absence "
                             "of capabilities. Rebuild it: run_expert wz_registry_rebuild")
        return out
    if not picked:
        out["message_ru"] = ("под эту задачу готовой способности не нашлось среди %d — "
                             "это повод построить новую, а не признак поломки" % len(items))
        out["message_en"] = ("no ready capability matches this task among %d — that is a reason to "
                             "build a new one, not a failure" % len(items))
    if stale_stamp:
        out["degraded_ru"] = ("платформа недоступна — ответ по кэшу от " + str(stale_stamp) +
                              "; новое с тех пор могло не попасть")
        out["degraded_en"] = ("platform unreachable — answered from the cache of " + str(stale_stamp) +
                              "; anything added since may be missing")
    if sem_error:
        out["degraded_ru"] = "семантический поиск недоступен, подбор шёл только по словам: " + sem_error
        out["degraded_en"] = "semantic search unavailable, matching fell back to words: " + sem_error
    return out

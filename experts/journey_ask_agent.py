# description: Позвать агента аккаунта и вернуть его ответ. Показательный вызов для витрины: страница зовёт эксперта на устройстве, эксперт зовёт агента. Цепочку и время возвращает целиком.
# Эксперт платформы: journey_ask_agent (global, cspl=fython)
#
# ЗАЧЕМ. Витрина продукта показывает силу нажатием, а не рассказом. Самый
# сильный из показов — цепочка через три слоя: страница в окне ОС → эксперт на
# устройстве покупателя → агент аккаунта. Каждый слой настоящий, и время каждого
# возвращается отдельно: без этого «быстро» и «дорого» остаются словами.
#
# ГДЕ БЕРЁТСЯ ТОКЕН. Листенер кладёт его в окружение процесса эксперта (канон
# H30). Четыре источника по порядку, как велит канон установщика: окружение,
# файл, launchctl не трогаем (эксперт не служба), конфиг листенера. Токен нигде
# не печатается и в ответ не попадает.
#
# ЦЕНА ВЫЗОВА. Запуск агента тратит план аккаунта, и это возвращается человеку
# числом: сколько заняло и сколько слоёв прошло. Не запрет, а видимость.

def journey_ask_agent(agent_id: str = "", question: str = "") -> str:
    import json, os, time, urllib.request

    def result(status, message, **extra):
        payload = {"status": status, "message": message}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)

    def token():
        t = (os.environ.get("EXTELLA_API_TOKEN") or "").strip()
        if len(t) >= 8:
            return t
        for path in (os.path.expanduser("~/.extella/api_token.txt"),
                     os.path.expanduser("~/.extella/os_token.txt")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    t = f.read().strip()
                if len(t) >= 8:
                    return t
            except Exception:
                pass
        try:
            with open(os.path.expanduser("~/extella_wizard/app/config.json"),
                      "r", encoding="utf-8") as f:
                d = json.loads(f.read())
            for k in ("auth_token", "token", "AUTH_TOKEN", "extella_token"):
                if d.get(k):
                    return str(d[k])
        except Exception:
            pass
        return ""

    if not agent_id or agent_id.startswith("{{"):
        return result("error", "нужен agent_id — какого агента звать")
    if not question or question.startswith("{{"):
        return result("error", "нужен question — что у него спросить")

    tok = token()
    if not tok:
        return result("error", "на этом устройстве нет доступа к Extella: "
                               "открой приложение Extella один раз, и доступ появится")

    body = json.dumps({"agent_id": agent_id, "input": question}).encode()
    req = urllib.request.Request(
        "https://api.extella.ai/api/agent/run", data=body,
        headers={"Content-Type": "application/json", "X-Auth-Token": tok,
                 "X-Profile-Id": "default", "X-Agent-Id": agent_id})
    started = time.time()
    try:
        raw = urllib.request.urlopen(req, timeout=170).read()
    except Exception as e:
        # Причина, а не факт: по «не ответил» разбирать нечего.
        return result("error", "агент не ответил: " + str(e)[:160])
    spent = round(time.time() - started, 1)

    try:
        data = json.loads(raw)
    except Exception:
        return result("error", "агент вернул не JSON")

    # Ответ агента приходит списком частей: рассуждение и сам текст. Берём
    # текст; рассуждение в витрину не тащим — оно длинное и не про то.
    answer = ""
    for part in (data.get("output") or []):
        if part.get("type") == "reasoning":
            continue
        for piece in (part.get("content") or []):
            t = piece.get("text") or piece.get("output_text") or ""
            if t:
                answer += t
    answer = answer.strip()
    if not answer:
        return result("error", "агент ответил без текста (состояние: "
                      + str(data.get("status")) + ")", seconds=spent)

    return result("success", "агент ответил",
                  answer=answer[:1200], seconds=spent,
                  agent=agent_id, chain="страница → эксперт → агент")

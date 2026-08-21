# description: Отнести текст к одной из категорий локальной моделью на устройстве: быстро, бесплатно, текст не уходит в облако. Для потока однотипных задач — тип обращения, тональность, рубрика.
# Эксперт платформы: local_model_classify (global, cspl=fython)
#
# ЗАЧЕМ ЭКСПЕРТ, А НЕ MCP. Локальную модель можно отдать агенту двумя путями.
# MCP-сервер (tools/local_model_mcp.py) собран и работает, но дойдёт ли его
# инструмент до агента в чате — не проверено ни разу. Эксперт — родной путь
# платформы: агент зовёт его так же, как любой другой, и это проверяется
# запуском. Поэтому канон один: сначала эксперт, MCP — когда доказан.
#
# ГДЕ ЗАПУСКАЕТСЯ. LM Studio живёт на 127.0.0.1 КОНКРЕТНОЙ машины. Таргет по
# умолчанию — VPS, там LM Studio нет; поэтому отказ называет причину и что
# сделать, а не молчит. UUID устройства в коде не хранится: его выбирают при
# запуске.
#
# ЗАМЕР 20.08.2026 (MacBook 32 ГБ, gemma-2-9b): «не приходит акт сверки за
# июль» → «поддержка» за 1.6 секунды. Та же задача на рассуждающей qwen3.8-27b —
# 47 секунд и пустой ответ на коротком потолке: рассуждающая модель кладёт всё
# в размышления. Поэтому модель выбирается не первой попавшейся.

def local_model_classify(text="", categories="", model="") -> str:
    import json, urllib.request

    def отказ(с):
        return json.dumps({"status": "error", "message": с}, ensure_ascii=False)

    if not text or text.startswith("{{"):
        return отказ("нужен text — текст, который надо отнести к категории")
    if not categories or categories.startswith("{{"):
        return отказ("нужен categories — категории через запятую, например: продажи, поддержка, бухгалтерия")
    список = [к.strip() for к in categories.replace(";", ",").split(",") if к.strip()]
    if len(список) < 2:
        return отказ("нужно хотя бы две категории через запятую")

    база = "http://127.0.0.1:1234/v1"
    try:
        сырое = json.loads(urllib.request.urlopen(база + "/models", timeout=8).read())
    except Exception as e:
        return отказ("на этой машине не отвечает LM Studio на 127.0.0.1:1234. "
                     "Выбери в запуске своё устройство, где запущена LM Studio, "
                     "и включи в ней Local Server. Причина: " + str(e)[:100])

    имена = [str(m.get("id", "")) for m in сырое.get("data", []) if m.get("id")]
    if not имена:
        return отказ("в LM Studio не загружена ни одна модель")
    выбранная = model if model and not model.startswith("{{") else ""
    if not выбранная:
        # Порядок в списке НЕ постоянен: замер 21.08.2026 — первой стала модель
        # для кода вместо замеренной быстрой, хотя список тот же. Поэтому не
        # «первая подходящая», а список предпочтений с падением вниз.
        # Предпочтение, а не гарантия: чего нет на машине, то пропускается.
        годные = [и for и in имена
                  if "embed" not in и.lower() and "reasoning" not in и.lower()]
        предпочтение = ("gemma-2-9b", "ministral-3-3b", "gemma", "ministral")
        выбранная = ""
        for метка in предпочтение:
            совпало = [и for и in годные if метка in и.lower()]
            if совпало:
                выбранная = совпало[0]
                break
        выбранная = выбранная or (годные or имена)[0]

    тело = json.dumps({
        "model": выбранная,
        "messages": [{"role": "user", "content":
                      "Отнеси текст ровно к одной категории из списка и ответь ТОЛЬКО "
                      "названием категории, без пояснений.\nКатегории: "
                      + ", ".join(список) + "\nТекст: " + text}],
        "max_tokens": 40, "temperature": 0,
    }).encode()
    try:
        зпр = urllib.request.Request(база + "/chat/completions", data=тело,
                                     headers={"Content-Type": "application/json"})
        готово = json.loads(urllib.request.urlopen(зпр, timeout=120).read())
    except Exception as e:
        return отказ("локальная модель не ответила: " + str(e)[:120])

    выбор = (готово.get("choices") or [{}])[0]
    ответ = str((выбор.get("message") or {}).get("content") or "").strip()
    if not ответ:
        return отказ("модель не дала ответа (finish_reason="
                     + str(выбор.get("finish_reason")) + "). Похоже, загружена "
                     "рассуждающая модель: для потока нужна быстрая, например gemma-2-9b")
    # Приводим к заданному списку: модель любит падеж, точку и заглавную букву.
    низ = ответ.strip().strip(".!\"'").lower()
    итог = ответ
    for к in список:
        if к.lower() == низ or к.lower() in низ:
            итог = к
            break
    return json.dumps({"status": "success", "category": итог,
                       "model": выбранная, "raw": ответ[:200]}, ensure_ascii=False)

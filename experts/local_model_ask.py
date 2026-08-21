# description: Задать короткий вопрос локальной модели на устройстве: бесплатно, ответ за секунды, текст не уходит в облако. Модель слабее платформенной — для рассуждений и длинных ответов отвечай сам, а этот эксперт зови для потока.
# Эксперт платформы: local_model_ask (global, cspl=fython)
#
# Пара к local_model_classify — там же и причины: почему эксперт, а не MCP, и
# почему модель выбирается не первой попавшейся. Обвязка HTTP повторена здесь
# намеренно: эксперт исполняется на платформе и импортировать соседа не может.
# Правка одного обязана повторяться в другом — их два, и оба короткие.
#
# ПОТОЛОК ОТВЕТА. Длинный ответ означает, что задачу выбрали неправильно: её
# надо было решать наверху, на сильной модели. Поэтому потолок жёсткий.

def local_model_ask(prompt="", max_tokens="", model="") -> str:
    import json, urllib.request

    def отказ(с):
        return json.dumps({"status": "error", "message": с}, ensure_ascii=False)

    if not prompt or prompt.startswith("{{"):
        return отказ("нужен prompt — вопрос или задание локальной модели")
    try:
        потолок = int(max_tokens) if max_tokens and not str(max_tokens).startswith("{{") else 200
    except Exception:
        потолок = 200
    потолок = max(1, min(потолок, 400))

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

    тело = json.dumps({"model": выбранная,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": потолок, "temperature": 0}).encode()
    try:
        зпр = urllib.request.Request(база + "/chat/completions", data=тело,
                                     headers={"Content-Type": "application/json"})
        готово = json.loads(urllib.request.urlopen(зпр, timeout=180).read())
    except Exception as e:
        return отказ("локальная модель не ответила: " + str(e)[:120])

    выбор = (готово.get("choices") or [{}])[0]
    ответ = str((выбор.get("message") or {}).get("content") or "").strip()
    if not ответ:
        return отказ("модель не дала ответа (finish_reason="
                     + str(выбор.get("finish_reason")) + "). Похоже, загружена "
                     "рассуждающая модель: для потока нужна быстрая, например gemma-2-9b")
    return json.dumps({"status": "success", "answer": ответ[:4000],
                       "model": выбранная}, ensure_ascii=False)

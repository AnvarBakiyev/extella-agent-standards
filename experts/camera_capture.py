# description: Камера для окна приложения: устройство берёт ОДИН кадр и возвращает жест, кадр не покидает машину
def camera_capture(
    mode: str = "gesture",
    device: str = "",
    model_path: str = "",
    labels: str = "rock,paper,scissors",
    keep_file: bool = False,
    max_side: int = 256,
):
    """Берёт ОДИН кадр камеры НА УСТРОЙСТВЕ и отдаёт жест в окно приложения.

    Зачем существует. Окно приложения живёт в песочнице без своего
    происхождения и без разрешения на камеру, поэтому `getUserMedia` в нём
    отклоняется — снять кадр со страницы нельзя в принципе. Замер 08.09.2026:
    игра Gesture Arena в окне Extella не получает браузерную камеру, её же
    загрузчик пишет «This Mac desktop build does not grant browser camera
    access», и автор был вынужден делать отдельный нативный модуль на каждую
    ОС. Это тот же тупик, что с микрофоном (mic_record) — и решается так же:
    у окна есть законный путь наружу, попросить устройство.

    Для «камень-ножницы-бумага» живое видео не нужно: нужен ОДИН кадр в момент
    хода. Поэтому вызов синхронный, как mic_record — окно жмёт «раунд» и ждёт.

    Приватность. По умолчанию (`mode="gesture"`) наружу уходит только метка
    жеста — сам кадр распознаётся на устройстве и удаляется, интернета не
    видит. `mode="frame"` вернёт уменьшенный кадр data-URI (для превью в окне) —
    это осознанный выбор: тогда кадр покидает устройство, поэтому не по умолчанию.

    Параметры:
      mode       — "gesture" вернуть распознанный жест (кадр остаётся на машине);
                   "frame" вернуть уменьшенный кадр data-URI для показа в окне.
      device     — имя или номер входа камеры, пусто — камера по умолчанию.
      model_path — ONNX-модель распознавания жеста на устройстве; пусто —
                   ищем extella_wizard/models/gesture.onnx, иначе честно говорим,
                   что распознаватель не подключён (кадр всё равно снят).
      labels     — метки классов модели по порядку выходов.
      keep_file  — не удалять кадр (по умолчанию удаляется).
      max_side   — для mode="frame": длинная сторона превью в пикселях.

    Возвращает готовое значение сразу, без внутренней задачи: окно ждёт ответа
    синхронно, как в mic_record.
    """
    import base64
    import os
    import subprocess
    import sys
    import tempfile
    import time

    начало = time.time()
    кадр = os.path.join(tempfile.gettempdir(), f"extella_cam_{int(начало*1000)}.jpg")

    def прибрать():
        if not keep_file:
            try:
                os.remove(кадр)
            except OSError:
                pass

    # ── снимок ОДНОГО кадра ──────────────────────────────────────────────────
    # Тот же путь, что запасной у микрофона: ffmpeg со штатным входом каждой ОС.
    вход = {"darwin": ("avfoundation", device or "0"),
            "win32":  ("dshow", f"video={device}" if device else "video=default"),
            }.get(sys.platform, ("v4l2", device or "/dev/video0"))
    снят = False
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", вход[0], "-i", вход[1],
             "-frames:v", "1", "-q:v", "3", кадр],
            capture_output=True, timeout=30, check=True)
        снят = os.path.exists(кадр) and os.path.getsize(кадр) > 1000
    except FileNotFoundError:
        return {"ok": False, "почему": "нет ffmpeg на устройстве",
                "что делать": "Поставить ffmpeg — он открывает камеру там, где "
                              "окно не может. Другой захват (opencv) добавим, если "
                              "ffmpeg недоступен."}
    except subprocess.CalledProcessError as беда:
        хвост = (беда.stderr or b"").decode(errors="replace")[-200:]
        return {"ok": False, "почему": "камера не открылась на устройстве",
                "подробности": хвост,
                "что делать": "Проверить, что устройству разрешён доступ к камере "
                              "в настройках системы: службе, которая исполняет "
                              "задания Extella, разрешение выдаётся отдельно и "
                              "молча не запрашивается (как с микрофоном)."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "почему": "камера не ответила за 30 с",
                "что делать": "Проверить, не занята ли камера другой программой."}

    if not снят:
        прибрать()
        return {"ok": False, "почему": "кадр вышел пустым",
                "что делать": "Проверить выбранный вход камеры."}

    # ── mode=frame: уменьшенный кадр наружу (осознанно, кадр покидает машину) ──
    if mode == "frame":
        data = _уменьшить(кадр, max_side)
        прибрать()
        return {"ok": True, "кадр_data_uri": data, "заняло_сек": round(time.time() - начало, 2),
                "внимание": "кадр покинул устройство по вашему запросу mode='frame'"}

    # ── mode=gesture: распознаём НА УСТРОЙСТВЕ, наружу только метка ────────────
    путь_модели = model_path or os.path.expanduser(
        "~/extella_wizard/models/gesture.onnx")
    if not os.path.exists(путь_модели):
        прибрать()
        return {"ok": False, "почему": "распознаватель жеста не подключён",
                "что делать": "Положить ONNX-модель игры в "
                              "~/extella_wizard/models/gesture.onnx или передать "
                              "model_path. Кадр снят успешно — путь до камеры "
                              "device-side доказан; осталось подключить ту же "
                              "модель, что крутится в браузерной версии.",
                "кадр_снят": True, "заняло_сек": round(time.time() - начало, 2)}
    try:
        import onnxruntime  # noqa: F401
    except Exception:                                             # noqa: BLE001
        прибрать()
        return {"ok": False, "почему": "onnxruntime не установлен на устройстве",
                "что делать": "Поставить onnxruntime — распознавание идёт на "
                              "устройстве, как в игре, но вне песочницы.",
                "кадр_снят": True}
    try:
        жест, уверенность = _распознать(кадр, путь_модели,
                                        [м.strip() for м in labels.split(",") if м.strip()])
    except Exception as беда:                                     # noqa: BLE001
        прибрать()
        return {"ok": False, "почему": "распознавание не справилось",
                "подробности": str(беда)[:200], "кадр_снят": True}
    прибрать()
    return {"ok": True, "жест": жест, "уверенность": round(float(уверенность), 3),
            "заняло_сек": round(time.time() - начало, 2),
            "приватность": "кадр распознан на устройстве и удалён, наружу не уходил"}


def _уменьшить(путь, max_side):
    import base64
    try:
        from PIL import Image
        import io
        im = Image.open(путь)
        im.thumbnail((max_side, max_side))
        буфер = io.BytesIO()
        im.save(буфер, format="JPEG", quality=70)
        сырьё = буфер.getvalue()
    except Exception:                                             # noqa: BLE001
        сырьё = open(путь, "rb").read()          # без PIL — как есть
    return "data:image/jpeg;base64," + base64.b64encode(сырьё).decode()


def _распознать(путь, модель, метки):
    """Инференс на устройстве. Форму входа читаем из самой модели, а не гадаем."""
    import numpy as np
    import onnxruntime
    from PIL import Image
    сессия = onnxruntime.InferenceSession(модель, providers=["CPUExecutionProvider"])
    вход = сессия.get_inputs()[0]
    _, _, h, w = (вход.shape if len(вход.shape) == 4 else (1, 3, 224, 224))
    h = int(h) if isinstance(h, int) else 224
    w = int(w) if isinstance(w, int) else 224
    im = Image.open(путь).convert("RGB").resize((w, h))
    x = (np.asarray(im, dtype="float32") / 255.0).transpose(2, 0, 1)[None]
    выход = сессия.run(None, {вход.name: x})[0][0]
    выход = np.asarray(выход, dtype="float32").ravel()
    i = int(выход.argmax())
    метка = метки[i] if i < len(метки) else f"class_{i}"
    экс = np.exp(выход - выход.max())
    уверенность = float((экс / экс.sum())[i])
    return метка, уверенность


def _selftest():
    """Проверяем структуру без камеры: отказ обязан быть честным и не падать стеком."""
    провалы = []
    o = camera_capture(mode="gesture", device="нет-такой-камеры-12345")
    if o.get("ok"):
        провалы.append("несуществующая камера не должна давать ok")
    if not o.get("почему"):
        провалы.append("отказ обязан называть причину")
    print("camera_capture selftest:", "провалы — " + "; ".join(провалы) if провалы
          else "пройден (честный отказ без камеры)")
    return 1 if провалы else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)

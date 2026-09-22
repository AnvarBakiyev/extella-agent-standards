# expert: my_app_where
# description: Диспетчер устройства приложения: сообщает, на каком компьютере исполнился. Параметры: нет.

def my_app_where() -> str:
    import json
    import os
    import socket

    # Платформа не говорит странице, где исполнился код (H106). Первый вызов страницы идёт
    # сюда без targets; мост берёт pageRoute.targetId и закрепляет за ним все следующие вызовы.
    # В облачном контейнере файла нет — честный отказ вместо чужого устройства.
    try:
        path = os.path.join(os.path.expanduser("~"), ".extella", "device.txt")
        with open(path, encoding="utf-8") as f:
            device = f.read().strip()
    except OSError:
        device = ""
    if len(device) != 36:
        return json.dumps({"status": "error",
                           "message": "Эксперт исполнился не на компьютере с Extella — устройство не найдено."},
                          ensure_ascii=False)
    return json.dumps({"status": "success", "pageRoute": {"targetId": device},
                       "device": device, "host": socket.gethostname()}, ensure_ascii=False)

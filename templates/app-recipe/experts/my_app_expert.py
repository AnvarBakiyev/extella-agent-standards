# expert: my_app_expert
# description: Пример эксперта приложения: выполняет задачу и сообщает, на каком компьютере исполнился. Параметры: task, scenario.

def my_app_expert(task: str = "", scenario: str = "base") -> str:
    import json
    import os
    import socket

    # Платформа не говорит странице, где исполнился код, — это сообщает сам эксперт.
    # Мост запоминает "device" и закрепляет за ним все следующие вызовы (H106).
    # В облачном контейнере файла нет: device пустой, и страница не закрепляется.
    def device() -> str:
        try:
            path = os.path.join(os.path.expanduser("~"), ".extella", "device.txt")
            with open(path, encoding="utf-8") as f:
                value = f.read().strip()
            return value if len(value) == 36 else ""
        except OSError:
            return ""

    # {{placeholder}} подставляется только для переданных параметров — проверяем явно.
    if not task or str(task).startswith("{{"):
        return json.dumps({"status": "error", "message": "Не передана задача."}, ensure_ascii=False)
    return json.dumps({
        "status": "success",
        "text": f"Задача: {task}\nСценарий: {scenario}\nВыполнено на компьютере: {socket.gethostname()}",
        "device": device(),
    }, ensure_ascii=False)

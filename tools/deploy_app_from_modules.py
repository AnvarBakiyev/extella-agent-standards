#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Предрелиз приложения из модулей: листинг с прикреплённым агентом, приёмка чтением.

ЗАЧЕМ. Обычная выкладка страниц (`deploy_page_product.py`) написана для окон без агента, а
приложение из модулей зовёт эксперты через своего агента. Агент прикрепляется к листингу
только при его создании (`publish-stream` с `source_id`, `source_type=agent`,
`attach_agent=1`); добавить агента потом нельзя — страница ответит
`403 this app has no deployed agent` (замер 25.08.2026). Поэтому у приложения из модулей
свой путь в магазин, и он останавливается перед публикацией: кнопку «Publish» жмёт человек.

Покупка себе делается отдельным флагом: после неё листинг больше нельзя удалить.

    python3 tools/deploy_app_from_modules.py apps/<slug>                # план, ничего не пишет
    python3 tools/deploy_app_from_modules.py apps/<slug> --выполнить    # предрелиз + приёмка
    python3 tools/deploy_app_from_modules.py apps/<slug> --выполнить --купить-себе
    python3 tools/deploy_app_from_modules.py --selftest

Коды выхода: 0 — сделано (или показан план), 1 — отказ с названной причиной, 2 — каталог не прочитан.
"""
import json
import pathlib
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
import platform_client as пк  # noqa: E402


def поля_публикации(карточка: dict, план: dict) -> dict:
    теги = карточка.get("теги") or []
    if not теги:
        raise пк.Отказ("в listing.json нет тегов — publish-stream отвечает 400 без тегов")
    права = карточка.get("права") or []
    if "expert.run" not in права:
        raise пк.Отказ("в правах нет expert.run — окно не сможет позвать эксперт")
    agent_id = str(план.get("agent_id") or "")
    if not agent_id.startswith("agent_") or agent_id == "agent_extella_default":
        raise пк.Отказ("agent_id приложения должен быть точным id вида agent_… и не основным агентом")
    return {
        "version": str(карточка.get("версия") or "0.1.0"),
        "price_credits": str(карточка.get("цена") or 0),
        "app_scopes": json.dumps(права),
        "name": str(карточка.get("name") or "").strip(),
        "description": str(карточка.get("описание") or "").strip(),
        "source_id": agent_id,
        "source_type": "agent",
        "attach_agent": "1",
        "tags": json.dumps(теги, ensure_ascii=False),
    }


def мои_листинги(запрос) -> list:
    код, сырое = запрос(пк.ОС, "/api/my-listings")
    if код != 200:
        raise пк.Отказ(f"список листингов ответил {код}")
    return пк.как_json(сырое, "список листингов").get("listings", [])


def приёмка(listing_id: str, план: dict, карточка: dict, запрос, эксперты: list) -> list:
    """Читаем обратно то, что якобы создали. «Успешно» от платформы фактом не является."""
    беды = []
    сделан = next((x for x in мои_листинги(запрос) if x.get("id") == listing_id), None)
    if сделан is None:
        return ["созданный листинг не читается обратно"]
    if сделан.get("published") is True:
        беды.append("листинг оказался опубликованным — это не предрелиз")
    версия = (сделан.get("versions") or [{}])[-1]
    права = версия.get("app_scopes") or []
    if isinstance(права, str):
        права = json.loads(права)
    if set(права) != set(карточка.get("права") or []):
        беды.append(f"права {права} вместо {карточка.get('права')}")
    if str(версия.get("source_id") or "") != план["agent_id"]:
        беды.append(f"агент версии {версия.get('source_id')} вместо {план['agent_id']}")
    заголовки = {"X-Auth-Token": пк.токен(), "X-Profile-Id": "default", "X-Agent-Id": план["agent_id"]}
    for имя in эксперты:
        код, сырое = запрос(пк.ЯДРО, "/api/expert/get", тело={"name": имя, "global": True}, заголовки=заголовки)
        if код != 200 or not (пк.как_json(сырое, имя).get("expert_code") or "").strip():
            беды.append(f"эксперт {имя} не читается из скоупа агента приложения")
    код, страница = запрос(пк.ОС, f"/app-page/{listing_id}/")
    if код != 200:
        беды.append(f"страница отдаётся с кодом {код}")
    else:
        if "{" + "{app_token}}" in страница:
            беды.append("плейсхолдер app_token не подставлен")
        if пк.токен()[:16] in страница:
            беды.append("в отданной странице виден токен аккаунта")
        if "xtl_help" not in страница:
            беды.append("в отданной странице нет «? Как это работает»")
    return беды


def выполнить(папка: pathlib.Path, запрос=None, купить: bool = False, план_только: bool = True) -> dict:
    запрос = запрос or пк.запрос
    карточка = json.loads((папка / "listing.json").read_text(encoding="utf-8"))
    план = json.loads((папка / "app.json").read_text(encoding="utf-8"))
    поля = поля_публикации(карточка, план)
    страница, иконка = папка / "index.html", папка / str(карточка.get("иконка") or "icon.png")
    for п in (страница, иконка):
        if not п.exists():
            raise пк.Отказ(f"нет файла {п.name} — собери: python3 tools/build_app_from_modules.py {папка}")
    пров = папка / "provisioning.json"
    if not пров.exists() or not json.loads(пров.read_text(encoding="utf-8")).get("all_verified"):
        raise пк.Отказ("нет подтверждённого provisioning.json — сначала python3 tools/provision_modules.py")
    эксперты = [с["expert"] for с in json.loads(пров.read_text(encoding="utf-8"))["experts"]]
    итог = {"поля": поля, "страница": страница.stat().st_size, "иконка": иконка.stat().st_size,
            "эксперты": эксперты, "listing_id": карточка.get("listing_id"), "version_id": карточка.get("version_id")}
    if план_только:
        return итог
    if карточка.get("listing_id"):
        raise пк.Отказ(f"листинг уже создан: {карточка['listing_id']}. Новая версия в существующий листинг — "
                       "отдельное решение: агент к ней не прикрепляется заново, а покупатели видят версию сразу")
    код, сырое = запрос(пк.ОС, "/api/publish-stream", поля=поля, файлы={"page": страница, "icon": иконка})
    готово = пк.из_потока(сырое, "создание предрелизного листинга", код)
    карточка["listing_id"] = готово.get("listing_id")
    карточка["version_id"] = готово.get("version_id")
    карточка["состояние"] = "предрелиз"
    (папка / "listing.json").write_text(json.dumps(карточка, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    итог.update({"listing_id": карточка["listing_id"], "version_id": карточка["version_id"]})
    итог["беды"] = приёмка(карточка["listing_id"], план, карточка, запрос, эксперты)
    if купить and карточка.get("version_id"):
        код, сырое = запрос(пк.ОС, f"/api/purchase-stream/{карточка['version_id']}",
                            тело={"deploy_mode": "existing", "target_agent_id": план["agent_id"]})
        try:
            пк.из_потока(сырое, "покупка себе", код)
            итог["куплено"] = True
        except пк.Отказ as о:
            итог["куплено"] = False
            итог["беды"].append(f"покупка себе: {о}")
    return итог


def selftest() -> int:
    import tempfile
    ошибки = []
    журнал = []

    def поддельный(база, путь, *, тело=None, поля=None, файлы=None, заголовки=None, таймаут=0, метод=None):
        журнал.append((путь, поля, тело))
        if путь == "/api/publish-stream":
            if not поля.get("attach_agent") == "1" or поля.get("source_type") != "agent":
                return 400, "agent not attached"
            return 200, 'data: {"type":"done","listing_id":"lst_1","version_id":"ver_1"}\n'
        if путь == "/api/my-listings":
            return 200, json.dumps({"listings": [{"id": "lst_1", "published": False,
                                                  "versions": [{"app_scopes": ["expert.run", "device.run"],
                                                                "source_id": "agent_app"}]}]})
        if путь == "/api/expert/get":
            return 200, json.dumps({"expert_code": "def x(): pass"})
        if путь.startswith("/app-page/"):
            return 200, "<html>xtl_help app_token=abc</html>"
        if путь.startswith("/api/purchase-stream/"):
            return 200, 'data: {"type":"done"}\n'
        return 500, "?"

    пк.токен = lambda: "проба-токен-проба-токен"
    with tempfile.TemporaryDirectory() as tmp:
        папка = pathlib.Path(tmp)
        (папка / "index.html").write_text("<html>{{app_token}}</html>")
        (папка / "icon.png").write_bytes(b"\x89PNG" + b"0" * 600)
        (папка / "app.json").write_text(json.dumps({"agent_id": "agent_app"}))
        (папка / "listing.json").write_text(json.dumps({"name": "Проба", "описание": "о" * 90, "теги": ["a", "b"],
                                                        "права": ["expert.run", "device.run"], "версия": "0.1.0"}))
        (папка / "provisioning.json").write_text(json.dumps({"all_verified": True, "experts": [{"expert": "toolkit_probe"}]}))
        план = выполнить(папка, поддельный, план_только=True)
        if план["поля"]["attach_agent"] == "1" and план["поля"]["source_id"] == "agent_app" and not журнал:
            print("  ✓ план: агент прикрепляется при создании, на платформу ничего не ушло")
        else:
            ошибки.append("план неверен или что-то записал")
        итог = выполнить(папка, поддельный, план_только=False)
        if итог["listing_id"] == "lst_1" and not итог["беды"] \
                and json.loads((папка / "listing.json").read_text())["listing_id"] == "lst_1":
            print("  ✓ предрелиз создан, id записаны в listing.json, приёмка чтением прошла")
        else:
            ошибки.append(f"выполнение: {итог}")
        try:
            выполнить(папка, поддельный, план_только=False)
            ошибки.append("повтор создал бы двойник листинга — НЕ пойман")
        except пк.Отказ:
            print("  ✓ повтор с существующим listing_id — отказ, двойник не создаётся")
        (папка / "provisioning.json").write_text(json.dumps({"all_verified": False, "experts": []}))
        try:
            выполнить(папка, поддельный, план_только=True)
            ошибки.append("неподтверждённый провижининг НЕ пойман")
        except пк.Отказ:
            print("  ✓ без подтверждённого провижининга — отказ")
    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main(аргументы) -> int:
    if "--selftest" in аргументы:
        return selftest()
    пути = [а for а in аргументы if not а.startswith("--")]
    if not пути:
        print(__doc__)
        return 2
    папка = pathlib.Path(пути[0]).expanduser()
    if not (папка / "listing.json").exists():
        print(f"ОТКАЗ: нет {папка / 'listing.json'}")
        return 2
    try:
        итог = выполнить(папка, купить="--купить-себе" in аргументы, план_только="--выполнить" not in аргументы)
    except пк.Отказ as о:
        print(f"ОТКАЗ: {о}")
        return 1
    п = итог["поля"]
    print(f"листинг      : «{п['name']}» версия {п['version']}, права {p_json(п['app_scopes'])}, теги {p_json(п['tags'])}")
    print(f"агент        : {п['source_id']} (прикрепляется при создании)")
    print(f"страница     : {итог['страница']} байт · иконка {итог['иконка']} байт · эксперты: {', '.join(итог['эксперты'])}")
    if "беды" not in итог:
        print("это план. Повтори с --выполнить" if not итог.get("listing_id")
              else f"листинг уже есть: {итог['listing_id']}")
        return 0
    print(f"предрелиз    : listing_id {итог['listing_id']}, version_id {итог['version_id']}")
    if итог.get("куплено") is not None:
        print("покупка себе : " + ("сделана" if итог["куплено"] else "НЕ прошла"))
    if итог["беды"]:
        print("ПРИЁМКА НЕ ПРОШЛА:\n  " + "\n  ".join(итог["беды"]))
        return 1
    print("приёмка      : предрелиз подтверждён чтением; публикация — кнопка человека")
    return 0


def p_json(т: str):
    try:
        return json.loads(т)
    except Exception:
        return т


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

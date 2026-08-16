#!/usr/bin/env python3
"""Отключить звонки наружу у чужого приложения — чтобы «локально» было правдой.

ЗАЧЕМ. Карточка в магазине обещает «всё локально, без интернета и аккаунта».
Чужие сборки почти всегда тянут при открытии постороннее: счётчики посещений,
шрифты с чужих серверов, предварительные соединения. Пока это внутри, обещание
на карточке — неправда, а у человека тихо утекает факт использования.

Что вырезается (только явные загрузки, ничего «на всякий случай»):
  * <link> на чужой адрес, который ЗАГРУЖАЕТ: preload, preconnect, stylesheet,
    dns-prefetch, prefetch, modulepreload;
  * <script src="чужой адрес">;
  * блок скрипта, вся работа которого — подсунуть чужой скрипт (счётчики);
  * чужие адреса в списке адресов ресурсов, если рядом в списке есть местный
    путь (обычный приём «сначала чужой сервер, потом свой»).

Что НЕ трогаем: canonical и подобные метки — они ничего не загружают. Всё
остальное подозрительное только показываем: молча менять чужой код нельзя.

    python3 tools/cut_outbound.py ~/extella-plugins/приложение/index.html
    python3 tools/cut_outbound.py <страница> --показать     # только посмотреть
    python3 tools/cut_outbound.py <страница> --снять        # вернуть как было
    python3 tools/cut_outbound.py --selftest

Рядом остаётся копия «.до_отключения»: если приложение обновится, будет с чем
сверить. Коды выхода: 0 — сделано, 1 — отказ с причиной.
"""

import argparse
import pathlib
import re
import shutil
import sys

СВОИ = ("localhost", "127.0.0.1", "0.0.0.0")
ЗАГРУЖАЮЩИЕ = ("preload", "preconnect", "stylesheet", "dns-prefetch",
               "prefetch", "modulepreload")
СЛЕД = ".до_отключения"
МЕТКА = "<!-- extella: убрана внешняя загрузка"


def чужой(адрес: str) -> bool:
    return bool(re.match(r"https?://", адрес)) and not any(
        f"//{с}" in адрес for с in СВОИ)


def _рел(тег: str) -> str:
    м = re.search(r'rel\s*=\s*["\']?([^"\'\s>]+)', тег, re.I)
    return (м.group(1) if м else "").lower()


def _адрес(тег: str) -> str:
    м = re.search(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', тег, re.I)
    return м.group(1) if м else ""


def разбор(текст: str) -> tuple[str, list[str], list[str]]:
    """Вернуть (новый текст, что вырезано, что осталось на глаз человека)."""
    вырезано: list[str] = []
    осталось: list[str] = []

    # 1) Блоки скриптов, которые подсовывают чужой скрипт (счётчики)
    def блок(м):
        тело = м.group(0)
        адреса = [а for а in re.findall(r'["\'](https?://[^"\']+)["\']', тело)
                  if чужой(а)]
        грузит = "createElement" in тело and "script" in тело.lower()
        if адреса and грузит:
            вырезано.append(f"счётчик/подгрузка: {адреса[0][:88]}")
            return f"{МЕТКА}: {адреса[0][:88]} -->"
        return тело

    текст = re.sub(r"<script(?![^>]*\bsrc\s*=)[^>]*>.*?</script>", блок,
                   текст, flags=re.I | re.S)

    # 2) <script src="чужой">
    def скрипт(м):
        тег = м.group(0)
        а = _адрес(тег)
        if чужой(а):
            вырезано.append(f"чужой скрипт: {а[:88]}")
            return f"{МЕТКА}: {а[:88]} -->"
        return тег

    текст = re.sub(r'<script\b[^>]*\bsrc\s*=[^>]*>\s*</script>|<script\b[^>]*\bsrc\s*=[^>]*/?>',
                   скрипт, текст, flags=re.I)

    # 3) <link>, который загружает
    def ссылка(м):
        тег = м.group(0)
        а = _адрес(тег)
        if not чужой(а):
            return тег
        рел = _рел(тег)
        if рел in ЗАГРУЖАЮЩИЕ:
            вырезано.append(f"{рел}: {а[:88]}")
            return f"{МЕТКА}: {рел} {а[:70]} -->"
        осталось.append(f"{рел or 'link'} (не загружает, оставлен): {а[:70]}")
        return тег

    текст = re.sub(r"<link\b[^>]*/?>", ссылка, текст, flags=re.I)

    # 4) Чужие адреса в списке адресов ресурсов, где рядом есть местный путь
    def список(м):
        тело = м.group(0)
        строки = re.findall(r'["\']([^"\']*)["\']', тело)
        чужие = [с for с in строки if чужой(с)]
        местные = [с for с in строки if с.startswith(("/", "./", "../"))]
        if not чужие or not местные:
            return тело
        нов = тело
        for с in чужие:
            нов = re.sub(r'["\']' + re.escape(с) + r'["\']\s*,?\s*', "", нов)
            вырезано.append(f"адрес ресурсов: {с[:88]}")
        return нов

    текст = re.sub(r"\[\s*(?:[\"'][^\"']*[\"']\s*,?\s*){2,}\]", список, текст)

    # 5) Что осталось внешнего — показываем, но не трогаем.
    # Свои пометки об уже вырезанном из просмотра убираем: адрес в комментарии
    # ничего не загружает, и показывать его второй раз как «остаток» — врать.
    без_меток = re.sub(re.escape(МЕТКА) + r".*?-->", "", текст, flags=re.S)
    for а in set(re.findall(r'["\'(](https?://[^"\'\s)<>]+)', без_меток)):
        if чужой(а):
            осталось.append(f"адрес в коде (не тронут): {а[:80]}")

    return текст, вырезано, осталось


def _местный_шрифт(папка: pathlib.Path, адрес: str) -> pathlib.Path | None:
    """Найти в папке приложения местную замену шрифту с чужого сервера.

    Сначала точное имя файла. Если его нет — берём тот же шрифт другого
    начертания (Assistant-SemiBold → Assistant-Regular): начертание браузер
    дорисует сам, а вот поход в интернет — уже нарушенное обещание.
    """
    имя = адрес.split("/")[-1].split("?")[0]
    точное = [п for п in папка.rglob(имя) if п.is_file()]
    if точное:
        return точное[0]
    семья = re.split(r"[-_.]", имя)[0]
    if len(семья) < 3:
        return None
    похожие = sorted(п for п in папка.rglob(f"{семья}*")
                     if п.is_file() and п.suffix.lower() in (".woff2", ".woff", ".ttf", ".otf"))
    return похожие[0] if похожие else None


def починить_стили(папка: pathlib.Path) -> tuple[list[str], list[str]]:
    """Увести шрифты и картинки в стилях с чужих серверов на местные файлы.

    ЗАЧЕМ ОТДЕЛЬНО ОТ СТРАНИЦЫ. Адреса шрифтов живут не в index.html, а внутри
    собранных стилей. По коду страницы приложение выглядит чистым, а в живом
    окне всё равно уходит в интернет — поймали ровно так.
    """
    вырезано: list[str] = []
    осталось: list[str] = []
    for стиль in папка.rglob("*.css"):
        if СЛЕД in стиль.name:
            continue
        try:
            текст = стиль.read_text(errors="ignore")
        except OSError:
            continue
        адреса = [а for а in re.findall(r"url\(\s*['\"]?(https?://[^)'\"]+)", текст)
                  if чужой(а)]
        if not адреса:
            continue
        новый = текст
        for а in set(адреса):
            замена = _местный_шрифт(папка, а)
            if замена:
                путь = "/" + str(замена.relative_to(папка))
                новый = новый.replace(а, путь)
                отметка = "" if замена.name == а.split("/")[-1] else " (другое начертание)"
                вырезано.append(f"{стиль.name}: {а.split('/')[-1]} → {путь}{отметка}")
            else:
                осталось.append(f"{стиль.name}: местной замены нет — {а[:70]}")
        if новый != текст:
            копия = стиль.with_suffix(стиль.suffix + СЛЕД)
            if not копия.exists():
                shutil.copyfile(стиль, копия)
            стиль.write_text(новый)
    return вырезано, осталось


def снять(файл: pathlib.Path) -> int:
    копия = файл.with_suffix(файл.suffix + СЛЕД)
    if not копия.exists():
        print(f"  ✕ нет копии {копия.name} — возвращать не из чего")
        return 1
    shutil.copyfile(копия, файл)
    print(f"  ✓ {файл.name} возвращён из {копия.name}")
    return 0


def работа(файл: pathlib.Path, только_показать: bool) -> int:
    исходный = файл.read_text(errors="ignore")
    новый, вырезано, осталось = разбор(исходный)

    # Стили правим только когда действительно меняем: показ ничего не трогает.
    if not только_показать:
        из_стилей, остатки_стилей = починить_стили(файл.parent)
        вырезано += из_стилей
        осталось += остатки_стилей

    print(f"\nСТРАНИЦА: {файл}")
    if not вырезано:
        print("  ✓ звонков наружу не нашёл — вырезать нечего")
    else:
        глагол = "нашёл" if только_показать else "вырезал"
        print(f"  {глагол} звонков наружу: {len(вырезано)}")
        for с in вырезано:
            print(f"      {с}")
    for с in осталось[:8]:
        print(f"  · {с}")

    if только_показать or not вырезано:
        return 0

    if новый != исходный:                       # страницу трогаем, только если есть что менять
        копия = файл.with_suffix(файл.suffix + СЛЕД)
        if not копия.exists():                  # первая копия — самая ценная
            shutil.copyfile(файл, копия)
            print(f"  ✓ копия исходного: {копия.name}")
        файл.write_text(новый)
        print(f"  ✓ {файл.name} обновлён")
    print("\n  ПРОВЕРИТЬ ЖИВЬЁМ, а не по коду: открыть приложение и посмотреть,")
    print("  что в окне браузера нет запросов наружу и шрифты на месте.")
    return 0


def selftest() -> int:
    import tempfile
    ошибки = []
    образец = (
        '<!doctype html><meta charset=utf-8>'
        '<link rel="canonical" href="https://excalidraw.com"/>'
        '<link rel="preconnect" href="https://fonts.googleapis.com"/>'
        '<link rel="preload" href="https://cdn.example.com/f.woff2" as="font"/>'
        '<link rel="stylesheet" href="/местный.css"/>'
        '<script src="https://чужой.example.com/a.js"></script>'
        '<script src="/assets/свой.js"></script>'
        '<script>var s=document.createElement("script");'
        's.setAttribute("src","https://scripts.simpleanalyticscdn.com/latest.js");'
        'document.body.appendChild(s);</script>'
        '<script>window.ПУТИ=["https://cdn.example.com/oss/","/",];</script>'
        '<body>ok')
    новый, вырезано, осталось = разбор(образец)

    # Вырезанное остаётся ВИДНЫМ в пометке-комментарии — это нарочно: человек
    # должен видеть, что именно убрали. Поэтому проверяем не «нет строки вовсе»,
    # а «нет загружающего тега»: комментарий ничего не грузит.
    без_меток = re.sub(re.escape(МЕТКА) + r".*?-->", "", новый, flags=re.S)
    проверки = [
        ("preconnect вырезан", "fonts.googleapis.com" not in без_меток),
        ("preload вырезан", "cdn.example.com/f.woff2" not in без_меток),
        ("чужой скрипт вырезан", "чужой.example.com" not in без_меток),
        ("счётчик вырезан", "simpleanalyticscdn" not in без_меток),
        ("подгрузка счётчика убрана целиком", "createElement" not in без_меток),
        ("чужой адрес ресурсов вырезан", "cdn.example.com/oss/" not in без_меток),
        ("пометка о вырезанном оставлена", МЕТКА in новый),
        ("canonical оставлен", 'rel="canonical"' in новый),
        ("местный стиль оставлен", "/местный.css" in новый),
        ("свой скрипт оставлен", "/assets/свой.js" in новый),
        ("местный путь в списке уцелел", '"/"' in новый or "'/'" in новый),
        ("кодировка на месте", "charset=utf-8" in новый),
    ]
    for имя, ок in проверки:
        if ок:
            print(f"  ✓ {имя}")
        else:
            ошибки.append(имя)

    if len(вырезано) != 5:
        ошибки.append(f"вырезано {len(вырезано)}, ожидалось 5")
    else:
        print("  ✓ счёт вырезанного сходится")

    # повтор ничего не ломает и не дублирует
    ещё, вырезано2, _ = разбор(новый)
    if вырезано2:
        ошибки.append(f"повторный проход снова что-то режет: {вырезано2}")
    else:
        print("  ✓ повтор ничего не меняет")

    # Стили: адреса шрифтов уводим на местные файлы, в том числе другого начертания
    with tempfile.TemporaryDirectory() as врем2:
        п = pathlib.Path(врем2)
        (п / "Assistant-Regular.woff2").write_bytes(b"woff2")
        (п / "assets").mkdir()
        (п / "assets" / "вид.css").write_text(
            '@font-face{font-family:Assistant;'
            'src:url(https://cdn.example.com/oss/fonts/Assistant/Assistant-SemiBold.woff2)}'
            '@font-face{font-family:Нет;'
            'src:url(https://cdn.example.com/oss/fonts/Нет/Нет-Regular.woff2)}')
        выр, ост = починить_стили(п)
        стало = (п / "assets" / "вид.css").read_text()
        if "/Assistant-Regular.woff2" not in стало:
            ошибки.append("шрифт не уведён на местный файл")
        elif "cdn.example.com/oss/fonts/Assistant" in стало:
            ошибки.append("чужой адрес шрифта остался в стилях")
        elif not any("другое начертание" in с for с in выр):
            ошибки.append("подмена начертания не отмечена честно")
        else:
            print("  ✓ шрифт уводится на местный файл, подмена начертания отмечена")
        if not any("местной замены нет" in с for с in ост):
            ошибки.append("отсутствие местной замены не показано")
        else:
            print("  ✓ отсутствие местной замены показывается честно")
        if not (п / "assets" / ("вид.css" + СЛЕД)).exists():
            ошибки.append("копия стиля не сохранена")
        else:
            print("  ✓ копия стиля сохраняется")

    with tempfile.TemporaryDirectory() as врем:
        ф = pathlib.Path(врем) / "index.html"
        ф.write_text(образец)
        работа(ф, только_показать=False)
        к = ф.with_suffix(".html" + СЛЕД)
        if not к.exists() or к.read_text() != образец:
            ошибки.append("копия исходного не сохранена или испорчена")
        else:
            print("  ✓ копия исходного сохранена целой")
        снять(ф)
        if ф.read_text() != образец:
            ошибки.append("возврат не восстановил исходный файл")
        else:
            print("  ✓ возврат восстанавливает файл дословно")

    if ошибки:
        for о in ошибки:
            print(f"  ✕ {о}")
        print("ИТОГ САМОПРОВЕРКИ: есть отказы")
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


def main() -> int:
    р = argparse.ArgumentParser(add_help=True)
    р.add_argument("страница", nargs="?")
    р.add_argument("--показать", action="store_true")
    р.add_argument("--снять", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()

    if а.selftest:
        return selftest()
    if not а.страница:
        р.print_help()
        return 1
    файл = pathlib.Path(а.страница).expanduser().resolve()
    if not файл.is_file():
        print(f"  ✕ нет такого файла: {файл}")
        return 1
    return снять(файл) if а.снять else работа(файл, а.показать)


if __name__ == "__main__":
    raise SystemExit(main())

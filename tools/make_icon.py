#!/usr/bin/env python3
"""Иконка продукта одной командой — в стиле Bronze Engraved.

ЗАЧЕМ. Четыре наших листинга из десяти вышли без иконки. Не из-за лени: чтобы
нарисовать картинку, нужен редактор, палитра под рукой и полчаса, а продукт готов
сейчас. Пока иконка — отдельная работа, её не будет; поэтому она должна получаться
командой, из одного канона, без ручного рисования.

    python3 tools/make_icon.py book-open products/пример/icon.svg
    python3 tools/make_icon.py book-open products/пример/icon.png   # + растр
    python3 tools/make_icon.py --образцы /tmp                       # все глифы

СТИЛЬ Bronze Engraved (спека владельца, 20.08.2026). Плитка с бронзовым
градиентом, радиус 0.27×размера, рамка, блик, мягкое затемнение у низа. Внутри —
ОДИН глиф из набора Lucide: штрих #B5722A толщиной 1.7 на сетке 24, размер
0.51×плитки, гравировка тонкой белой кромкой. Без заливок, без текста, без
логотипов внутри; максимум один золотой акцент, и им является сам штрих.

ФОРМАТ. Канонический вывод — SVG: он вектор, он источник правды, он собирается
чистым Python без единого пакета. PNG (для магазина и .icns) рендерится из этого
же SVG доступным движком (rsvg-convert или Chrome); если движка нет, рядом
кладётся .svg и печатается честный отказ — растеризатор в чистом Python честно
не осилит штриховые кривые Lucide.

Самопроверка судит SVG, а не PNG: гейт должен проходить и там, где движка нет.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

РАЗМЕР = 512

# Палитра Bronze Engraved. Другой цвет в иконке — дефект, а не мелочь.
ШТРИХ = "#B5722A"          # бронзовый глиф — единственный акцент
РАМКА = "#C57E33"          # цвет рамки (прозрачность задаётся отдельно)

# Глифы Lucide по имени: внутренняя разметка на сетке 24×24, штрихом, без заливок.
# Пути взяты из Lucide как есть — «ничего не рисовать руками» относится и к нам.
ГЛИФЫ = {
    "book-open": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "table": '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "library": '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/>',
    "bar-chart-3": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "presentation": '<path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/><path d="M12 16v5"/>',
    "network": '<rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/>',
    "arrow-left-right": '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    "app-window": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 4v4"/><path d="M2 8h20"/><path d="M6 4v4"/>',
    "trash-2": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "box": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
}

# Русские имена, которыми зовут генератор старые вызовы, на глифы Lucide.
СИНОНИМЫ = {
    "доска": "network",       # доска схем — схема как сеть узлов
    "сторож": "activity",     # сторож — линия активности
    "docs": "book-open",
    "tech": "settings",
}


def _глиф_имя(имя):
    имя = (имя or "").strip()
    return СИНОНИМЫ.get(имя, имя)


ЗНАКИ = sorted(set(ГЛИФЫ) | set(СИНОНИМЫ))


def svg(имя, размер=РАЗМЕР):
    """Bronze Engraved SVG с глифом Lucide по имени. Чистый Python, без пакетов."""
    ключ = _глиф_имя(имя)
    if ключ not in ГЛИФЫ:
        print(f"make_icon: неизвестный глиф «{имя}». Доступны: {', '.join(ЗНАКИ)}",
              file=sys.stderr)
        sys.exit(2)

    р = размер
    радиус = round(р * 0.27, 2)               # спека: 0.27×размера
    глиф_px = round(р * 0.51, 2)              # спека: 0.51×плитки
    сдвиг = round((р - глиф_px) / 2, 2)
    масштаб = round(глиф_px / 24, 4)          # сетка Lucide 24
    кромка = max(1, round(р / 73))            # светлая кромка ~1px@74

    # Направление градиента 165°, спроецированное на квадрат размера р.
    # d=(sin165, cos165)=(0.2588, -0.9659); длина полулинии ~0.612×р.
    L = 0.612 * р
    x1 = round(р / 2 - 0.2588 * L, 1); y1 = round(р / 2 - 0.9659 * L, 1)
    x2 = round(р / 2 + 0.2588 * L, 1); y2 = round(р / 2 + 0.9659 * L, 1)
    грав = max(1, round(р / 256, 2))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{р}" height="{р}" '
        f'viewBox="0 0 {р} {р}">\n'
        f'  <defs>\n'
        f'    <linearGradient id="fon" gradientUnits="userSpaceOnUse" '
        f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">\n'
        f'      <stop offset="0" stop-color="#FFFDF9"/>\n'
        f'      <stop offset="0.55" stop-color="#F0EBE0"/>\n'
        f'      <stop offset="1" stop-color="#E4DDD0"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="blik" x1="0" y1="0" x2="0" y2="1">\n'
        f'      <stop offset="0" stop-color="#ffffff" stop-opacity="0.6"/>\n'
        f'      <stop offset="0.45" stop-color="#ffffff" stop-opacity="0"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="niz" x1="0" y1="0" x2="0" y2="1">\n'
        f'      <stop offset="0.72" stop-color="#8C6E3C" stop-opacity="0"/>\n'
        f'      <stop offset="1" stop-color="#8C6E3C" stop-opacity="0.14"/>\n'
        f'    </linearGradient>\n'
        f'    <clipPath id="плитка"><rect width="{р}" height="{р}" rx="{радиус}"/></clipPath>\n'
        f'    <filter id="грав" x="-10%" y="-10%" width="120%" height="120%">\n'
        f'      <feDropShadow dx="0" dy="{грав}" stdDeviation="0.4" '
        f'flood-color="#ffffff" flood-opacity="0.85"/>\n'
        f'    </filter>\n'
        f'  </defs>\n'
        f'  <g clip-path="url(#плитка)">\n'
        f'    <rect width="{р}" height="{р}" fill="url(#fon)"/>\n'
        f'    <rect width="{р}" height="{р}" fill="url(#niz)"/>\n'
        f'    <rect x="0" y="0" width="{р}" height="{кромка}" fill="#ffffff" opacity="0.6"/>\n'
        f'    <g filter="url(#грав)">\n'
        f'      <g transform="translate({сдвиг},{сдвиг}) scale({масштаб})" fill="none" '
        f'stroke="{ШТРИХ}" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round">{ГЛИФЫ[ключ]}</g>\n'
        f'    </g>\n'
        f'    <rect width="{р}" height="{р}" fill="url(#blik)"/>\n'
        f'  </g>\n'
        f'  <rect x="0.5" y="0.5" width="{р-1}" height="{р-1}" rx="{round(радиус-0.5, 2)}" '
        f'fill="none" stroke="{РАМКА}" stroke-opacity="0.35" stroke-width="1"/>\n'
        f'</svg>\n'
    )


def _который(имя):
    for каталог in os.environ.get("PATH", "").split(os.pathsep):
        путь = os.path.join(каталог, имя)
        if os.path.isfile(путь) and os.access(путь, os.X_OK):
            return путь
    return None


def _растеризатор():
    """Первый доступный движок SVG→PNG: (вид, путь). Чистого Python-растра нет:
    штриховые кривые Lucide он честно не осилит, а плохой растр хуже отказа."""
    rsvg = _который("rsvg-convert")
    if rsvg:
        return ("rsvg", rsvg)
    for chrome in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        _который("google-chrome"), _который("chromium"), _который("chromium-browser"),
    ):
        if chrome and os.path.isfile(chrome):
            return ("chrome", chrome)
    return (None, None)


def png(имя, размер=РАЗМЕР):
    """PNG-байты из SVG доступным движком. Без движка — понятный отказ."""
    вид, движок = _растеризатор()
    разметка = svg(имя, размер)
    if вид == "rsvg":
        # Через временные файлы, а не /dev/stdout: rsvg-convert падает на
        # усечении трубы («Error truncating file: Invalid argument»).
        with tempfile.TemporaryDirectory() as tmp:
            svg_path = os.path.join(tmp, "i.svg")
            png_path = os.path.join(tmp, "i.png")
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(разметка)
            completed = subprocess.run(
                [движок, "-w", str(размер), "-h", str(размер), "-o", png_path, svg_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            if completed.returncode == 0 and os.path.isfile(png_path):
                with open(png_path, "rb") as f:
                    данные = f.read()
                if данные[:8] == b"\x89PNG\r\n\x1a\n":
                    return данные
        raise RuntimeError("rsvg-convert не отдал PNG")
    if вид == "chrome":
        with tempfile.TemporaryDirectory() as tmp:
            html = os.path.join(tmp, "i.html")
            out = os.path.join(tmp, "i.png")
            with open(html, "w", encoding="utf-8") as f:
                f.write('<!doctype html><html><head><meta charset="utf-8">'
                        '<style>html,body{margin:0;padding:0}'
                        f'img{{display:block;width:{размер}px;height:{размер}px}}</style>'
                        '</head><body><img src="i.svg"></body></html>')
            with open(os.path.join(tmp, "i.svg"), "w", encoding="utf-8") as f:
                f.write(разметка)
            subprocess.run([движок, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=1", "--default-background-color=00000000",
                            f"--window-size={размер},{размер}", f"--screenshot={out}",
                            f"file://{html}"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=90)
            if os.path.isfile(out):
                with open(out, "rb") as f:
                    return f.read()
        raise RuntimeError("Chrome не отдал PNG")
    raise RuntimeError(
        "нет движка SVG→PNG (rsvg-convert или Chrome). SVG сохранён рядом — "
        "растеризуйте им или установите rsvg: brew install librsvg")


# Обратная совместимость: старый вызов ждал PNG-байты из нарисовать().
def нарисовать(имя, размер=РАЗМЕР):
    return png(имя, размер)


def _записать(имя, цель):
    цель = pathlib.Path(цель)
    цель.parent.mkdir(parents=True, exist_ok=True)
    if цель.suffix.lower() == ".svg":
        цель.write_text(svg(имя), encoding="utf-8")
        print(f"иконка готова: {цель} ({цель.stat().st_size} байт, SVG)")
        return
    try:
        цель.write_bytes(png(имя))
        print(f"иконка готова: {цель} ({цель.stat().st_size} байт, PNG)")
    except RuntimeError as ошибка:
        запас = цель.with_suffix(".svg")
        запас.write_text(svg(имя), encoding="utf-8")
        print(f"make_icon: {ошибка}", file=sys.stderr)
        print(f"  SVG сохранён: {запас}", file=sys.stderr)
        sys.exit(1)


def _selftest() -> int:
    провалы = []
    for имя in ЗНАКИ:
        s = svg(имя, 128)
        глиф = ГЛИФЫ[_глиф_имя(имя)]
        тело_глифа = глиф.split('"')[1][:6]   # начало первого d/rect — маркер, что глиф на месте
        # Иконка обязана быть Bronze Engraved: плитка с бронзовым градиентом,
        # рамка, блик, и ровно один бронзовый штрих-глиф. Проверяем структуру
        # SVG, а не PNG: гейт должен проходить там, где движка нет.
        ок = (
            s.startswith("<svg") and 'viewBox="0 0 128 128"' in s
            and "url(#fon)" in s and "#FFFDF9" in s and "#E4DDD0" in s  # градиент
            and 'rx="34.56"' in s                                       # 0.27×128
            and f'stroke="{ШТРИХ}"' in s and 'stroke-width="1.7"' in s  # штрих
            and "url(#грав)" in s                                       # гравировка
            and "url(#blik)" in s                                       # блик
            and f'stroke="{РАМКА}"' in s and 'stroke-opacity="0.35"' in s  # рамка
            and тело_глифа in s                                         # тело глифа на месте
            and s.count(ШТРИХ) == 1                                     # ровно один акцент
        )
        print(("  ✓ " if ок else "  ✗ ") + f"{имя}: SVG {len(s)} байт")
        if not ок:
            провалы.append(имя)
    # Несуществующий глиф обязан честно отказать, а не нарисовать пустоту.
    try:
        svg("такого-нет", 64)
        провалы.append("неизвестный глиф не отказал")
        print("  ✗ неизвестный глиф не отказал")
    except SystemExit:
        print("  ✓ неизвестный глиф отказывает честно")
    # Синоним обязан вести на существующий глиф.
    for син, цель in СИНОНИМЫ.items():
        if цель not in ГЛИФЫ:
            провалы.append(f"синоним {син} ведёт в никуда")
    if провалы:
        print("ИТОГ САМОПРОВЕРКИ: провалы —", "; ".join(провалы))
        return 1
    print("ИТОГ САМОПРОВЕРКИ: все проверки прошли")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--образцы" in sys.argv:
        куда = pathlib.Path(sys.argv[sys.argv.index("--образцы") + 1])
        куда.mkdir(parents=True, exist_ok=True)
        for имя in sorted(ГЛИФЫ):
            (куда / f"icon_{имя}.svg").write_text(svg(имя), encoding="utf-8")
            print("  ", куда / f"icon_{имя}.svg")
        sys.exit(0)
    if len(sys.argv) < 3:
        print(__doc__)
        print("глифы:", ", ".join(sorted(ГЛИФЫ)))
        print("синонимы:", ", ".join(f"{k}→{v}" for k, v in СИНОНИМЫ.items()))
        sys.exit(2)
    _записать(sys.argv[1], sys.argv[2])

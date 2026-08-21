#!/usr/bin/env python3
"""Цветные серии плиток Extella. Решение владельца (Анвар) 21.08.2026:
стол делится на три серии по цвету штриха — бронза остаётся продуктам и
агентам, петроль-зелёная — офисным инструментам, стальная синяя —
управленческим панелям. Геометрия, крем-фон и гравировка — без изменений:
исполняемый источник стиля остаётся bronze_icon.py, здесь только цвет.

Синий #3A6EA5 не новый: это акцент карточек КТ-модулей, закреплён серией.

    python3 tools/цветная_плитка.py зелёная table editions/tablica/icon.png
    python3 tools/цветная_плитка.py синяя coins editions/ceo-finance/icon.png
    python3 tools/цветная_плитка.py --selftest
"""

import pathlib
import subprocess
import sys

СЮДА = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(СЮДА))
import bronze_icon  # noqa: E402

# Бронзовые цвета спеки → цвет серии. Меняются ровно четыре: штрих, рамка,
# нижняя внутренняя тень, внешняя тень. Всё остальное — общее для всех серий.
СЕРИИ = {
    "зелёная": {                              # петроль из палитры Extella
        "#B5722A": "#2F6B66",
        "rgba(197,126,51,.35)": "rgba(47,107,102,.35)",
        "#8C6E3C": "#3C6B5E",
        "#5A4628": "#28463E",
    },
    "синяя": {                                # сталь КТ-модулей, #3A6EA5
        "#B5722A": "#3A6EA5",
        "rgba(197,126,51,.35)": "rgba(58,110,165,.35)",
        "#8C6E3C": "#3C566B",
        "#5A4628": "#283850",
    },
}


def svg_серии(глиф: str, серия: str, размер: int = 512) -> str:
    svg = bronze_icon.svg_плитки(глиф, размер)
    for бронза, цвет in СЕРИИ[серия].items():
        svg = svg.replace(бронза, цвет)
    return svg


def сделать(серия: str, глиф_имя: str, куда: pathlib.Path, размер: int = 512) -> None:
    if серия not in СЕРИИ:
        raise SystemExit(f"серии «{серия}» нет. Есть: {', '.join(СЕРИИ)}; "
                         f"бронзовую делает bronze_icon.py")
    svg = svg_серии(bronze_icon.тело_глифа(глиф_имя), серия)
    куда.parent.mkdir(parents=True, exist_ok=True)
    куда.with_suffix(".svg").write_text(svg)
    bronze_icon.в_png(svg, куда, размер)
    subprocess.run(["sips", "-z", "256", "256", str(куда)],
                   capture_output=True, timeout=30)
    вес = куда.stat().st_size
    if вес > 60_000:
        raise SystemExit(f"плитка вышла {вес} байт — застрянет в кэше стола")
    print(f"{серия} плитка готова: {куда} ({вес} байт, 256px) + svg рядом")


def selftest() -> int:
    ошибки = []
    for серия in СЕРИИ:
        svg = svg_серии(bronze_icon.тело_глифа("table"), серия)
        штрих = СЕРИИ[серия]["#B5722A"]
        if штрих not in svg:
            ошибки.append(f"{серия}: штрих {штрих} не попал в svg")
        elif "#B5722A" in svg:
            ошибки.append(f"{серия}: бронзовый штрих остался — замена неполная")
        elif "#FFFDF9" not in svg or 'stroke-width="1.7"' not in svg:
            ошибки.append(f"{серия}: крем-фон или толщина штриха потеряны")
        else:
            print(f"  ✓ {серия}: штрих {штрих}, фон и гравировка спеки на месте")
    try:
        сделать("фиолетовая", "table", pathlib.Path("/tmp/никогда.png"))
        ошибки.append("выдуманная серия не отвергнута")
    except SystemExit:
        print("  ✓ выдуманная серия отвергается словами")
    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    сделать(sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).expanduser())

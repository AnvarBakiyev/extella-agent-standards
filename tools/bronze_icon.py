#!/usr/bin/env python3
"""Иконки «Bronze Engraved» — стиль всех плиток Extella. Спека Анвара, 20.08.2026.

СПЕКА (метрика 74px, всё масштабируется пропорционально):
  плитка: radius 0.27×size; фон linear-gradient(165deg, #FFFDF9 0%, #F0EBE0 55%,
  #E4DDD0 100%); рамка 1px rgba(197,126,51,.35); блик сверху white .6→0 до 45%;
  тени inset 0 1px 1px #fff, inset 0 -3px 6px rgba(140,110,60,.14),
  внешняя 0 5px 14px rgba(90,70,40,.14).
  глиф: сетка Lucide 24×24, размер 0.51×плитки; stroke #B5722A, width 1.7,
  cap/join round; гравировка drop-shadow(0 1px 0 rgba(255,255,255,.9)).

ПРАВИЛА НАБОРА (из спеки, проверяются кодом):
  глифы ТОЛЬКО из Lucide (templates/lucide/, вшиты с лицензией ISC) — руками не
  рисовать; один глиф = одна линия, без заливок, текста и логотипов; сторонние
  приложения оборачиваются в ту же плитку монохромным штрихом — родные PNG
  не показываем.

PNG для витрины рендерит Chrome из SVG: спека живёт градиентами и тенями,
которые честно воспроизводятся браузером, а не нашей самодельной растеризацией.

    python3 tools/bronze_icon.py table editions/tablica/icon.png
    python3 tools/bronze_icon.py --список
    python3 tools/bronze_icon.py --selftest
"""

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

СЮДА = pathlib.Path(__file__).resolve().parent
ГЛИФЫ = СЮДА.parent / "templates" / "lucide"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Метрика спеки: всё задано для плитки 74px и масштабируется линейно.
БАЗА = 74.0


def тело_глифа(имя: str) -> str:
    """Достать содержимое Lucide-глифа. Только из вшитого набора — руками не рисуем."""
    ф = ГЛИФЫ / f"{имя}.svg"
    if not ф.exists():
        есть = ", ".join(sorted(x.stem for x in ГЛИФЫ.glob("*.svg")))
        raise SystemExit(f"глифа «{имя}» нет в наборе. Есть: {есть}. "
                         f"Добавить: curl -sL https://unpkg.com/lucide-static@latest/"
                         f"icons/{имя}.svg -o {ф}")
    т = ф.read_text()
    # Лицензионный комментарий Lucide стоит ПЕРЕД <svg>: наивный поиск первого
    # «>» хватал открывающий тег целиком, и глиф приезжал вложенным svg со
    # своими stroke="currentColor" и width=2 — чёрный и жирный. Замер 20.08.2026.
    т = re.sub(r"<!--.*?-->", "", т, flags=re.S)
    м = re.search(r"<svg\b[^>]*>(.*?)</svg>", т, re.S)
    if not м:
        raise SystemExit(f"файл {ф} не похож на Lucide-глиф")
    внутренности = м.group(1).strip()
    if re.search(r"<(text|image)\b", внутренности) or 'fill="#' in внутренности:
        raise SystemExit(f"глиф «{имя}» нарушает правила набора: заливки/текст запрещены")
    return внутренности


def svg_плитки(глиф: str, размер: int = 512) -> str:
    """Собрать плитку по спеке. Каждое число — из спеки × масштаб, не на глаз."""
    м = размер / БАЗА                       # масштаб от 74-пиксельной метрики
    поле = round(9 * м)                     # запас под внешнюю тень
    плитка = размер - 2 * поле
    рад = round(0.27 * плитка)
    глиф_рзм = round(0.51 * плитка)
    гх = поле + (плитка - глиф_рзм) / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{размер}" height="{размер}"
     viewBox="0 0 {размер} {размер}">
  <defs>
    <linearGradient id="фон" gradientTransform="rotate(75 .5 .5)">
      <stop offset="0" stop-color="#FFFDF9"/>
      <stop offset=".55" stop-color="#F0EBE0"/>
      <stop offset="1" stop-color="#E4DDD0"/>
    </linearGradient>
    <linearGradient id="блик" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".6"/>
      <stop offset=".45" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="низ" x1="0" y1="0" x2="0" y2="1">
      <stop offset=".8" stop-color="#8C6E3C" stop-opacity="0"/>
      <stop offset="1" stop-color="#8C6E3C" stop-opacity=".14"/>
    </linearGradient>
    <filter id="тень" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="{5*м:.1f}" stdDeviation="{7*м:.1f}"
                    flood-color="#5A4628" flood-opacity=".14"/>
    </filter>
    <clipPath id="кп"><rect x="{поле}" y="{поле}" width="{плитка}" height="{плитка}"
      rx="{рад}"/></clipPath>
  </defs>

  <g filter="url(#тень)">
    <rect x="{поле}" y="{поле}" width="{плитка}" height="{плитка}" rx="{рад}"
          fill="url(#фон)"/>
  </g>
  <g clip-path="url(#кп)">
    <rect x="{поле}" y="{поле}" width="{плитка}" height="{плитка}" fill="url(#блик)"/>
    <rect x="{поле}" y="{поле}" width="{плитка}" height="{плитка}" fill="url(#низ)"/>
    <rect x="{поле}" y="{поле+1*м:.1f}" width="{плитка}" height="{плитка}" rx="{рад}"
          fill="none" stroke="#FFFFFF" stroke-opacity=".9" stroke-width="{1*м:.1f}"/>
  </g>
  <rect x="{поле}" y="{поле}" width="{плитка}" height="{плитка}" rx="{рад}"
        fill="none" stroke="rgba(197,126,51,.35)" stroke-width="{1*м:.1f}"/>

  <g transform="translate({гх:.1f} {гх+1*м:.1f}) scale({глиф_рзм/24:.3f})"
     fill="none" stroke="#FFFFFF" stroke-opacity=".9" stroke-width="1.7"
     stroke-linecap="round" stroke-linejoin="round">
    {глиф}
  </g>
  <g transform="translate({гх:.1f} {гх:.1f}) scale({глиф_рзм/24:.3f})"
     fill="none" stroke="#B5722A" stroke-width="1.7" stroke-linecap="round"
     stroke-linejoin="round">
    {глиф}
  </g>
</svg>'''


def в_png(svg: str, куда: pathlib.Path, размер: int) -> None:
    with tempfile.TemporaryDirectory() as вр:
        стр = pathlib.Path(вр) / "плитка.html"
        стр.write_text(f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                       f"<style>html,body{{margin:0;background:transparent}}</style>"
                       f"</head><body>{svg}</body></html>")
        итог = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
             f"--screenshot={куда}", f"--window-size={размер},{размер}",
             "--default-background-color=00000000", "--hide-scrollbars",
             str(стр)], capture_output=True, text=True, timeout=60)
        if not куда.exists():
            raise SystemExit(f"Chrome не отрисовал плитку: {итог.stderr[-300:]}")


def сделать(глиф_имя: str, куда: pathlib.Path, размер: int = 512) -> None:
    svg = svg_плитки(тело_глифа(глиф_имя), размер)
    куда.parent.mkdir(parents=True, exist_ok=True)
    куда.with_suffix(".svg").write_text(svg)      # SVG 1× — канонический экспорт спеки
    в_png(svg, куда, размер)
    # Витринная плитка обязана быть ЛЁГКОЙ: стол Extella кэширует карточки в
    # localStorage, и тяжёлая запись падает МОЛЧА — плитка навсегда застревает
    # старой (задокументированный капкан; воспроизведён 20.08.2026: бронза
    # 100 КБ не доехала до стола, при том что «худой» Сторож доехал).
    # Рендерим 512 ради гладкости и ужимаем штатным sips до 256.
    subprocess.run(["sips", "-z", "256", "256", str(куда)],
                   capture_output=True, timeout=30)
    вес = куда.stat().st_size
    if вес > 60_000:
        raise SystemExit(f"плитка вышла {вес} байт — такая застрянет в кэше стола")
    print(f"плитка готова: {куда} ({вес} байт, 256px) + svg рядом")


def selftest() -> int:
    ошибки = []
    if not ГЛИФЫ.exists() or not (ГЛИФЫ / "LICENSE").exists():
        ошибки.append("нет вшитого набора Lucide с лицензией — глифы взять неоткуда")
    else:
        print(f"  ✓ набор Lucide вшит ({len(list(ГЛИФЫ.glob('*.svg')))} глифов) "
              f"с лицензией ISC")

    svg = svg_плитки(тело_глифа("table"), 512)
    прв = [("#B5722A" in svg, "штрих не бронзовый"),
           ('stroke-width="1.7"' in svg, "толщина штриха не по спеке"),
           ("rgba(197,126,51,.35)" in svg, "рамка не по спеке"),
           ("#FFFDF9" in svg and "#E4DDD0" in svg, "градиент фона не по спеке"),
           (f'rx="{round(0.27 * (512 - 2 * round(9 * 512 / 74)))}"' in svg,
            "радиус не 0.27×плитки")]
    for ок, что in прв:
        if not ок:
            ошибки.append(что)
    if not any(что in ошибки for _, что in прв):
        print("  ✓ плитка собирается по спеке: бронза 1.7, рамка, градиент, радиус 0.27")

    try:
        тело_глифа("несуществующий-глиф")
        ошибки.append("выдуманный глиф не отвергнут — открыта дорога рисованию руками")
    except SystemExit:
        print("  ✓ глиф не из набора Lucide отвергается — руками не рисуем")

    if not pathlib.Path(CHROME).exists():
        ошибки.append("нет Chrome — PNG рендерить нечем")
    else:
        print("  ✓ Chrome на месте — PNG рендерится честным браузером")

    print("\n" + ("ИТОГ САМОПРОВЕРКИ: все проверки прошли" if not ошибки
                  else "ОТКАЗ:\n  " + "\n  ".join(ошибки)))
    return 1 if ошибки else 0


def main() -> int:
    р = argparse.ArgumentParser(description="Плитка Bronze Engraved из Lucide-глифа")
    р.add_argument("глиф", nargs="?")
    р.add_argument("куда", nargs="?")
    р.add_argument("--размер", type=int, default=512)
    р.add_argument("--список", action="store_true")
    р.add_argument("--selftest", action="store_true")
    а = р.parse_args()
    if а.selftest:
        return selftest()
    if а.список:
        print("глифы в наборе:", ", ".join(sorted(x.stem for x in ГЛИФЫ.glob("*.svg"))))
        return 0
    if not (а.глиф and а.куда):
        р.print_help()
        return 1
    сделать(а.глиф, pathlib.Path(а.куда).expanduser(), а.размер)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Gera um card com as linguagens mais usadas, contadas por bytes de codigo.

Diferente dos cards do github-profile-summary-cards, que atribuem uma unica
linguagem (a primaria) para cada repositorio, aqui somamos o breakdown de bytes
de todos os repositorios publicos do usuario. Assim um repositorio como
CCpuc-mg, classificado como Java, ainda contribui com seus bytes de C.
"""

import json
import math
import os
import urllib.request

USER = os.environ.get("CARD_USER", "pedrohlmelo")
OUTPUT = os.environ.get("CARD_OUTPUT", "assets/top-languages.svg")
EXCLUDE = {
    lang.strip().lower()
    for lang in os.environ.get("CARD_EXCLUDE", "Swift,HTML,CSS,JavaScript,Verilog").split(",")
    if lang.strip()
}
TOP_N = int(os.environ.get("CARD_TOP_N", "5"))

# Cores oficiais do linguist para as linguagens que aparecem aqui.
COLORS = {
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "CMake": "#DA3434",
    "Assembly": "#6E4C13",
    "Python": "#3572A5",
    "Dart": "#00B4AB",
    "TeX": "#3D6117",
    "Kotlin": "#A97BFF",
    "Objective-C": "#438eff",
    "VHDL": "#adb2cb",
    "Shell": "#89e051",
    "Makefile": "#427819",
    "Verilog": "#b2b7f8",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Swift": "#F05138",
}
FALLBACK_COLOR = "#586e75"

BG = "#1a1b27"
TITLE_COLOR = "#70a5fd"
TEXT_COLOR = "#38bdae"


def api(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect_bytes():
    totals = {}
    page = 1
    while True:
        repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork") or repo.get("archived"):
                continue
            for lang, size in api(repo["languages_url"]).items():
                if lang.lower() in EXCLUDE:
                    continue
                totals[lang] = totals.get(lang, 0) + size
        if len(repos) < 100:
            break
        page += 1
    return totals


def arc_path(cx, cy, outer, inner, start, end):
    """Caminho de um anel entre dois angulos (em radianos, 0 = topo)."""
    large = 1 if end - start > math.pi else 0

    def point(radius, angle):
        return (
            round(cx + radius * math.sin(angle), 3),
            round(cy - radius * math.cos(angle), 3),
        )

    x1, y1 = point(outer, start)
    x2, y2 = point(outer, end)
    x3, y3 = point(inner, end)
    x4, y4 = point(inner, start)
    return (
        f"M{x1},{y1}A{outer},{outer},0,{large},1,{x2},{y2}"
        f"L{x3},{y3}A{inner},{inner},0,{large},0,{x4},{y4}Z"
    )


def render(totals):
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:TOP_N]
    total = sum(size for _, size in ranked) or 1

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="340" height="200" viewBox="0 0 340 200">',
        "<style>* { font-family: 'Segoe UI', Ubuntu, Sans-Serif }</style>",
        f'<rect x="1" y="1" rx="5" ry="5" height="99%" width="99.4%" stroke="{BG}" '
        f'stroke-width="1" fill="{BG}"/>',
        f'<text x="30" y="40" style="font-size: 22px; fill: {TITLE_COLOR};">Top Languages by Code</text>',
    ]

    angle = 0.0
    for index, (lang, size) in enumerate(ranked):
        color = COLORS.get(lang, FALLBACK_COLOR)
        sweep = 2 * math.pi * size / total
        # Um unico item ocupa o circulo inteiro: dois semicirculos evitam o arco degenerado.
        if sweep >= 2 * math.pi - 1e-9:
            for half_start, half_end in ((0.0, math.pi), (math.pi, 2 * math.pi)):
                parts.append(
                    f'<path d="{arc_path(250, 118, 60, 35, half_start, half_end)}" fill="{color}"/>'
                )
        else:
            parts.append(f'<path d="{arc_path(250, 118, 60, 35, angle, angle + sweep)}" fill="{color}"/>')
        angle += sweep

        y = 70 + index * 25
        percent = 100 * size / total
        parts.append(f'<rect x="40" y="{y - 12}" width="14" height="14" rx="2" fill="{color}"/>')
        parts.append(
            f'<text x="62" y="{y}" style="font-size: 14px; fill: {TEXT_COLOR};">'
            f"{lang} {percent:.1f}%</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    totals = collect_bytes()
    if not totals:
        raise SystemExit("nenhuma linguagem encontrada")
    svg = render(totals)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as handle:
        print(svg, file=handle)
    print(f"{OUTPUT}: " + ", ".join(f"{lang} {size}" for lang, size in sorted(totals.items(), key=lambda i: -i[1])[:8]))


if __name__ == "__main__":
    main()

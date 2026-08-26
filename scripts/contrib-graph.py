#!/usr/bin/env python3
"""Gera o grafico de contribuicoes dos ultimos 12 meses como SVG estatico.

Substitui o github-readme-activity-graph, cuja instancia publica foi desativada
(HTTP 402). Os dados vem da GraphQL do GitHub, e o SVG e commitado no proprio
repositorio, entao nao dependemos de nenhum servico de terceiro no ar.

CARD_MOCK=1 gera dados sinteticos, para conferir o desenho sem token.
"""

import datetime
import json
import math
import os
import random
import urllib.request

USER = os.environ.get("CARD_USER", "pedrohlmelo")
OUTPUT = os.environ.get("CARD_GRAPH_OUTPUT", "assets/contributions.svg")

BG = "#1a1b27"
LINE = "#58a6ff"
AREA = "#1f6feb"
GRID = "#2c3050"
TEXT = "#8b949e"
TITLE = "#70a5fd"

WIDTH, HEIGHT = 840, 260
LEFT, RIGHT, TOP, BOTTOM = 60, 24, 64, 44

QUERY = """
query Contributions($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_days():
    if os.environ.get("CARD_MOCK"):
        random.seed(7)
        today = datetime.date.today()
        return [
            (today - datetime.timedelta(days=364 - i), max(0, int(random.gauss(2, 3))))
            for i in range(365)
        ]

    token = os.environ["GITHUB_TOKEN"]
    to = datetime.datetime.now(datetime.timezone.utc)
    since = to - datetime.timedelta(days=364)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": USER,
                "from": since.isoformat(),
                "to": to.isoformat(),
            },
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "errors" in body:
        raise SystemExit(f"GraphQL: {body['errors']}")
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append((datetime.date.fromisoformat(day["date"]), day["contributionCount"]))
    return sorted(days)


def nice_ceiling(value):
    """Arredonda o topo do eixo para 1/2/5 x 10^n, para os rotulos ficarem redondos."""
    if value <= 5:
        return 5
    exponent = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 5, 10):
        if value <= step * exponent:
            return int(step * exponent)
    return int(10 * exponent)


def weekly(days):
    """Agrupa os dias em semanas: 52 pontos desenham melhor que 365."""
    buckets = []
    for index in range(0, len(days), 7):
        chunk = days[index:index + 7]
        buckets.append((chunk[0][0], sum(count for _, count in chunk)))
    return buckets


def render(days):
    weeks = weekly(days)
    plot_width = WIDTH - LEFT - RIGHT
    plot_height = HEIGHT - TOP - BOTTOM
    top_value = nice_ceiling(max(count for _, count in weeks) or 1)
    total = sum(count for _, count in days)

    def x_at(index):
        return LEFT + plot_width * index / max(len(weeks) - 1, 1)

    def y_at(count):
        return TOP + plot_height * (1 - count / top_value)

    points = [(round(x_at(i), 2), round(y_at(c), 2)) for i, (_, c) in enumerate(weeks)]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        "<style>* { font-family: 'Segoe UI', Ubuntu, Sans-Serif }</style>",
        f'<rect x="1" y="1" rx="5" ry="5" width="{WIDTH - 2}" height="{HEIGHT - 2}" fill="{BG}"/>',
        f'<text x="{LEFT - 30}" y="38" style="font-size: 20px; fill: {TITLE};">'
        f"Contribuições nos últimos 12 meses ({total})</text>",
        f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{AREA}" stop-opacity="0.65"/>'
        f'<stop offset="100%" stop-color="{AREA}" stop-opacity="0.03"/></linearGradient>',
    ]

    # Linhas de grade horizontais com os valores do eixo Y.
    for step in range(5):
        value = top_value * step / 4
        y = round(y_at(value), 2)
        parts.append(
            f'<line x1="{LEFT}" y1="{y}" x2="{WIDTH - RIGHT}" y2="{y}" stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{LEFT - 10}" y="{y + 4}" text-anchor="end" '
            f'style="font-size: 11px; fill: {TEXT};">{int(value)}</text>'
        )

    # Um rotulo de mes a cada dois meses, na primeira semana daquele mes.
    seen = set()
    for index, (day, _) in enumerate(weeks):
        key = (day.year, day.month)
        if key in seen or day.month % 2 == 1:
            continue
        seen.add(key)
        parts.append(
            f'<text x="{round(x_at(index), 2)}" y="{HEIGHT - BOTTOM + 22}" text-anchor="middle" '
            f'style="font-size: 11px; fill: {TEXT};">{day.strftime("%m/%y")}</text>'
        )

    line = " ".join(f"{x},{y}" for x, y in points)
    baseline = TOP + plot_height
    parts.append(
        f'<polygon points="{LEFT},{baseline} {line} {WIDTH - RIGHT},{baseline}" fill="url(#area)"/>'
    )
    parts.append(
        f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main():
    days = fetch_days()
    svg = render(days)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as handle:
        print(svg, file=handle)
    print(f"{OUTPUT}: {len(days)} dias, {sum(c for _, c in days)} contribuicoes")


if __name__ == "__main__":
    main()

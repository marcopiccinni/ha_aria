"""Parser tests using small synthetic HTML snippets (no real site data)."""

from __future__ import annotations

from ha_aria.parser import parse_air


def _period(name: str, value: str, pct: str, cat: str) -> str:
    return (
        f'<div style="flex-basis:120px">{name}</div>'
        f'<span class="value">{value} µg/m³</span>'
        f'<div class="reliability-indicator" style="left:{pct}%"></div>'
        f'<div class="tag tag-green ds-label-small">{cat}</div>'
    )


def _item(
    weekday: str,
    short: str,
    cat: str,
    maximum: str,
    mean: str,
    periods: list[tuple[str, str, str, str]],
) -> str:
    body = "".join(_period(*period) for period in periods)
    return (
        '<li class="fc-accordion-item active">'
        f'<span aria-label="{weekday}">{short}</span>'
        f'<div class="tag tag-green ds-label-small">{cat}</div>'
        f"Max: {maximum} µg/m³ Media: {mean} µg/m³"
        f"{body}"
        "</li>"
    )


def _page(pollutants: list[tuple[str, str, list[str]]]) -> str:
    tabs = "".join(
        f'<div data-pollutant="{key}"><div class="chips outlined">{label}</div></div>'
        for key, label, _ in pollutants
    )
    panels = "".join(
        f'<div id="{index}" class="content-day">' + "".join(days) + "</div>"
        for index, (_, _, days) in enumerate(pollutants)
    )
    return "<html><body>" + tabs + panels + "</body></html>"


def test_parse_air_extracts_days_and_periods() -> None:
    day_one = _item(
        "lunedì 14",
        "Lun",
        "Buona",
        "20,5",
        "15,2",
        [("Notte", "12,3", "42", "Buona"), ("Mattina", "18,0", "55", "Buona")],
    )
    day_two = _item(
        "martedì 15",
        "Mar",
        "Accettabile",
        "44,0",
        "30,1",
        [("Notte", "25,0", "61", "Accettabile")],
    )
    html = _page(
        [
            ("pm25", "PM2.5", [day_one, day_two]),
            ("pm10", "PM10", [day_two]),
        ]
    )

    report = parse_air(html, "roma")

    assert report.canonical == "roma"
    assert set(report.pollutants) == {"pm25", "pm10"}
    pm25 = report.pollutants["pm25"]
    assert len(pm25) == 2
    first = pm25[0]
    assert first.label == "lunedì 14"
    assert first.short == "Lun"
    assert first.category == "Buona"
    assert first.maximum == 20.5
    assert first.mean == 15.2
    assert first.periods["Notte"].value == 12.3
    assert first.periods["Notte"].indicator == 42.0
    assert first.periods["Notte"].category == "Buona"
    assert pm25[1].category == "Accettabile"
    assert len(report.pollutants["pm10"]) == 1


def test_parse_air_empty_html() -> None:
    report = parse_air("", "roma")
    assert report.pollutants == {}

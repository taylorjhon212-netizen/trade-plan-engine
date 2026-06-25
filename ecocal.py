from datetime import datetime, timedelta
import requests


EVENTS_CACHE = None


def get_upcoming_events(days_ahead: int = 7) -> list:
    global EVENTS_CACHE
    if EVENTS_CACHE:
        return EVENTS_CACHE

    events = _fetch_macro_events()
    if not events:
        events = _default_events()
    now = datetime.now()
    cutoff = now + timedelta(days=days_ahead)
    upcoming = [e for e in events if now <= e["date"] <= cutoff]
    upcoming.sort(key=lambda x: x["date"])
    EVENTS_CACHE = upcoming
    return upcoming


def _fetch_macro_events() -> list:
    try:
        r = requests.get(
            "https://api.fcsapi.com/calendar?type=economic",
            params={"access_key": "demo"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            events = []
            for item in data.get("response", []):
                try:
                    dt = datetime.strptime(item["date"], "%Y-%m-%d %H:%M")
                except:
                    continue
                events.append({
                    "date": dt,
                    "title": item.get("title", item.get("event", "N/A")),
                    "impact": item.get("impact", item.get("volatility", "low")),
                    "country": item.get("country", ""),
                })
            return events
    except:
        pass
    return []


def _default_events() -> list:
    now = datetime.now()
    events = []

    weekdays = []
    for i in range(10):
        d = now + timedelta(days=i)
        weekdays.append(d)

    for d in weekdays:
        wd = d.weekday()

        if wd == 0 and d.hour < 14:
            events.append({"date": d.replace(hour=14, minute=30), "title": "US 10-Year Note Auction", "impact": "medium", "country": "US"})
        if wd == 1:
            pass
        if wd == 2:
            events.append({"date": d.replace(hour=8, minute=30), "title": "US MBA Mortgage Applications", "impact": "low", "country": "US"})
            if d.day >= 1 and d.day <= 7:
                events.append({"date": d.replace(hour=13, minute=30), "title": "US ISM Manufacturing PMI", "impact": "high", "country": "US"})
        if wd == 3:
            events.append({"date": d.replace(hour=8, minute=30), "title": "US Jobless Claims", "impact": "medium", "country": "US"})
            if d.day >= 12 and d.day <= 18:
                events.append({"date": d.replace(hour=8, minute=30), "title": "US CPI (MoM)", "impact": "high", "country": "US"})
        if wd == 4:
            if d.day >= 1 and d.day <= 7:
                events.append({"date": d.replace(hour=8, minute=30), "title": "US Non-Farm Payrolls", "impact": "high", "country": "US"})

        if d.weekday() == 4 and d.hour == 0:
            pass

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_friday = (now.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)
    next_friday = last_friday + timedelta(days=7) if days_since_friday > 0 else today + timedelta(days=(4 - now.weekday()) % 7)

    for d in [now + timedelta(days=i) for i in range(-2, 8)]:
        if d.day in [15, 30, 31] and d.weekday() < 5:
            if d >= now:
                events.append({"date": d.replace(hour=10, minute=0), "title": "Options Expiry / Rebalancing Window", "impact": "medium", "country": "US"})

    return events


def format_events(events: list) -> str:
    if not events:
        return ""
    lines = []
    for e in events:
        impact_map = {"high": "HIGH", "medium": "MED", "low": "low"}
        imp = impact_map.get(e["impact"].lower(), "?")
        day_str = e["date"].strftime("%a %d")
        time_str = e["date"].strftime("%H:%M")
        lines.append(f"  [{imp}] {day_str} {time_str} - {e['title']}")
    return "\n".join(lines)


def get_week_ahead_note() -> str:
    events = get_upcoming_events(7)
    if not events:
        return ""
    high_impact = [e for e in events if e["impact"] == "high"]
    medium_impact = [e for e in events if e["impact"] == "medium"]

    parts = []
    if high_impact:
        parts.append(f"{len(high_impact)} high-impact event(s) this week")
    if medium_impact:
        parts.append(f"{len(medium_impact)} medium-impact event(s)")
    parts.append("Expect increased volatility around these times")

    note = "; ".join(parts)
    details = format_events(events[:5])
    return f"{note}.\n{details}" if details else note

from flask import Flask, render_template
import icalendar
import requests
from datetime import datetime
from collections import defaultdict
import re

app = Flask(__name__)

def parse_ics(ics_url):
    response = requests.get(ics_url, timeout=10)
    calendar = icalendar.Calendar.from_ical(response.text)
    events = []
    for component in calendar.walk():
        if component.name == "VEVENT":
            start_dt = component.get("DTSTART").dt
            start = start_dt.date() if hasattr(start_dt, "date") else start_dt
            raw_description = str(component.get("DESCRIPTION"))
            description_lines = raw_description.splitlines()
            tags = []
            filtered_lines = []
            screenshot_url = None
            for line in description_lines:
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    tags.extend([t.strip() for t in line.strip().split("#") if t.strip()])
                    continue
                m = re.search(r"@?https://gyazo\.com/([A-Za-z0-9]+)", line)
                if m and not screenshot_url:
                    gyazo_id = m.group(1)
                    screenshot_url = f"https://i.gyazo.com/{gyazo_id}.png"
                    continue
                filtered_lines.append(line)
            event = {
                "summary": str(component.get("SUMMARY")),
                "location": str(component.get("LOCATION")),
                "description": "\n".join(filtered_lines).strip(),
                "start": start,
                "tags": tags,
                "screenshot_url": screenshot_url,
            }
            events.append(event)
    events.sort(key=lambda x: x["start"], reverse=True)
    return events

def generate_yearly_calendar(year, events):
    calendar_by_date = defaultdict(list)
    for event in events:
        calendar_by_date[event["start"]].append(event)

    yearly_calendar = defaultdict(lambda: defaultdict(list))
    yearly_counts = defaultdict(int)
    yearly_monthly_counts = defaultdict(lambda: defaultdict(int))
    for date, event_list in calendar_by_date.items():
        year_key = date.year
        month = date.month
        yearly_calendar[year_key][month].append({"date": date, "events": event_list})
        yearly_counts[year_key] += len(event_list)
        yearly_monthly_counts[year_key][month] += len(event_list)

    sorted_yearly_calendar = {}
    for year_key in sorted(yearly_calendar.keys(), reverse=True):
        sorted_yearly_calendar[year_key] = dict(
            sorted(yearly_calendar[year_key].items(), reverse=True)
        )

    sorted_yearly_monthly_counts = {}
    for year_key in sorted(yearly_monthly_counts.keys(), reverse=True):
        sorted_yearly_monthly_counts[year_key] = dict(
            sorted(yearly_monthly_counts[year_key].items(), reverse=True)
        )

    return sorted_yearly_calendar, sorted_yearly_monthly_counts, yearly_counts

@app.route("/")
def index():
    ics_url = "https://calendar.google.com/calendar/ical/3b0cf5c3987b37ec7a28ba13677629e3d21b23c1c5b65e5a2250521ca3157b53%40group.calendar.google.com/private-7b9ec4075feb534a998aa9494a735161/basic.ics"
    events = parse_ics(ics_url)
    yearly_calendar, yearly_monthly_counts, yearly_counts = generate_yearly_calendar(datetime.now().year, events)

    tag_freq = defaultdict(int)
    for event in events:
        for t in event.get("tags", []):
            tag_freq[t] += 1
    sorted_tags = sorted(tag_freq.items(), key=lambda x: (-x[1], x[0]))

    tag_styles = {}
    n_tags = len(sorted_tags) if sorted_tags else 1
    for i, (tag, _cnt) in enumerate(sorted_tags):
        hue = int(round(360 * i / n_tags)) % 360
        bg = f"hsl({hue}, 70%, 90%)"
        fg = f"hsl({hue}, 35%, 30%)"
        tag_styles[tag] = f"background: {bg}; color: {fg};"

    return render_template(
        "index.html",
        yearly_calendar=yearly_calendar,
        yearly_monthly_counts=yearly_monthly_counts,
        yearly_counts=yearly_counts,
        tags=sorted_tags,
        events=events,
        tag_styles=tag_styles,
    )

if __name__ == "__main__":
    app.run(debug=True)

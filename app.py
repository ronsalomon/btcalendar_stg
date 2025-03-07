import os
import json
import calendar
import uuid
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify
from xml.sax.saxutils import escape

app = Flask(__name__)
app.jinja_env.globals.update(datetime=datetime)

EVENTS_FILE = "events.json"

def load_events():
    """Load events from the JSON file. Returns a list of event dictionaries."""
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r") as f:
            try:
                events = json.load(f)
            except json.JSONDecodeError:
                events = []
        return events
    else:
        return []

def save_events(events):
    """Save a list of event dictionaries to the JSON file."""
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=2)


@app.route("/api/events", methods=["GET", "POST"])
def events_api():
    """
    GET: Return all events in JSON.
    POST: Add a new event. Expects JSON with at least "title", "start_date", and "start_time".
    """
    if request.method == "GET":
        events = load_events()
        return jsonify(events)
    elif request.method == "POST":
        data = request.json or {}
        required_fields = ["title", "start_date", "start_time"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field '{field}'"}), 400
        new_event = {
            "title": data["title"],
            "start_date": data["start_date"],
            "start_time": data["start_time"],
            "end_date": data.get("end_date", ""),
            "end_time": data.get("end_time", ""),
            "description": data.get("description", ""),
            "image": data.get("image", "")
        }
        events = load_events()
        events.append(new_event)
        save_events(events)
        return jsonify({"status": "success", "event": new_event}), 201


@app.route("/api/events/date/<date_str>")
def events_by_date(date_str):
    """
    Return events for a specific date in JSON.
    
    :param date_str: Date string in YYYY-MM-DD format
    """
    try:
        # Parse the date string
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Get all events
        all_events = load_events()
        
        # Filter events for the target date
        filtered_events = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                # Skip events with invalid dates
                continue
                
        return jsonify(filtered_events)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400


@app.route("/api/list_events/<date_str>")
def list_events(date_str):
    """
    Returns the events content for a given date.
    If there are no events for the selected day, returns all upcoming events
    (events with a date >= today's date), sorted by date and time.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_events = load_events()
        # First, filter events that occur exactly on the target date.
        filtered_events = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                continue

        # If no events on the selected day, show upcoming events (from today onward).
        if not filtered_events:
            upcoming_events = []
            for event in all_events:
                try:
                    event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                    # Use today's date as the lower bound for upcoming events.
                    if event_date >= date.today():
                        upcoming_events.append(event)
                except (ValueError, KeyError):
                    continue

            # Define a key to sort events by date and time.
            def event_sort_key(ev):
                try:
                    return datetime.strptime(ev["start_date"] + " " + ev["start_time"], "%Y-%m-%d %H:%M")
                except Exception:
                    return datetime.max
            upcoming_events.sort(key=event_sort_key)
            filtered_events = upcoming_events

        return render_template("list_events_fragment.html", events=filtered_events)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400


@app.route("/api/row_events/<date_str>")
def row_events(date_str):
    """
    Returns the events content for a given date.
    If there are no events for the selected day, returns all upcoming events
    (events with a date >= today's date), sorted by date and time.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_events = load_events()
        # First, filter events that occur exactly on the target date.
        filtered_events_row = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events_row.append(event)
            except (ValueError, KeyError):
                continue

        # If no events on the selected day, show upcoming events (from today onward).
        if not filtered_events_row:
            upcoming_events = []
            for event in all_events:
                try:
                    event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                    # Use today's date as the lower bound for upcoming events.
                    if event_date >= date.today():
                        upcoming_events.append(event)
                except (ValueError, KeyError):
                    continue

            # Define a key to sort events by date and time.
            def event_sort_key(ev):
                try:
                    return datetime.strptime(ev["start_date"] + " " + ev["start_time"], "%Y-%m-%d %H:%M")
                except Exception:
                    return datetime.max
            upcoming_events.sort(key=event_sort_key)
            filtered_events_row = upcoming_events

        return render_template("row_events_fragment.html", events=filtered_events_row)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    

@app.route("/api/calendar")
def api_calendar():
    """
    Returns the rendered calendar fragment for a given year and month.
    Query parameters: year and month (defaults to current year and month).
    """
    try:
        year = int(request.args.get('year', date.today().year))
        month = int(request.args.get('month', date.today().month))
    except ValueError:
        year = date.today().year
        month = date.today().month

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)
    
    events = load_events()
    events_by_day = {}
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["start_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if ev_date.year == year and ev_date.month == month:
            events_by_day.setdefault(ev_date.day, []).append(ev)
    
    return render_template("calendar_fragment.html",
                           year=year,
                           month=month,
                           month_name=calendar.month_name[month],
                           month_days=month_days,
                           events_monthly=events_by_day,
                           today=date.today())

@app.route("/")
def index():
    """
    Render the SPA. The header remains static while the content area is swapped on the client side.
    """
    today = date.today()
    year = today.year
    month = today.month

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)

    events = load_events()

    events_by_day = {}
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["start_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if ev_date.year == year and ev_date.month == month:
            events_by_day.setdefault(ev_date.day, []).append(ev)
    
    # Filter events for today's date for initial list view
    today_events = []
    for ev in events:
        try:
            ev_date = datetime.strptime(ev["start_date"], "%Y-%m-%d").date()
            if ev_date == today:
                today_events.append(ev)
        except ValueError:
            continue
    
    display_date = today.strftime("%a, %B %d")
    display_date_iso = today.strftime("%Y-%m-%d")
    return render_template("index.html",
                           year=year,
                           month=month,
                           month_name=calendar.month_name[month],
                           month_days=month_days,
                           events_monthly=events_by_day,
                           today=today,
                           events=today_events,
                           display_date=display_date,
                           display_date_iso=display_date_iso)

@app.route("/calendar.ics")
def download_ics():
    # Get the current year
    current_year = date.today().year
    # Load all events
    events = load_events()
    # Filter events for the current year
    current_year_events = []
    for event in events:
        try:
            event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            if event_date.year == current_year:
                current_year_events.append(event)
        except Exception:
            continue

    # Generate the ICS file content
    ics_content = generate_ics(current_year_events)
    response = app.response_class(ics_content, mimetype='text/calendar')
    response.headers["Content-Disposition"] = f"attachment; filename=calendar_{current_year}.ics"
    return response


def generate_ics(events):
    """
    Generate an ICS file string from a list of event dictionaries.
    """
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//BT Calendar//EN")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    for event in events:
        try:
            # Parse the event's start date and time
            dtstart = datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M")
            dtstart_str = dtstart.strftime("%Y%m%dT%H%M%S")
        except Exception:
            continue  # skip events with invalid date/time
        
        # Determine end date/time if provided; otherwise, default to 1 hour after start
        if event.get("end_date") and event.get("end_time"):
            try:
                dtend = datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M")
            except Exception:
                dtend = dtstart + timedelta(hours=1)
        else:
            dtend = dtstart + timedelta(hours=1)
        dtend_str = dtend.strftime("%Y%m%dT%H%M%S")
        
        # Create a unique ID for the event
        uid = str(uuid.uuid4())
        summary = event.get("title", "No Title")
        # Escape newlines in the description
        description = event.get("description", "").replace("\n", "\\n")
        
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"DTSTART:{dtstart_str}")
        lines.append(f"DTEND:{dtend_str}")
        lines.append(f"SUMMARY:{summary}")
        if description:
            lines.append(f"DESCRIPTION:{description}")
        lines.append("END:VEVENT")
    
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@app.route("/calendar.xml")
def download_xml():
    # Get the current year
    current_year = date.today().year
    # Load all events
    events = load_events()
    # Filter events for the current year
    current_year_events = []
    for event in events:
        try:
            event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            if event_date.year == current_year:
                current_year_events.append(event)
        except Exception:
            continue

    # Generate the XML file content
    xml_content = generate_xml(current_year_events)
    response = app.response_class(xml_content, mimetype='application/xml')
    response.headers["Content-Disposition"] = f"attachment; filename=calendar_{current_year}.xml"
    return response


def generate_xml(events):
    """
    Generate an XML file string from a list of event dictionaries.
    """
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append("<calendar>")
    dtstamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for event in events:
        try:
            # Parse the event's start date and time
            dtstart = datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M")
            dtstart_str = dtstart.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            continue  # skip events with invalid date/time
        
        # Determine end date/time if provided; otherwise, default to 1 hour after start
        if event.get("end_date") and event.get("end_time"):
            try:
                dtend = datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M")
            except Exception:
                dtend = dtstart + timedelta(hours=1)
        else:
            dtend = dtstart + timedelta(hours=1)
        dtend_str = dtend.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create a unique ID for the event
        uid = str(uuid.uuid4())
        summary = escape(event.get("title", "No Title"))
        description = escape(event.get("description", ""))
        
        lines.append("  <event>")
        lines.append(f"    <uid>{uid}</uid>")
        lines.append(f"    <dtstamp>{dtstamp}</dtstamp>")
        lines.append(f"    <dtstart>{dtstart_str}</dtstart>")
        lines.append(f"    <dtend>{dtend_str}</dtend>")
        lines.append(f"    <summary>{summary}</summary>")
        if description:
            lines.append(f"    <description>{description}</description>")
        lines.append("  </event>")
    
    lines.append("</calendar>")
    return "\n".join(lines)

if __name__ == "__main__":
    app.run(debug=True)
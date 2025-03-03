import os
import json
import calendar
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify

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
    Returns ONLY the events content for a given date, not the entire fragment.
    
    :param date_str: Date string in YYYY-MM-DD format
    """
    try:
        # Parse the date string
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Get filtered events
        all_events = load_events()
        filtered_events = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                # Skip events with invalid dates
                continue
        
        # Return just the events HTML, not the entire fragment
        return render_template("list_events_fragment.html",
                           events=filtered_events)
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

if __name__ == "__main__":
    app.run(debug=True)
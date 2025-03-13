import os
import calendar
import uuid
import psycopg2
import requests
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from xml.sax.saxutils import escape
from flask import Response
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import httpx
import pytz
from dotenv import load_dotenv


# Load environment variables from .env (if available)
load_dotenv()

app = Flask(__name__)
app.jinja_env.globals.update(datetime=datetime)

# Use the provided Render PostgreSQL URL, or override via DATABASE_URL environment variable.
DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------
# Database functions
# --------------------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Initialize the database by creating the events table if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            asana_task_gid TEXT,
            event_status TEXT,
            ministry TEXT,
            organizer TEXT,
            website_trigger TEXT,
            registration TEXT,
            title TEXT NOT NULL,
            start_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_date DATE,
            end_time TIME,
            location TEXT,
            description TEXT,
            image TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_events():
    """Load all events from the database and return them as a list of dictionaries."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT asana_task_gid, event_status, ministry, organizer, website_trigger, registration, title,
               start_date, start_time, end_date, end_time, location, description, image, image_url,
               CASE WHEN image_data IS NOT NULL THEN true ELSE false END as image_data
        FROM events
    """)
    rows = cur.fetchall()
    events = []
    for row in rows:
        events.append({
            "asana_task_gid": row[0],
            "event_status": row[1],
            "ministry": row[2],
            "organizer": row[3],
            "website_trigger": row[4],
            "registration": row[5],
            "title": row[6],
            "start_date": row[7].strftime("%Y-%m-%d") if row[7] else "",
            "start_time": row[8].strftime("%H:%M") if row[8] else "",
            "end_date": row[9].strftime("%Y-%m-%d") if row[9] else "",
            "end_time": row[10].strftime("%H:%M") if row[10] else "",
            "location": row[11],
            "description": row[12],
            "image": row[13],
            "image_url": row[14],
            "image_data": row[15]
        })
    cur.close()
    conn.close()
    return events


@app.route('/event_image/<event_id>')
def event_image(event_id):
    """Serve an event image directly from the database."""
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Debug info
        print(f"Fetching image for event ID: {event_id}")
        
        # Use simple binary data selection to avoid encoding issues
        cur.execute("SELECT image_data FROM events WHERE asana_task_gid = %s", (event_id,))
        result = cur.fetchone()
        
        if result and result[0]:  # If image data exists
            # Debug info
            print(f"Found image data for event ID {event_id}: {len(result[0])} bytes")
            
            # Default to JPEG content type
            content_type = 'image/jpeg'
            
            # Serve the image directly from the database
            return Response(result[0], mimetype=content_type)
        else:
            # Debug info
            print(f"No image data found for event ID: {event_id}")
            return '', 404  # Not found
    except Exception as e:
        print(f"Error serving image: {e}")
        return '', 500  # Server error
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def add_event(event):
    """Insert a new event into the database and return the inserted event with its new id."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Prepare image_data for database insertion if it exists
    image_data = None
    if "image_data" in event and event["image_data"]:
        image_data = psycopg2.Binary(event["image_data"])
        
    cur.execute("""
         INSERT INTO events (
             asana_task_gid, event_status, ministry, organizer, website_trigger, registration, title,
             start_date, start_time, end_date, end_time, location, description, image, image_url, image_data
         )
         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
         RETURNING id
    """, (
         event.get("asana_task_gid"),
         event.get("event_status"),
         event.get("ministry"),
         event.get("organizer"),
         event.get("website_trigger"),
         event.get("registration"),
         event.get("title"),
         event.get("start_date"),
         event.get("start_time"),
         event.get("end_date"),
         event.get("end_time"),
         event.get("location"),
         event.get("description"),
         event.get("image"),
         event.get("image_url"),
         image_data
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    event["id"] = new_id
    return event


def event_exists(asana_task_gid):
    """Check if an event with the given Asana task gid exists."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events WHERE asana_task_gid = %s", (asana_task_gid,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count > 0

def get_event(asana_task_gid):
    """Retrieve an event record by its asana_task_gid."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT asana_task_gid, event_status, ministry, organizer, website_trigger, registration, title,
               to_char(start_date, 'YYYY-MM-DD'), to_char(start_time, 'HH24:MI'),
               to_char(end_date, 'YYYY-MM-DD'), to_char(end_time, 'HH24:MI'),
               location, description, image, image_url,
               CASE WHEN image_data IS NOT NULL THEN true ELSE false END as has_image_data
        FROM events WHERE asana_task_gid = %s
    """, (asana_task_gid,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {
            "asana_task_gid": row[0],
            "event_status": row[1],
            "ministry": row[2],
            "organizer": row[3],
            "website_trigger": row[4],
            "registration": row[5],
            "title": row[6],
            "start_date": row[7],
            "start_time": row[8],
            "end_date": row[9],
            "end_time": row[10],
            "location": row[11],
            "description": row[12],
            "image": row[13],
            "image_url": row[14],
            "image_data": row[15]  # This is just a boolean indicating presence of image data
        }
    return None

def sanitize_html(html_content):
    """Sanitize HTML content to remove dangerous tags and attributes."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, iframe, and other potentially dangerous tags
    for tag in soup.find_all(['script', 'iframe', 'embed', 'object']):
        tag.decompose()
    
    # Remove on* attributes (onclick, onload, etc.)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith('on'):
                del tag[attr]
    
    return str(soup)


def update_event(event):
    """Update an existing event in the database based on asana_task_gid."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Prepare image_data for database insertion if it exists
    image_data = None
    if "image_data" in event and event["image_data"]:
        image_data = psycopg2.Binary(event["image_data"])
        
    cur.execute("""
         UPDATE events
         SET event_status = %s,
             ministry = %s,
             organizer = %s,
             website_trigger = %s,
             registration = %s,
             title = %s,
             start_date = %s,
             start_time = %s,
             end_date = %s,
             end_time = %s,
             location = %s,
             description = %s,
             image = %s,
             image_url = %s,
             image_data = %s
         WHERE asana_task_gid = %s
         RETURNING id
    """, (
         event.get("event_status"),
         event.get("ministry"),
         event.get("organizer"),
         event.get("website_trigger"),
         event.get("registration"),
         event.get("title"),
         event.get("start_date"),
         event.get("start_time"),
         event.get("end_date"),
         event.get("end_time"),
         event.get("location"),
         event.get("description"),
         event.get("image"),
         event.get("image_url"),
         image_data,
         event.get("asana_task_gid")
    ))
    updated_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    event["id"] = updated_id
    return event

# --------------------------
# Cancellation adjustment helper
# --------------------------
def adjust_for_cancellation(event):
    """
    If the event's Website Trigger is 'Unpublish', prepend 'CANCELED: ' to the title
    and add a cancellation message at the top of the description.
    Otherwise, remove these modifications if present.
    """
    cancellation_message = "THIS EVENT HAS BEEN CANCELED"
    should_cancel = (event.get("website_trigger") == "Unpublish")
    
    if should_cancel:
        if not event["title"].startswith("CANCELED: "):
            event["title"] = "CANCELED: " + event["title"]
        if not event["description"].lstrip().startswith(cancellation_message):
            event["description"] = cancellation_message + "\n\n" + event["description"]
    else:
        if event["title"].startswith("CANCELED: "):
            event["title"] = event["title"][len("CANCELED: "):]
        if event["description"].lstrip().startswith(cancellation_message):
            lines = event["description"].splitlines()
            if lines and lines[0].strip() == cancellation_message:
                if len(lines) > 1 and lines[1].strip() == "":
                    event["description"] = "\n".join(lines[2:]).strip()
                else:
                    event["description"] = "\n".join(lines[1:]).strip()
    return event

# --------------------------
# Asana Functions
# --------------------------
async def fetch_tasks_from_asana():
    bearer_token = os.getenv('ASANA_TOKEN')
    project_gid = os.getenv('ASANA_DEMO_PROJECT_ID')
    if not bearer_token or not project_gid:
        print("ASANA_TOKEN or ASANA_DEMO_PROJECT_ID not set.")
        return []
    asana_url = f"https://app.asana.com/api/1.0/projects/{project_gid}/tasks"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {bearer_token}"
    }
    params = {
        "limit": 100,
        "opt_fields": "name,projects.gid,projects.name,custom_fields.gid,custom_fields.name,custom_fields.display_value,due_on"
    }
    all_tasks = []
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(asana_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            tasks = data.get("data", [])
            all_tasks.extend(tasks)
            next_page = data.get("next_page")
            if next_page and next_page.get("offset"):
                params["offset"] = next_page["offset"]
            else:
                break
    return all_tasks

def sanitize_html(html_content):
    """Sanitize HTML content to remove dangerous tags and attributes."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, iframe, and other potentially dangerous tags
    for tag in soup.find_all(['script', 'iframe', 'embed', 'object']):
        tag.decompose()
    
    # Remove on* attributes (onclick, onload, etc.)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith('on'):
                del tag[attr]
    
    return str(soup)

def process_asana_tasks():
    try:
        tasks = asyncio.run(fetch_tasks_from_asana())
        print(f"[DEBUG] Fetched {len(tasks)} tasks from Asana")
        
        # Get the current year
        current_year = datetime.now().year
        print(f"[DEBUG] Filtering for events in {current_year}")
        
        def get_cf(task, field_name):
            for cf in task.get("custom_fields", []):
                if cf.get("name") == field_name:
                    return cf.get("display_value", "")
            return ""
        
        added_count = 0
        skipped_count = 0
        for task in tasks:
            asana_task_gid = task.get("gid")
            if not asana_task_gid:
                continue
            
            title = task.get("name", "Unnamed Task")
            due_on = task.get("due_on")
            start_date = due_on if due_on else datetime.now().strftime("%Y-%m-%d")
            
            # Skip events not in the current year
            try:
                event_year = datetime.strptime(start_date, "%Y-%m-%d").year
                if event_year != current_year:
                    print(f"[DEBUG] Skipping event {title} from year {event_year}")
                    skipped_count += 1
                    continue
            except ValueError:
                print(f"[DEBUG] Couldn't parse date for event {title}, using default")
                
            # Check if the event already exists before proceeding
            if event_exists(asana_task_gid):
                print(f"[DEBUG] Event {title} already exists, skipping")
                skipped_count += 1
                continue
                
            start_time = "09:00"
            end_time = "10:00"
            
            event_status    = get_cf(task, "Event Status") or "Approved"
            ministry        = get_cf(task, "Ministry") or ""
            organizer       = ministry or "Asana Import"
            website_trigger = get_cf(task, "Website Trigger") or "Publish"
            registration    = get_cf(task, "Registration") or ""
            description     = get_cf(task, "Content") or title
            
            # Apply HTML sanitization AFTER description is defined
            description = sanitize_html(description)
            
            image           = get_cf(task, "Graphics") or ""
            location        = get_cf(task, "Locations") or ""
            
            if "dropbox.com" in image and "dl=0" in image:
                image = image.replace("dl=0", "raw=1")
            
            location = location.strip()
            if location.startswith("17 -"):
                location = "17 Smith Street"
            elif location.startswith("163"):
                location = "163 Livingston Street"
            elif location.startswith("392"):
                location = "392 Fulton Street"
            elif location.startswith("190"):
                location = "190 Livingston Street"
            
            # Download image if URL exists
            image_data = None
            image_url = image
            if image:
                try:
                    print(f"[DEBUG] Downloading image from {image}")
                    # Add a user-agent header to mimic a browser
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(image, timeout=15, headers=headers)
                    response.raise_for_status()
                    image_data = response.content
                    print(f"[DEBUG] Downloaded image: {len(image_data)} bytes")
                    
                    # Verify that we actually got an image
                    if len(image_data) < 100:
                        print(f"[WARNING] Downloaded file seems too small to be an image ({len(image_data)} bytes)")
                        image_data = get_placeholder_image()
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403:
                        print(f"[DEBUG] Access forbidden to image: {image}. Using placeholder.")
                        image_data = get_placeholder_image()
                    else:
                        print(f"[DEBUG] HTTP error downloading image: {e}")
                        image_data = get_placeholder_image()
                except Exception as e:
                    print(f"[DEBUG] Error downloading image: {e}")
                    image_data = get_placeholder_image()
            
            new_event = {
                "asana_task_gid": asana_task_gid,
                "event_status": event_status,
                "ministry": ministry,
                "organizer": organizer,
                "website_trigger": website_trigger,
                "registration": registration,
                "title": title,
                "start_date": start_date,
                "start_time": start_time,
                "end_date": start_date,
                "end_time": end_time,
                "location": location,
                "description": description,
                "image": image,
                "image_url": image_url,
                "image_data": image_data
            }
            
            new_event = adjust_for_cancellation(new_event)
            
            # Only add the event if it doesn't exist
            add_event(new_event)
            added_count += 1
            print(f"[DEBUG] Inserted event for task: {new_event['title']}")
                
        print(f"[DEBUG] Asana sync complete. Added: {added_count}, Skipped: {skipped_count}")
    except Exception as e:
        print("Error processing Asana tasks:", e)


def start_asana_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_asana_tasks, 'interval', seconds=60, max_instances=1)
    scheduler.start()

# --------------------------
# Flask Routes
# --------------------------
@app.route("/api/events", methods=["GET", "POST"])
def events_api():
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
            "asana_task_gid": data.get("asana_task_gid"),
            "event_status": data.get("event_status"),
            "ministry": data.get("ministry"),
            "website_trigger": data.get("website_trigger"),
            "registration": data.get("registration"),
            "title": data["title"],
            "start_date": data["start_date"],
            "start_time": data["start_time"],
            "end_date": data.get("end_date", None),
            "end_time": data.get("end_time", None),
            "description": data.get("description", ""),
            "image": data.get("image", ""),
            "location": data.get("location", "")
        }
        added_event = add_event(new_event)
        return jsonify({"status": "success", "event": added_event}), 201


@app.route("/api/events/date/<date_str>")
def events_by_date(date_str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_events = load_events()
        filtered_events = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                continue
        return jsonify(filtered_events)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400


@app.route("/api/list_events/<date_str>")
def list_events(date_str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_events = load_events()
        filtered_events = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events.append(event)
            except (ValueError, KeyError):
                continue

        if not filtered_events:
            upcoming_events = []
            for event in all_events:
                try:
                    event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                    if event_date >= date.today():
                        upcoming_events.append(event)
                except (ValueError, KeyError):
                    continue

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
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        all_events = load_events()
        filtered_events_row = []
        for event in all_events:
            try:
                event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                if event_date == target_date:
                    filtered_events_row.append(event)
            except (ValueError, KeyError):
                continue

        if not filtered_events_row:
            upcoming_events = []
            for event in all_events:
                try:
                    event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
                    if event_date >= date.today():
                        upcoming_events.append(event)
                except (ValueError, KeyError):
                    continue

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
                           display_date_iso=display_date_iso,
                           default_view="calendar")

@app.route("/calendar.ics")
def download_ics():
    current_year = date.today().year
    events = load_events()
    current_year_events = []
    for event in events:
        try:
            event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            if event_date.year == current_year:
                current_year_events.append(event)
        except Exception:
            continue
    ics_content = generate_ics(current_year_events)
    response = app.response_class(ics_content, mimetype='text/calendar')
    response.headers["Content-Disposition"] = f"attachment; filename=calendar_{current_year}.ics"
    return response

def generate_ics(events):
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//BT Calendar//EN")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for event in events:
        try:
            dtstart = datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M")
            dtstart_str = dtstart.strftime("%Y%m%dT%H%M%S")
        except Exception:
            continue
        if event.get("end_date") and event.get("end_time"):
            try:
                dtend = datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M")
            except Exception:
                dtend = dtstart + timedelta(hours=1)
        else:
            dtend = dtstart + timedelta(hours=1)
        dtend_str = dtend.strftime("%Y%m%dT%H%M%S")
        uid = str(uuid.uuid4())
        summary = event.get("title", "No Title")
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
    current_year = date.today().year
    events = load_events()
    current_year_events = []
    for event in events:
        try:
            event_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            if event_date.year == current_year:
                current_year_events.append(event)
        except Exception:
            continue
    xml_content = generate_xml(current_year_events)
    response = app.response_class(xml_content, mimetype='application/xml')
    response.headers["Content-Disposition"] = f"attachment; filename=calendar_{current_year}.xml"
    return response

def generate_xml(events):
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append("<calendar>")
    dtstamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for event in events:
        try:
            dtstart = datetime.strptime(f"{event['start_date']} {event['start_time']}", "%Y-%m-%d %H:%M")
            dtstart_str = dtstart.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            continue
        if event.get("end_date") and event.get("end_time"):
            try:
                dtend = datetime.strptime(f"{event['end_date']} {event['end_time']}", "%Y-%m-%d %H:%M")
            except Exception:
                dtend = dtstart + timedelta(hours=1)
        else:
            dtend = dtstart + timedelta(hours=1)
        dtend_str = dtend.strftime("%Y-%m-%dT%H:%M:%S")
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

@app.route('/<view>')
def spa(view):
    if view not in ['modern_row', 'modern_list', 'calendar']:
        view = 'calendar'
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
                           display_date_iso=display_date_iso,
                           default_view=view)

@app.route("/trigger-asana")
def trigger_asana():
    process_asana_tasks()
    return "Asana tasks processed"

def start_asana_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_asana_tasks, 'interval', seconds=60, max_instances=1)
    scheduler.start()

if __name__ == "__main__":
    init_db()
    if os.getenv('ASANA_TOKEN') and os.getenv('ASANA_DEMO_PROJECT_ID'):
        start_asana_scheduler()
    app.run(debug=True, threaded=False)

    serve(app, host="127.0.0.1", port=5000)

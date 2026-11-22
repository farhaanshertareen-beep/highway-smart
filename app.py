import streamlit as st
import sqlite3
import requests
import json
import hashlib
import secrets
import urllib.parse
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit.components.v1 as components

DB = Path(__file__).with_name("highway_alerts.db")
API = "https://api.open-meteo.com/v1/forecast"

# Balochistan Highway Corridors with coordinates, elevation, and verified alternative routes
ROUTES_DATA = {
    "Quetta–Karachi (N-25)": {
        "code": "N-25",
        "distance": "688 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Sukkur → Karachi (N-5/M-9) [All-Weather Bypass]",
        "alt_reason": "Avoids Kalat/Surab snow & Khuzdar/Wadh flash-flood gorges via low-elevation Indus Highway.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Mastung", "lat": 29.7997, "lon": 66.8455, "elevation": "1,701m"},
            {"name": "Kalat", "lat": 29.0266, "lon": 66.5936, "elevation": "2,007m"},
            {"name": "Surab", "lat": 28.4914, "lon": 66.2585, "elevation": "1,750m"},
            {"name": "Khuzdar", "lat": 27.8000, "lon": 66.6167, "elevation": "1,237m"},
            {"name": "Wadh", "lat": 27.3436, "lon": 66.3708, "elevation": "1,220m"},
            {"name": "Lasbela", "lat": 26.2289, "lon": 66.3106, "elevation": "87m"},
            {"name": "Hub", "lat": 25.0244, "lon": 66.8906, "elevation": "24m"},
        ]
    },
    "Quetta–Zhob (N-50)": {
        "code": "N-50",
        "distance": "331 km",
        "alt_route": "Quetta → Ziarat Cross → Loralai (N-70) → Mekhtar → Zhob Link Road",
        "alt_reason": "Bypasses Khan Mehtarzai (2,224m) snow/blizzard pass via lower Loralai valley.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khan Mehtarzai", "lat": 30.4833, "lon": 67.6167, "elevation": "2,224m"},
            {"name": "Muslim Bagh", "lat": 30.8317, "lon": 67.7408, "elevation": "1,787m"},
            {"name": "Qilla Saifullah", "lat": 30.7000, "lon": 68.3600, "elevation": "1,550m"},
            {"name": "Zhob", "lat": 31.3411, "lon": 69.4481, "elevation": "1,426m"},
        ]
    },
    "Quetta–Sibi (N-65)": {
        "code": "N-65",
        "distance": "163 km",
        "alt_route": "Quetta → Harnai → Shahrag → Sibi (via Ziarat-Harnai Corridor)",
        "alt_reason": "Alternative detour when Kolpur/Bolan Pass experiences rockslides or flash flooding.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kolpur (Bolan Pass)", "lat": 29.9000, "lon": 67.1500, "elevation": "1,790m"},
            {"name": "Mach", "lat": 29.8637, "lon": 67.3302, "elevation": "1,006m"},
            {"name": "Dhadar", "lat": 29.4749, "lon": 67.6514, "elevation": "132m"},
            {"name": "Sibi", "lat": 29.5430, "lon": 67.8773, "elevation": "130m"},
        ]
    },
    "Quetta–Chaman (N-25 North)": {
        "code": "N-25N",
        "distance": "125 km",
        "alt_route": "Quetta → Kuchlak → Pishin → Gulistan → Boghra Pass → Chaman",
        "alt_reason": "Bypasses Khojak Pass (2,290m) during heavy snow or dense winter fog.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Kuchlak", "lat": 30.3125, "lon": 67.0114, "elevation": "1,560m"},
            {"name": "Khojak Pass (Shelabagh)", "lat": 30.8050, "lon": 66.5680, "elevation": "2,290m"},
            {"name": "Chaman", "lat": 30.9177, "lon": 66.4526, "elevation": "1,338m"},
        ]
    },
    "Quetta–Nushki–Taftan (N-40)": {
        "code": "N-40",
        "distance": "610 km",
        "alt_route": "Quetta → Mastung → Khuzdar → Basima → Washuk → Dalbandin Link",
        "alt_reason": "Alternative southern detour if Lakpass tunnel or Nushki sandstorms block N-40.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Lakpass", "lat": 29.9650, "lon": 66.8200, "elevation": "1,810m"},
            {"name": "Nushki", "lat": 29.5522, "lon": 66.0215, "elevation": "1,020m"},
            {"name": "Dalbandin", "lat": 28.8885, "lon": 64.4062, "elevation": "843m"},
            {"name": "Nok Kundi", "lat": 28.8261, "lon": 62.7489, "elevation": "680m"},
            {"name": "Taftan", "lat": 28.9667, "lon": 61.5833, "elevation": "910m"},
        ]
    },
    "Quetta–Loralai–DG Khan (N-70)": {
        "code": "N-70",
        "distance": "425 km",
        "alt_route": "Quetta → Sibi (N-65) → Jacobabad → Kashmore → Rajanpur → DG Khan (N-55)",
        "alt_reason": "Safe lowland Indus Highway alternative during Fort Munro / Rakhni hill-torrent closures.",
        "points": [
            {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": "1,680m"},
            {"name": "Ziarat Cross", "lat": 30.3824, "lon": 67.7256, "elevation": "2,450m"},
            {"name": "Sanjawi", "lat": 30.2856, "lon": 68.3489, "elevation": "1,620m"},
            {"name": "Loralai", "lat": 30.3705, "lon": 68.5979, "elevation": "1,430m"},
            {"name": "Rakhni", "lat": 30.0683, "lon": 69.9214, "elevation": "1,110m"},
        ]
    },
}

# Verified Roadside Emergency & Safe-Haven Facilities across Balochistan Corridors
NEARBY_FACILITIES = [
    {"route": "Quetta–Karachi (N-25)", "sector": "Quetta", "type": "Hospital / Trauma", "name": "Bolan Medical Complex (BMC) Trauma Center", "lat": 30.1845, "lon": 66.9680, "phone": "081-9213030", "notes": "24/7 Emergency & Ambulance"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Mastung", "type": "Safe Rest Area", "name": "Mastung NHA Toll Plaza & Safe Haven", "lat": 29.8050, "lon": 66.8500, "phone": "130 (NHA)", "notes": "Illuminated heavy-vehicle parking & Levies post"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Kalat", "type": "Hospital / Trauma", "name": "DHQ Hospital Kalat Emergency Wing", "lat": 29.0290, "lon": 66.5910, "phone": "0844-210222", "notes": "24/7 Trauma & Cold-Weather Medical Aid"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Surab", "type": "Petrol / Fuel", "name": "PSO Highway Fuel & Tire Station Surab", "lat": 28.4940, "lon": 66.2610, "phone": "0844-410115", "notes": "24/7 Diesel, Petrol & Heavy Truck Air"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Hospital / Trauma", "name": "Teaching Hospital Khuzdar Trauma Unit", "lat": 27.8040, "lon": 66.6120, "phone": "0848-412555", "notes": "Regional Trauma & Rescue 1122 Base"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Khuzdar", "type": "Repair Workshop", "name": "Al-Baloch Heavy Truck & Engine Workshop", "lat": 27.7950, "lon": 66.6210, "phone": "0333-7891102", "notes": "24/7 Crane, Brake & Axle Recovery"},
    {"route": "Quetta–Karachi (N-25)", "sector": "Lasbela", "type": "Safe Rest Area", "name": "Uthal Highway Rest Stop & Fuel Complex", "lat": 25.8070, "lon": 66.6210, "phone": "0853-610400", "notes": "Safe overnight parking, mosque & diner"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Khan Mehtarzai", "type": "Safe Rest Area", "name": "PDMA Snow Shelter & Levies Post", "lat": 30.4850, "lon": 67.6190, "phone": "1122 / PDMA", "notes": "Heated shelter, snow-clearing machinery"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Qilla Saifullah", "type": "Hospital / Trauma", "name": "DHQ Hospital Qilla Saifullah", "lat": 30.7040, "lon": 68.3580, "phone": "0823-610333", "notes": "24/7 Emergency Ward"},
    {"route": "Quetta–Zhob (N-50)", "sector": "Zhob", "type": "Petrol / Fuel", "name": "Shell / Attock Highway Station Zhob", "lat": 31.3390, "lon": 69.4450, "phone": "0822-412890", "notes": "Fuel, mechanic & safe parking"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Kolpur (Bolan Pass)", "type": "Safe Rest Area", "name": "Kolpur Levies & NHA Checkpoint Safe Zone", "lat": 29.9030, "lon": 67.1520, "phone": "130 (NHA)", "notes": "Mandatory convoy hold area during rain"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Mach", "type": "Hospital / Trauma", "name": "Civil Hospital Mach & Rescue 1122 Post", "lat": 29.8650, "lon": 67.3320, "phone": "0832-210112", "notes": "Bolan Pass emergency medical response"},
    {"route": "Quetta–Sibi (N-65)", "sector": "Sibi", "type": "Repair Workshop", "name": "Sibi Grand Trunk Heavy Auto Workshop", "lat": 29.5450, "lon": 67.8750, "phone": "0833-412770", "notes": "Radiator, AC & heavy truck recovery"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Khojak Pass (Shelabagh)", "type": "Safe Rest Area", "name": "Shelabagh Tunnel Safety & Recovery Post", "lat": 30.8070, "lon": 66.5660, "phone": "130 / Levies", "notes": "Snow chains & emergency towing"},
    {"route": "Quetta–Chaman (N-25 North)", "sector": "Chaman", "type": "Hospital / Trauma", "name": "DHQ Hospital Chaman Emergency", "lat": 30.9190, "lon": 66.4540, "phone": "0826-613222", "notes": "24/7 Trauma & Ambulance"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Nushki", "type": "Hospital / Trauma", "name": "DHQ Hospital Nushki", "lat": 29.5550, "lon": 66.0240, "phone": "0825-871444", "notes": "24/7 Emergency & Heatstroke Unit"},
    {"route": "Quetta–Nushki–Taftan (N-40)", "sector": "Dalbandin", "type": "Petrol / Fuel", "name": "PSO RCD Highway Fuel & Rest Complex", "lat": 28.8900, "lon": 64.4090, "phone": "0825-210300", "notes": "Desert transit safe haven & water"},
    {"route": "Quetta–Loralai–DG Khan (N-70)", "sector": "Loralai", "type": "Hospital / Trauma", "name": "Teaching Hospital Loralai", "lat": 30.3720, "lon": 68.5990, "phone": "0824-660555", "notes": "24/7 Trauma & Surgical Unit"},
]

ROUTES = list(ROUTES_DATA.keys())
LANGUAGES = ["Urdu", "English", "Pashto", "Balochi"]
ROAD_STATUSES = ["Open (Verified)", "Restricted — Caution", "Closed — Emergency", "Clearance Pending"]
SOS_TYPES = ["Accident / Collision", "Vehicle Breakdown", "Medical Emergency", "Stranded in Weather / Flood"]

st.set_page_config(
    page_title="Balochistan Smart Highway Watch | Safety & Monitoring",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOGO_PATH = Path(__file__).with_name("logo.png")

@st.cache_data(show_spinner=False)
def get_logo_b64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return ""

def logo_svg(size=46):
    b64 = get_logo_b64()
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:{size}px;height:{size}px;object-fit:cover;border-radius:12px;'
            f'border:1px solid rgba(56,189,248,0.38);box-shadow:0 4px 14px rgba(0,0,0,0.45);" '
            f'alt="Highway Watch Logo"/>'
        )
    return ""

def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    if not stored_hash:
        return (False, False)
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$", 2)
        if len(parts) != 3:
            return (False, False)
        _, salt, expected_hex = parts
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return (secrets.compare_digest(dk.hex(), expected_hex), False)
    legacy_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if secrets.compare_digest(legacy_hex, stored_hash):
        return (True, True)
    return (False, False)

def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username))

def is_valid_pk_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone.strip())
    return bool(re.fullmatch(r"(\+92|0092|0)?3\d{9}", cleaned))

def is_valid_plate(plate: str) -> bool:
    cleaned = re.sub(r"\s+", "", plate.strip().upper())
    return bool(re.fullmatch(r"[A-Z]{2,5}-?\d{2,4}[A-Z]?", cleaned))

def connect():
    con = sqlite3.connect(DB, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with connect() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            department TEXT DEFAULT 'PDMA / NHA Operations',
            role TEXT DEFAULT 'Control Room Operator',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            vehicle_type TEXT DEFAULT 'Heavy Transport',
            route TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT DEFAULT 'Active on Route',
            current_sector TEXT DEFAULT 'Quetta',
            next_checkpoint TEXT DEFAULT 'Mastung',
            expected_eta TEXT,
            last_checkin TEXT,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            route TEXT NOT NULL,
            location TEXT NOT NULL,
            officer_incharge TEXT DEFAULT 'Duty Officer',
            qr_scans INTEGER DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS road_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            area TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_score INTEGER DEFAULT 2,
            authority_note TEXT NOT NULL,
            verified_by TEXT DEFAULT 'Control Room Quetta',
            updated_at TEXT NOT NULL,
            UNIQUE(route, area))""")
        con.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            route TEXT NOT NULL,
            language TEXT DEFAULT 'Urdu',
            severity TEXT DEFAULT 'Advisory',
            message TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sos_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sos_code TEXT UNIQUE,
            driver_id INTEGER,
            driver_name TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            phone TEXT NOT NULL,
            route TEXT NOT NULL,
            sector TEXT NOT NULL,
            lat REAL,
            lon REAL,
            emergency_type TEXT NOT NULL,
            source TEXT DEFAULT 'Driver SOS Button',
            details TEXT,
            status TEXT DEFAULT 'ACTIVE SOS',
            dispatched_unit TEXT DEFAULT 'Pending Dispatch',
            created_at TEXT NOT NULL,
            FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL)""")

        existing_cols = {
            "drivers": [r[1] for r in con.execute("PRAGMA table_info(drivers)").fetchall()],
            "checkpoints": [r[1] for r in con.execute("PRAGMA table_info(checkpoints)").fetchall()],
            "road_status": [r[1] for r in con.execute("PRAGMA table_info(road_status)").fetchall()],
            "alerts": [r[1] for r in con.execute("PRAGMA table_info(alerts)").fetchall()],
        }
        migrations = [
            ("drivers", "driver_code", "TEXT"),
            ("drivers", "vehicle_type", "TEXT DEFAULT 'Heavy Transport'"),
            ("drivers", "status", "TEXT DEFAULT 'Active on Route'"),
            ("drivers", "current_sector", "TEXT DEFAULT 'Quetta'"),
            ("drivers", "next_checkpoint", "TEXT DEFAULT 'Mastung'"),
            ("drivers", "expected_eta", "TEXT"),
            ("drivers", "last_checkin", "TEXT"),
            ("checkpoints", "code", "TEXT"),
            ("checkpoints", "officer_incharge", "TEXT DEFAULT 'Duty Officer'"),
            ("checkpoints", "qr_scans", "INTEGER DEFAULT 0"),
            ("road_status", "risk_score", "INTEGER DEFAULT 2"),
            ("road_status", "verified_by", "TEXT DEFAULT 'Control Room Quetta'"),
            ("alerts", "language", "TEXT DEFAULT 'Urdu'"),
            ("alerts", "severity", "TEXT DEFAULT 'Advisory'"),
        ]
        for tbl, col, col_def in migrations:
            if col not in existing_cols[tbl]:
                con.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")

        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_road_route_area ON road_status(route, area)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_code ON drivers(driver_code)")

def rows(q, p=()):
    with connect() as con:
        return [dict(x) for x in con.execute(q, p).fetchall()]

def run(q, p=()):
    with connect() as con:
        cur = con.execute(q, p)
        con.commit()
        return cur.lastrowid

def seed():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    if not rows("SELECT id FROM users LIMIT 1"):
        run(
            "INSERT OR IGNORE INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
            ("Quetta Control Admin", "admin", "PDMA / NHA Balochistan", "Chief Command Officer", hash_password("admin123"), now_str)
        )
    if not rows("SELECT id FROM checkpoints LIMIT 1"):
        idx = 101
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                run(
                    "INSERT OR IGNORE INTO checkpoints(code,name,route,location,officer_incharge,qr_scans) VALUES(?,?,?,?,?,?)",
                    (f"CP-{idx}", f"{pt['name']} Highway Gate", route, pt["name"], "Levies / NHA Post", idx % 47 + 12)
                )
                idx += 1
    if not rows("SELECT id FROM road_status LIMIT 1"):
        for route, rdata in ROUTES_DATA.items():
            for pt in rdata["points"]:
                default_status = "Open (Verified)"
                default_risk = 2
                note = "Normal traffic flow; regular patrol active."
                if "Khan Mehtarzai" in pt["name"] or "Khojak" in pt["name"]:
                    default_status = "Restricted — Caution"
                    default_risk = 6
                    note = "High altitude pass; strong crosswinds & low night visibility."
                elif "Kolpur" in pt["name"]:
                    default_status = "Open (Verified)"
                    default_risk = 4
                    note = "Bolan sector clear; watch for slippery bends."
                run(
                    "INSERT OR IGNORE INTO road_status(route,area,status,risk_score,authority_note,verified_by,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (route, pt["name"], default_status, default_risk, note, "PDMA / NHA Control Room", now_str)
                )
    if not rows("SELECT id FROM drivers LIMIT 1"):
        future_eta = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        overdue_eta = (now - timedelta(minutes=38)).strftime("%Y-%m-%d %H:%M")
        sample_drivers = [
            ("BHW-2401", "Haji Abdul Wahid", "0300-8381920", "QTA-4821", "Cargo Truck", "Quetta–Karachi (N-25)", "Urdu", "Active on Route", "Mastung", "Kalat", future_eta, now_str),
            ("BHW-2402", "Sardar Khan Kakar", "0333-7812094", "ZHB-1190", "Passenger Coach", "Quetta–Zhob (N-50)", "Pashto", "Overdue — Welfare Check", "Khan Mehtarzai", "Muslim Bagh", overdue_eta, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")),
            ("BHW-2403", "Mirwais Baloch", "0321-8904412", "KZD-7734", "Oil Tanker", "Quetta–Nushki–Taftan (N-40)", "Balochi", "Verified at Gate", "Nushki", "Dalbandin", future_eta, now_str),
            ("BHW-2404", "Noor Muhammad", "0312-9045123", "SIB-3092", "Pickup / Utility", "Quetta–Sibi (N-65)", "Urdu", "Active on Route", "Kolpur (Bolan Pass)", "Mach", future_eta, now_str),
        ]
        for d in sample_drivers:
            run(
                """INSERT OR IGNORE INTO drivers
                (driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*d, now_str)
            )
    if not rows("SELECT id FROM sos_incidents LIMIT 1"):
        run(
            """INSERT OR IGNORE INTO sos_incidents
            (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("SOS-901", 2, "Sardar Khan Kakar", "ZHB-1190", "0333-7812094", "Quetta–Zhob (N-50)", "Khan Mehtarzai", 30.4833, 67.6167,
             "Stranded in Weather / Flood", "Auto Checkpoint Monitor", "Missed Muslim Bagh checkpoint ETA by 38 mins in sub-zero crosswinds.",
             "ACTIVE SOS", "Levies Mobile Unit #4", now_str)
        )

def generate_unique_driver_code() -> str:
    existing = {r["driver_code"] for r in rows("SELECT driver_code FROM drivers WHERE driver_code IS NOT NULL")}
    num = 2401 + len(rows("SELECT id FROM drivers"))
    while f"BHW-{num}" in existing:
        num += 1
    return f"BHW-{num}"

def generate_unique_sos_code() -> str:
    existing = {r["sos_code"] for r in rows("SELECT sos_code FROM sos_incidents WHERE sos_code IS NOT NULL")}
    num = 901 + len(rows("SELECT id FROM sos_incidents"))
    while f"SOS-{num}" in existing:
        num += 1
    return f"SOS-{num}"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,surface_pressure",
        "hourly": "temperature_2m,precipitation_probability,precipitation,visibility,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": 7,
        "timezone": "Asia/Karachi"
    }
    response = requests.get(API, params=params, timeout=12)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "current" not in data:
        raise ValueError("Invalid weather payload received")
    return data

def safe_float(val, default=None):
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default

def weather_info(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1
    if code == 0:
        return ("Clear Sky", "صاف موسم", "☀️", 1)
    if code in (1, 2, 3):
        return ("Partly Cloudy", "ابر آلود", "⛅", 2)
    if code in (45, 48):
        return ("Dense Fog", "گہری دھند", "🌫️", 7)
    if code in (51, 53, 55, 56, 57):
        return ("Light Drizzle", "ہلکی بوندا باندی", "🌦️", 4)
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ("Heavy Rain", "بارش / پھسلن", "🌧️", 7)
    if code in (71, 73, 75, 77, 85, 86):
        return ("Snowfall / Ice", "برف باری", "❄️", 9)
    if code in (95, 96, 99):
        return ("Thunderstorm", "آندھی اور گرج چمک", "⛈️", 9)
    return ("Variable / Telemetry", "موسمی تبدیلی", "🌤️", 3)

def compute_risk_score(cur, road_status_str, manual_risk=None):
    if "Closed" in (road_status_str or ""):
        return 10
    score = 1
    if "Restricted" in (road_status_str or ""):
        score = max(score, 6)
    elif "Pending" in (road_status_str or ""):
        score = max(score, 4)
    if manual_risk is not None:
        try:
            score = max(score, int(manual_risk))
        except (TypeError, ValueError):
            pass
    if cur:
        code = cur.get("weather_code")
        if code is not None:
            _, _, _, w_risk = weather_info(code)
            score = max(score, w_risk)
        wind = safe_float(cur.get("wind_speed_10m"), 0.0)
        precip = safe_float(cur.get("precipitation"), 0.0)
        if wind > 35:
            score = max(score, 7)
        elif wind > 22:
            score = max(score, 5)
        if precip > 2.0:
            score = max(score, 8)
    return max(1, min(int(score), 10))

def journey_risk_tier(score: int) -> tuple[str, str, str]:
    if score <= 3:
        return ("LOW", "#10b981", "rgba(16,185,129,0.16)")
    if score <= 6:
        return ("MODERATE", "#f59e0b", "rgba(245,158,11,0.18)")
    if score <= 8:
        return ("HIGH", "#f97316", "rgba(249,115,22,0.22)")
    return ("SEVERE", "#ef4444", "rgba(239,68,68,0.24)")

def risk_meta(score):
    tier, color, bg = journey_risk_tier(score)
    return (f"{tier} RISK", color, bg)

def get_overdue_drivers(drivers_list):
    now = datetime.now()
    overdue = []
    for d in drivers_list:
        st_val = d.get("status") or ""
        if "Safe" in st_val or "Completed" in st_val:
            continue
        eta_str = d.get("expected_eta")
        is_flagged = "Overdue" in st_val or "SOS" in st_val
        mins_late = 0
        if eta_str:
            try:
                eta_dt = datetime.strptime(eta_str, "%Y-%m-%d %H:%M")
                if now > eta_dt:
                    is_flagged = True
                    mins_late = int((now - eta_dt).total_seconds() // 60)
            except ValueError:
                pass
        if is_flagged:
            d_copy = dict(d)
            d_copy["mins_late"] = max(mins_late, 15)
            overdue.append(d_copy)
    return overdue

def to_phonetic_tts_script(text: str, lang: str) -> tuple[str, str]:
    clean = text.replace("→", " سے ").replace("—", " ، ").replace("–", " ")
    clean = re.sub(r"\bN-(\d+)\b", r"این \1", clean)
    clean = re.sub(r"\bM-(\d+)\b", r"ایم \1", clean)
    clean = re.sub(r"[()\[\]•|/]+", " ، ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if lang == "English":
        en_clean = text.replace("→", " to ").replace("—", ", ").replace("–", " ")
        en_clean = re.sub(r"[()\[\]•|/]+", ", ", en_clean)
        en_clean = re.sub(r"\s+", " ", en_clean).strip()
        return en_clean, "en"
    if lang == "Urdu":
        return clean, "ur"
    elif lang == "Pashto":
        pashto_norm = (
            clean.replace("ښ", "ش")
            .replace("ږ", "ژ")
            .replace("څ", "تس")
            .replace("ځ", "دز")
            .replace("ډ", "ڈ")
            .replace("ړ", "ڑ")
            .replace("ڼ", "ن")
            .replace("ټ", "ٹ")
            .replace("ګ", "گ")
            .replace("ې", "ے")
            .replace("ۍ", "ئی")
            .replace("ۀ", "ہ")
        )
        return pashto_norm, "ur"
    else:
        balochi_norm = (
            clean.replace("ءِ", " ءِ ")
            .replace("ءَ", " ءَ ")
            .replace("ءُ", " اور ")
            .replace("گوں", " گون ")
            .replace("پچ انت", " پچ اَنت ")
            .replace("بند انت", " بند اَنت ")
            .replace("المی انت", " المی اَنت ")
        )
        return balochi_norm, "ur"

VOICE_SAMPLES_DIR = Path(__file__).with_name("voice_samples")
VOICE_SAMPLES_DIR.mkdir(exist_ok=True)

def save_custom_voice_sample(lang: str, audio_bytes: bytes, ext: str = "wav") -> Path:
    safe_ext = re.sub(r"[^a-zA-Z0-9]", "", ext.lower()) or "wav"
    if safe_ext == "mpeg":
        safe_ext = "mp3"
    out_path = VOICE_SAMPLES_DIR / f"custom_voice_{lang.lower()}.{safe_ext}"
    for old_f in VOICE_SAMPLES_DIR.glob(f"custom_voice_{lang.lower()}.*"):
        try:
            old_f.unlink()
        except Exception:
            pass
    out_path.write_bytes(audio_bytes)
    return out_path

def get_custom_voice_sample(lang: str) -> tuple[bytes, str] | None:
    matches = sorted(VOICE_SAMPLES_DIR.glob(f"custom_voice_{lang.lower()}.*"))
    if not matches:
        matches = sorted(VOICE_SAMPLES_DIR.glob("custom_voice_*.*"))
    if matches:
        p = matches[0]
        mime = "audio/mpeg" if p.suffix.lower() == ".mp3" else ("audio/ogg" if p.suffix.lower() == ".ogg" else "audio/wav")
        return p.read_bytes(), mime
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def synthesize_voice_mp3(text: str, lang: str) -> bytes | None:
    spoken_text, tts_lang = to_phonetic_tts_script(text, lang)
    # 1. Try Microsoft Edge Neural Female Voices (Studio-grade natural female voice)
    try:
        import asyncio
        import edge_tts

        voice_map = {
            "Urdu": "ur-PK-UzmaNeural",       # Natural Pakistani Urdu Female
            "English": "en-GB-SoniaNeural",   # Clear, warm natural English Female
            "Pashto": "ps-AF-LatifaNeural",   # Natural Pashto Female
            "Balochi": "ur-PK-UzmaNeural",    # Natural Urdu/Balochi phonetic Female
        }
        chosen_neural = voice_map.get(lang, "ur-PK-UzmaNeural")
        tts_input = text if lang in ("Urdu", "English", "Pashto") else spoken_text

        async def _gen_edge_mp3() -> bytes:
            communicate = edge_tts.Communicate(tts_input, chosen_neural, rate="-4%", pitch="+2Hz")
            chunks = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.extend(chunk["data"])
            return bytes(chunks)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                audio_data = ex.submit(lambda: asyncio.run(_gen_edge_mp3())).result(timeout=15)
        else:
            audio_data = asyncio.run(_gen_edge_mp3())

        if audio_data and len(audio_data) > 500:
            return audio_data
    except Exception:
        pass

    # 2. Fallback to gTTS
    try:
        from gtts import gTTS
        import io
        if lang == "English":
            buf = io.BytesIO()
            gTTS(text=spoken_text, lang="en", tld="co.uk", slow=False).write_to_fp(buf)
            return buf.getvalue()
        if lang == "Pashto":
            try:
                buf = io.BytesIO()
                gTTS(text=text, lang="ps", slow=False).write_to_fp(buf)
                return buf.getvalue()
            except Exception:
                pass
        buf = io.BytesIO()
        gTTS(text=spoken_text, lang=tts_lang, slow=False).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None

def localize_weather_term(weather_en: str, lang: str) -> str:
    mapping = {
        "Clear Sky": {"Urdu": "صاف موسم", "English": "Clear Sky", "Pashto": "ساحو او صفا هوا", "Balochi": "ساپ ءُ وشیں موسم"},
        "Partly Cloudy": {"Urdu": "جزوی ابر آلود", "English": "Partly Cloudy", "Pashto": "نیمه وریځ", "Balochi": "نيم جمبر"},
        "Dense Fog": {"Urdu": "گہری دھند", "English": "Dense Fog", "Pashto": "سخته لړه او غبار", "Balochi": "گورم ءُ دنز"},
        "Light Drizzle": {"Urdu": "ہلکی بوندا باندی", "English": "Light Drizzle", "Pashto": "نرم باران", "Balochi": "هورتیں هور"},
        "Heavy Rain": {"Urdu": "تیز بارش اور پھسلن", "English": "Heavy Rain & Flash Flood Risk", "Pashto": "تیز باران او ښویدنه", "Balochi": "تيزیں هور ءُ لگوشگ"},
        "Snowfall / Ice": {"Urdu": "برف باری اور کہرا", "English": "Heavy Snowfall & Black Ice", "Pashto": "واوره او یخ وهنه", "Balochi": "برپ ءُ يخبندی"},
        "Thunderstorm": {"Urdu": "آندھی اور گرج چمک", "English": "Severe Thunderstorm & Squalls", "Pashto": "توفان، تندر او تیز باد", "Balochi": "توپان ءُ گرند ءُ گروک"},
    }
    if weather_en in mapping and lang in mapping[weather_en]:
        return mapping[weather_en][lang]
    if lang == "English":
        return weather_en
    if lang == "Urdu":
        return "موسمی تبدیلی"
    if lang == "Pashto":
        return "د هوا بدلون"
    return "موسم ءِ بدلی"

def generate_multilingual_alert(area, route, weather_en, weather_ur, road, lang):
    w_local = localize_weather_term(weather_en, lang)
    alt_str = ROUTES_DATA[route]["alt_route"]
    if lang == "English":
        if "Closed" in road:
            return (
                f"EMERGENCY HIGHWAY ALERT ({route}): The road at {area} is CLOSED due to {w_local}. "
                f"Halt immediately at the nearest safe rest area or Levies checkpoint. Verified Alternative Route: {alt_str}.",
                f"Route Closed — Use Verified Detour: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"TRAVEL CAUTION ({route}): Restricted movement at {area} due to {w_local}. "
                f"Reduce speed, use fog lights, and stop at the nearest safe haven if visibility drops.",
                "Proceed with caution or pause at nearest safe rest area."
            )
        return (
            f"HIGHWAY ADVISORY ({route}): {area} corridor is OPEN with {w_local}. "
            f"Maintain safe speed limits and scan your QR pass at the next checkpoint.",
            "Corridor verified open — safe to proceed."
        )
    elif lang == "Urdu":
        if "Closed" in road:
            return (
                f"ہنگامی شاہراہ الرٹ: {route} پر {area} کے مقام پر سڑک {w_local} کے باعث بند کر دی گئی ہے۔ "
                f"قریبی محفوظ ریسٹ ایریا پر رک جائیں۔ متبادل محفوظ راستہ: {alt_str}۔",
                f"مقام بند ہے — متبادل راستہ اختیار کریں: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"سفری انتباہ: {route} کے {area} سیکٹر میں {w_local} کے باعث احتیاطی پابندی نافذ ہے۔ "
                f"رفتار کم رکھیں، فوگ لائٹس آن رکھیں اور ضرورت پڑنے پر قریبی محفوظ اسٹاپ پر رک جائیں۔",
                "پہاڑی دروں پر احتیاط کریں یا محفوظ ریسٹ ایریا پر قیام کریں۔"
            )
        return (
            f"موسمی اپ ڈیٹ: {route} پر {area} کے اطراف میں موسم {w_local} ہے اور شاہراہ کھلی ہے۔ "
            f"محفوظ ڈرائیونگ کے اصولوں پر عمل کریں اور چیک پوسٹ پر کیو آر کوڈ اسکین کروائیں۔",
            "سفر جاری رکھا جا سکتا ہے — رفتار کی حد کی پابندی کریں۔"
        )
    elif lang == "Pashto":
        if "Closed" in road:
            return (
                f"بیړنی خبرتیا: د {route} پر لویه لاره د {area} په سیمه کې د {w_local} له امله تړل شوې ده. "
                f"مهرباني وکړئ په نږدې خوندي تمځای کې ودریږئ. بدیله خوندي لاره: {alt_str}.",
                f"لاره تړلې ده — بدیله لاره وکاروئ: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"د احتیاط خبرتیا: د {route} پر لاره د {area} په سیمه کې د {w_local} له امله احتیاط اړین دی. "
                f"مهرباني وکړئ سرعت کم کړئ او د اړتیا په صورت کې په خوندي ځای کې تم شئ.",
                "په غرنیو لارو کې په پوره احتیاط سره موټر چلوئ."
            )
        return (
            f"د هوا او لارې تازه معلومات: د {route} پر لاره د {area} په سیمه کې هوا {w_local} ده او لویه لاره خلاصه ده. "
            f"ترافیکي قوانین مراعات کړئ او په پوسته کې کیو آر کوڈ سکین کړئ.",
            "لاره خلاصه ده — خپل سفر په خوندي توګه ترسره کړئ."
        )
    else:
        if "Closed" in road:
            return (
                f"هنگامی حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ راه {w_local} ءِ سوب ءَ بند کنگ بوتگ۔ "
                f"نزیکیں محفوظیں ریسٹ ایریا ءَ اوشت ات۔ دومی محفوظیں راه: {alt_str}۔",
                f"راه بند انت — دومی محفوظیں راه ءَ بہ رو ات: {alt_str}"
            )
        if "Restricted" in road:
            return (
                f"هوشیاری حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ {w_local} ءِ سوب ءَ هوشیاری المی انت۔ "
                f"گاڑی ءِ رفتار کم بہ کن ات ءُ نزیکیں محفوظیں جاہ ءَ اوشت ات۔",
                "کوهی راهانی سر ءَ گوں هوشیاری ءَ سفر بہ کن ات۔"
            )
        return (
            f"موسمی ءُ راه ءِ نوکیں حال: {route} شاهراہ ءِ سر ءَ {area} ءِ دمگ ءَ موسم {w_local} انت ءُ شاهراہ پچ انت۔ "
            f"سلامتی ءَ گوں سفر بہ کن ات ءُ چیک پوسٹ ءَ کیو آر کوڈ اسکین بہ کنائین ات۔",
            "شاهراہ پچ انت — ٹریفک ءِ رهبندانی پابندی ءَ بہ کن ات۔"
        )

def trigger_instant_sos(route_name: str, sector_name: str, emergency_type: str = "Accident / Collision",
                        source: str = "Quick SOS Button", notes: str = "", driver_obj: dict | None = None) -> str:
    pts = ROUTES_DATA.get(route_name, ROUTES_DATA[ROUTES[0]])["points"]
    pt_obj = next((p for p in pts if p["name"] == sector_name), pts[0])
    s_code = generate_unique_sos_code()
    now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
    d_id = driver_obj["id"] if driver_obj else None
    d_name = driver_obj["name"] if driver_obj else "Highway Commuter"
    d_veh = driver_obj["vehicle"] if driver_obj else "SOS-UNIT"
    d_ph = driver_obj["phone"] if driver_obj else "0300-0000000"
    run(
        """INSERT INTO sos_incidents
        (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            s_code, d_id, d_name, d_veh, d_ph, route_name, pt_obj["name"],
            pt_obj["lat"], pt_obj["lon"], emergency_type, source,
            notes.strip() or f"{emergency_type} reported at {pt_obj['name']} ({route_name}).",
            "ACTIVE SOS", "Rescue 1122 & Levies Dispatched", now_s,
        ),
    )
    if d_id:
        run("UPDATE drivers SET status='ACTIVE SOS', current_sector=? WHERE id=?", (pt_obj["name"], d_id))
    return s_code

MAP_HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map { height:100%; width:100%; margin:0; padding:0; background:#0c2850; font-family:'Barlow','Inter',system-ui,sans-serif; }
    .leaflet-container { background:#0c2850 !important; }
    /* Navy-blue basemap look */
    .tiles-dark { filter: sepia(1) hue-rotate(178deg) saturate(2.6) brightness(1.55) contrast(.95); }
    .tiles-light { filter: invert(1) grayscale(1) brightness(.85) sepia(1) hue-rotate(178deg) saturate(2.6) brightness(1.5); }
    .leaflet-control-attribution { background:rgba(6,16,36,.7) !important; color:#7f9cc4 !important; font-size:9px; }
    .leaflet-control-attribution a { color:#8fd3ff !important; }

    .legend-bar { position:absolute; top:12px; left:12px; z-index:999; background:rgba(5,14,32,.88); backdrop-filter:blur(8px);
      border:1px solid rgba(82,214,224,.28); border-radius:12px; padding:7px 13px; color:#e2ecfb; font-size:11px;
      display:flex; flex-wrap:wrap; align-items:center; gap:8px 10px; box-shadow:0 8px 24px rgba(0,0,0,.45); max-width:calc(100% - 90px); }
    .pill { padding:2px 8px; border-radius:6px; font-weight:800; font-size:10px; letter-spacing:.3px; }

    .map-hud { position:absolute; bottom:14px; left:14px; z-index:999; background:rgba(5,14,32,.9); backdrop-filter:blur(8px);
      border:1px solid rgba(82,214,224,.32); border-radius:14px; padding:11px 15px; color:#f1f5f9; min-width:230px; max-width:340px;
      box-shadow:0 10px 30px rgba(0,0,0,.55); }
    .hud-title { font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#52d6e0; font-weight:700; }
    .hud-route { font-size:15px; font-weight:800; margin:3px 0 5px 0; }
    .hud-meta { font-size:11px; color:#9db4d6; line-height:1.5; }

    .custom-popup .leaflet-popup-content-wrapper { background:#0b1f42; color:#f1f5f9; border:1px solid #28508f; border-radius:14px; }
    .custom-popup .leaflet-popup-tip { background:#0b1f42; }

    .route-lbl { width:0; height:0; }
    .route-lbl span { position:absolute; transform:translate(-50%,-50%); white-space:nowrap; color:#fff; font-weight:800; font-size:11px;
      letter-spacing:.3px; text-shadow:0 0 4px #04142e,0 0 4px #04142e,0 1px 2px #04142e; opacity:.75; pointer-events:none; }
    .route-lbl.sel span { font-size:15px; opacity:1; }

    .city-tip { background:transparent !important; border:none !important; box-shadow:none !important; color:#fff !important;
      font-weight:800; font-size:11px; letter-spacing:.3px; text-transform:uppercase; text-shadow:0 0 4px #04142e,0 0 4px #04142e; padding:0 !important; }
    .city-tip:before { display:none !important; }

    .map-btn { width:34px; height:34px; display:flex; align-items:center; justify-content:center; background:rgba(5,14,32,.88);
      border:1px solid rgba(82,214,224,.35); border-radius:10px; color:#e6f3ff; font-size:17px; cursor:pointer; margin-bottom:8px; }
    .map-btn:hover { background:rgba(23,179,198,.35); }
    .leaflet-bar { border:none !important; box-shadow:none !important; }
    .leaflet-bar a { background:rgba(5,14,32,.88) !important; color:#e6f3ff !important; border:1px solid rgba(82,214,224,.35) !important;
      border-radius:10px !important; margin-bottom:4px; width:34px !important; height:34px !important; line-height:32px !important; }

    @keyframes pulseSOS { 0%{transform:scale(.95);opacity:.95} 50%{transform:scale(1.25);opacity:.55} 100%{transform:scale(.95);opacity:.95} }
    .sos-badge-icon { background:#ee4b23; color:#fff; font-weight:900; font-size:10px; border:2px solid #fff; border-radius:50%; width:28px; height:28px;
      display:flex; align-items:center; justify-content:center; box-shadow:0 0 16px #ee4b23; animation:pulseSOS 1.3s infinite; }
    .fac-badge-icon { background:#1d6fd1; color:#fff; font-weight:800; font-size:11px; border:1.5px solid #bfe3ff; border-radius:7px; width:22px; height:22px;
      display:flex; align-items:center; justify-content:center; }
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="legend-bar">
    <span style="font-weight:700;color:#9db4d6;">JOURNEY RISK:</span>
    <span class="pill" style="background:rgba(74,222,128,.2);color:#86efac;border:1px solid #4ade80;">LOW</span>
    <span class="pill" style="background:rgba(245,181,58,.2);color:#fcd34d;border:1px solid #f5b53a;">MODERATE</span>
    <span class="pill" style="background:rgba(249,115,22,.22);color:#fdba74;border:1px solid #f97316;">HIGH</span>
    <span class="pill" style="background:rgba(239,68,68,.25);color:#fca5a5;border:1px solid #ef4444;">SEVERE</span>
    <span style="color:#ff6b5b;font-weight:700;">&#9873; Danger zone</span>
    <span style="color:#8fd3ff;font-weight:700;">&#10010; Facilities</span>
    <span style="color:#ff6b5b;font-weight:700;">&#128680; SOS</span>
  </div>
  <div class="map-hud">
    <div class="hud-title">CORRIDOR TELEMETRY &amp; SAFETY HUD</div>
    <div class="hud-route" id="hudRouteName"></div>
    <div class="hud-meta" id="hudRouteMeta">Click any checkpoint, hospital, safe haven, danger flag, or SOS beacon for live details.</div>
  </div>

  <script>
    const routesData = __ROUTES__;
    const sosData = __SOS__;
    const facData = __FAC__;
    const activeLayers = __LAYERS__;
    document.getElementById('hudRouteName').innerText = __HUDROUTE__;

    const map = L.map('map', { center:[28.6,65.9], zoom:6, zoomControl:false });
    L.control.zoom({ position:'bottomright' }).addTo(map);

    const primaryTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution:'&copy; OpenStreetMap &copy; CARTO | Balochistan Transport Safety System',
      subdomains:'abcd', maxZoom:18, className:'tiles-dark'
    });
    const fallbackTiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:'&copy; OpenStreetMap contributors', maxZoom:18, className:'tiles-light'
    });
    let fallbackApplied = false;
    primaryTiles.on('tileerror', () => {
      if (!fallbackApplied) { fallbackApplied = true; map.removeLayer(primaryTiles); fallbackTiles.addTo(map); }
    });
    primaryTiles.addTo(map);

    function riskColor(r) {
      if (r >= 9) return '#ef4444';
      if (r >= 7) return '#f97316';
      if (r >= 4) return '#f5b53a';
      return '#4ade80';
    }
    const pinSvg = '<svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg"><path d="M13 1C6.4 1 1.5 6 1.5 12.4c0 8.2 11.5 20 11.5 20s11.5-11.8 11.5-20C24.5 6 19.6 1 13 1z" fill="#fff" stroke="#0b2a57" stroke-width="1.5"/><circle cx="13" cy="12.4" r="4.4" fill="#0b2a57"/></svg>';
    const flagSvg = '<svg width="24" height="30" viewBox="0 0 24 30" xmlns="http://www.w3.org/2000/svg"><line x1="5" y1="2" x2="5" y2="28" stroke="#e2e8f0" stroke-width="2.2" stroke-linecap="round"/><path d="M5 3h16l-4 5.5 4 5.5H5z" fill="#ef4444" stroke="#7f1d1d" stroke-width="1"/></svg>';

    function popupFor(route, pt) {
      const c = riskColor(pt.risk);
      return `
        <div style="min-width:215px;font-family:Barlow,Inter,sans-serif;">
          <div style="font-size:10px;color:#52d6e0;font-weight:700;">${route.code} CHECKPOINT</div>
          <div style="font-size:16px;font-weight:800;margin:2px 0 8px 0;">${pt.name} <span style="font-size:11px;color:#9db4d6;">(${pt.elev})</span></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;background:#07162f;padding:8px;border-radius:9px;margin-bottom:8px;">
            <div><span style="color:#7f9cc4;">Temp:</span> <b>${pt.temp} °C</b></div>
            <div><span style="color:#7f9cc4;">Wind:</span> <b>${pt.wind} km/h</b></div>
            <div><span style="color:#7f9cc4;">Rain:</span> <b>${pt.precip} mm</b></div>
            <div><span style="color:#7f9cc4;">Rating:</span> <b style="color:${c};">${pt.tier} (${pt.risk}/10)</b></div>
          </div>
          <div style="font-size:11px;"><b>Weather:</b> ${pt.weather}</div>
          <div style="font-size:11px;margin-top:3px;"><b>Road Status:</b> <span style="color:${c};">${pt.status}</span></div>
        </div>`;
    }
    function hudUpdate(pt) {
      const c = riskColor(pt.risk);
      document.getElementById('hudRouteMeta').innerHTML =
        `<b>${pt.name}</b> (${pt.elev}) • Temp: <b>${pt.temp}°C</b> • Rating: <b style="color:${c};">${pt.tier}</b><br/>Status: ${pt.status}`;
    }

    let selectedBounds = [];
    const pinned = {};

    // Draw unselected routes first so the selected corridor always sits on top
    const ordered = routesData.slice().sort((a, b) => (a.selected ? 1 : 0) - (b.selected ? 1 : 0));

    ordered.forEach(route => {
      const latlngs = route.points.map(p => [p.lat, p.lon]);
      const isSel = route.selected;

      if (activeLayers.highways) {
        L.polyline(latlngs, { color:'#9fe7ff', weight:isSel ? 15 : 9, opacity:isSel ? 0.2 : 0.1, lineCap:'round', lineJoin:'round' }).addTo(map);
        for (let i = 0; i < route.points.length - 1; i++) {
          const a = route.points[i], b = route.points[i + 1];
          const seg = L.polyline([[a.lat, a.lon], [b.lat, b.lon]], {
            color: riskColor(Math.max(a.risk, b.risk)), weight:isSel ? 5.5 : 3.5, opacity:isSel ? 1 : 0.78, lineCap:'round'
          }).addTo(map);
          seg.bindTooltip(`${route.name} (${route.distance}) • ${a.name} → ${b.name} • Risk ${Math.max(a.risk, b.risk)}/10`, { sticky:true });
        }
        const mi = Math.floor((route.points.length - 1) / 2);
        const pa = route.points[mi], pb = route.points[Math.min(mi + 1, route.points.length - 1)];
        const mid = [(pa.lat + pb.lat) / 2, (pa.lon + pb.lon) / 2];
        L.marker(mid, { icon:L.divIcon({ className:'route-lbl' + (isSel ? ' sel' : ''), html:'<span>' + route.label + '</span>', iconSize:[0, 0] }), interactive:false, keyboard:false }).addTo(map);
      }

      route.points.forEach((pt, idx) => {
        if (isSel) selectedBounds.push([pt.lat, pt.lon]);
        const ptColor = riskColor(pt.risk);
        const isEnd = (idx === 0 || idx === route.points.length - 1);

        if (activeLayers.weather_radar) {
          L.circle([pt.lat, pt.lon], { radius:isSel ? 32000 : 20000, color:ptColor, weight:1, fillColor:ptColor, fillOpacity:isSel ? 0.14 : 0.07, interactive:false }).addTo(map);
        }

        if (activeLayers.checkpoints) {
          const marker = L.circleMarker([pt.lat, pt.lon], {
            radius:isSel ? 6 : 4, fillColor:'#0b2a57', color:'#ffffff', weight:isSel ? 2.5 : 1.5, opacity:1, fillOpacity:1
          }).addTo(map);
          marker.bindPopup(popupFor(route, pt), { className:'custom-popup' });
          marker.on('click', () => hudUpdate(pt));

          if (isSel || isEnd) {
            marker.bindTooltip(pt.name, { permanent:true, direction:'right', offset:[8, 0], className:'city-tip' });
          }

          if (isEnd && !pinned[pt.name]) {
            pinned[pt.name] = true;
            const pm = L.marker([pt.lat, pt.lon], { icon:L.divIcon({ className:'', html:pinSvg, iconSize:[26, 34], iconAnchor:[13, 33] }) }).addTo(map);
            pm.bindPopup(popupFor(route, pt), { className:'custom-popup' });
            pm.on('click', () => hudUpdate(pt));
          }

          const isDanger = pt.risk >= 7 || /Closed|Restricted/.test(pt.status);
          if (isDanger) {
            const fm = L.marker([pt.lat, pt.lon], { icon:L.divIcon({ className:'', html:flagSvg, iconSize:[24, 30], iconAnchor:[5, 29] }), zIndexOffset:500 }).addTo(map);
            fm.bindPopup(popupFor(route, pt), { className:'custom-popup' });
            fm.on('click', () => hudUpdate(pt));
          }
        }
      });
    });

    if (activeLayers.facilities) {
      facData.forEach(fc => {
        let symbol = '🏥';
        if (fc.type.includes('Petrol')) symbol = '⛽';
        else if (fc.type.includes('Repair')) symbol = '🔧';
        else if (fc.type.includes('Safe')) symbol = '🛡️';
        const fIcon = L.divIcon({ className:'', html:`<div class="fac-badge-icon">${symbol}</div>`, iconSize:[22, 22], iconAnchor:[11, 11] });
        const fm = L.marker([fc.lat + 0.04, fc.lon + 0.04], { icon:fIcon }).addTo(map);
        fm.bindPopup(`
          <div style="min-width:200px;font-family:Barlow,Inter,sans-serif;">
            <div style="font-size:10px;color:#8fd3ff;font-weight:800;">${fc.type.toUpperCase()}</div>
            <div style="font-size:15px;font-weight:800;margin:2px 0 6px 0;">${fc.name}</div>
            <div style="font-size:11px;color:#cbd5e1;">Sector: <b>${fc.sector}</b></div>
            <div style="font-size:11px;color:#52d6e0;margin:3px 0;">Helpline: <b>${fc.phone}</b></div>
            <div style="font-size:11px;color:#9db4d6;">${fc.notes}</div>
          </div>`, { className:'custom-popup' });
      });
    }

    sosData.forEach(s => {
      const sIcon = L.divIcon({ className:'', html:`<div class="sos-badge-icon">SOS</div>`, iconSize:[28, 28], iconAnchor:[14, 14] });
      const sm = L.marker([s.lat, s.lon], { icon:sIcon, zIndexOffset:1000 }).addTo(map);
      sm.bindPopup(`
        <div style="min-width:210px;font-family:Barlow,Inter,sans-serif;">
          <div style="font-size:10px;color:#ff6b5b;font-weight:800;">🚨 ACTIVE EMERGENCY (${s.code})</div>
          <div style="font-size:15px;font-weight:800;margin:2px 0 6px 0;">${s.vehicle} • ${s.driver}</div>
          <div style="font-size:11px;"><b>Type:</b> ${s.type}</div>
          <div style="font-size:11px;"><b>Location:</b> ${s.sector}</div>
          <div style="font-size:11px;color:#fca5a5;margin-top:4px;">${s.details}</div>
        </div>`, { className:'custom-popup' });
    });

    function fitSelected() { if (selectedBounds.length > 1) map.fitBounds(selectedBounds, { padding:[60, 60] }); }

    // Top-right fullscreen + bottom-right recenter controls
    const Ctl = L.Control.extend({
      options:{ position:'topright' },
      onAdd: function () {
        const d = L.DomUtil.create('div');
        const fs = L.DomUtil.create('div', 'map-btn', d); fs.innerHTML = '&#x26F6;'; fs.title = 'Fullscreen';
        L.DomEvent.disableClickPropagation(d);
        fs.onclick = () => {
          const el = document.documentElement;
          try { if (!document.fullscreenElement) el.requestFullscreen(); else document.exitFullscreen(); } catch (e) {}
        };
        return d;
      }
    });
    map.addControl(new Ctl());
    const Ctl2 = L.Control.extend({
      options:{ position:'bottomright' },
      onAdd: function () {
        const d = L.DomUtil.create('div');
        const lc = L.DomUtil.create('div', 'map-btn', d); lc.innerHTML = '&#9678;'; lc.title = 'Recenter on active corridor';
        L.DomEvent.disableClickPropagation(d);
        lc.onclick = fitSelected;
        return d;
      }
    });
    map.addControl(new Ctl2());
    window.addEventListener('resize', () => { map.invalidateSize(); });

    fitSelected();
    setTimeout(() => { map.invalidateSize(); fitSelected(); }, 250);
  </script>
</body>
</html>
"""

def render_balochistan_map(selected_route, weather_cache, road_map, layers, sos_list=None, facilities_list=None):
    routes_payload = []
    for r_name, r_data in ROUTES_DATA.items():
        pts_out = []
        max_r = 1
        for pt in r_data["points"]:
            w_cur = weather_cache.get(pt["name"], {})
            r_row = road_map.get((r_name, pt["name"]), {})
            r_stat = r_row.get("status", "Open (Verified)")
            r_score = compute_risk_score(w_cur, r_stat, r_row.get("risk_score"))
            max_r = max(max_r, r_score)
            has_weather = bool(w_cur and ("temperature_2m" in w_cur or "weather_code" in w_cur))
            label_txt, _, _, _ = weather_info(w_cur.get("weather_code")) if has_weather else ("Cached / Telemetry", "", "🛰️", 2)
            temp_disp = f"{safe_float(w_cur.get('temperature_2m')):.1f}" if safe_float(w_cur.get("temperature_2m")) is not None else "—"
            wind_disp = f"{safe_float(w_cur.get('wind_speed_10m')):.1f}" if safe_float(w_cur.get("wind_speed_10m")) is not None else "—"
            precip_disp = f"{safe_float(w_cur.get('precipitation')):.1f}" if safe_float(w_cur.get("precipitation")) is not None else "—"
            tier_lbl, _, _ = journey_risk_tier(r_score)
            pts_out.append({
                "name": pt["name"],
                "lat": pt["lat"],
                "lon": pt["lon"],
                "elev": pt["elevation"],
                "temp": temp_disp,
                "wind": wind_disp,
                "precip": precip_disp,
                "weather": label_txt,
                "status": r_stat,
                "risk": r_score,
                "tier": tier_lbl
            })
        _, color_hex, _ = risk_meta(max_r)
        routes_payload.append({
            "name": r_name,
            "label": r_name.split(" (")[0].replace("–", " – ").upper() + " ROUTE",
            "code": r_data["code"],
            "distance": r_data["distance"],
            "selected": (r_name == selected_route),
            "color": color_hex,
            "max_risk": max_r,
            "points": pts_out
        })

    sos_payload = []
    for s in (sos_list or []):
        if s.get("status") == "ACTIVE SOS" and s.get("lat") and s.get("lon"):
            sos_payload.append({
                "code": s.get("sos_code", "SOS"),
                "driver": s.get("driver_name", ""),
                "vehicle": s.get("vehicle", ""),
                "type": s.get("emergency_type", "Emergency"),
                "sector": s.get("sector", ""),
                "lat": float(s["lat"]),
                "lon": float(s["lon"]),
                "details": s.get("details", "")
            })

    fac_payload = []
    for fc in (facilities_list or []):
        if fc.get("route") == selected_route or layers.get("all_facilities"):
            fac_payload.append({
                "type": fc["type"],
                "name": fc["name"],
                "sector": fc["sector"],
                "phone": fc["phone"],
                "notes": fc["notes"],
                "lat": fc["lat"],
                "lon": fc["lon"]
            })

    payload_json = json.dumps(routes_payload).replace("</", "<\\/")
    sos_json = json.dumps(sos_payload).replace("</", "<\\/")
    fac_json = json.dumps(fac_payload).replace("</", "<\\/")
    layers_json = json.dumps(layers).replace("</", "<\\/")
    hud_route_safe = json.dumps(selected_route).replace("</", "<\\/")

    html = MAP_HTML_TEMPLATE
    html = html.replace("__ROUTES__", payload_json)
    html = html.replace("__SOS__", sos_json)
    html = html.replace("__FAC__", fac_json)
    html = html.replace("__LAYERS__", layers_json)
    html = html.replace("__HUDROUTE__", hud_route_safe)
    components.html(html, height=520, scrolling=False)


def wind_compass(deg):
    d = safe_float(deg)
    if d is None:
        return ""
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int(((d % 360) + 22.5) // 45) % 8]

_CLOUD = '<path d="M18 46h27a9.5 9.5 0 0 0 1.5-18.9A13 13 0 0 0 21.5 25 10.5 10.5 0 0 0 18 46z"/>'
_ICON_WRAP = '<svg width="{s}" height="{s}" viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{b}</svg>'
_WX_ICONS = {
    "sun": '<circle cx="32" cy="32" r="9"/>' + "".join(
        f'<line x1="{32 + 15 * c:.1f}" y1="{32 + 15 * s:.1f}" x2="{32 + 22 * c:.1f}" y2="{32 + 22 * s:.1f}"/>'
        for c, s in [(1, 0), (.707, .707), (0, 1), (-.707, .707), (-1, 0), (-.707, -.707), (0, -1), (.707, -.707)]),
    "partly": '<circle cx="24" cy="22" r="7"/><line x1="24" y1="8" x2="24" y2="11"/><line x1="10" y1="22" x2="13" y2="22"/><line x1="14" y1="12" x2="16" y2="14"/><line x1="34" y1="12" x2="32" y2="14"/>'
              '<path d="M22 50h24a9 9 0 0 0 1.4-17.9A12 12 0 0 0 25 31a10 10 0 0 0-3 19z"/>',
    "cloud": _CLOUD,
    "fog": '<path d="M18 38h27a9 9 0 0 0 1.5-17.9A13 13 0 0 0 21.5 17 10.5 10.5 0 0 0 18 38z"/><line x1="14" y1="46" x2="50" y2="46"/><line x1="20" y1="54" x2="44" y2="54"/>',
    "rain": '<path d="M18 38h27a9 9 0 0 0 1.5-17.9A13 13 0 0 0 21.5 17 10.5 10.5 0 0 0 18 38z"/><line x1="22" y1="46" x2="19" y2="54"/><line x1="32" y1="46" x2="29" y2="54"/><line x1="42" y1="46" x2="39" y2="54"/>',
    "snow": '<path d="M18 38h27a9 9 0 0 0 1.5-17.9A13 13 0 0 0 21.5 17 10.5 10.5 0 0 0 18 38z"/><circle cx="22" cy="49" r="1.6"/><circle cx="32" cy="53" r="1.6"/><circle cx="42" cy="49" r="1.6"/>',
    "storm": '<path d="M18 38h27a9 9 0 0 0 1.5-17.9A13 13 0 0 0 21.5 17 10.5 10.5 0 0 0 18 38z"/><polyline points="33,40 27,49 35,49 29,58"/>',
}

def wx_icon_key(code):
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "cloud"
    if c == 0:
        return "sun"
    if c in (1, 2):
        return "partly"
    if c == 3:
        return "cloud"
    if c in (45, 48):
        return "fog"
    if c in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if c in (71, 73, 75, 77, 85, 86):
        return "snow"
    if c in (95, 96, 99):
        return "storm"
    return "partly"

def wx_icon_svg(code, size=54):
    return _ICON_WRAP.format(s=size, b=_WX_ICONS[wx_icon_key(code)])

WIND_ICON_SVG = ('<svg width="30" height="22" viewBox="0 0 40 28" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round">'
                 '<path d="M3 9h22a5 5 0 1 0-5-5"/><path d="M3 15h30a5 5 0 1 1-5 5"/><path d="M3 21h14"/></svg>')

def risk_tier_label(score):
    tier, _, _ = journey_risk_tier(score)
    name = {"LOW": "GREEN", "MODERATE": "AMBER", "HIGH": "ORANGE", "SEVERE": "RED"}[tier]
    css = {"LOW": "wx-low", "MODERATE": "wx-mod", "HIGH": "wx-high", "SEVERE": "wx-sev"}[tier]
    return tier, name, css

def _go_nav(key):
    st.session_state["nav_key"] = key

NAV_ITEMS = [
    ("dash", "🏠", "Admin Control Dashboard"),
    ("sos", "🚨", "Emergency SOS & Welfare"),
    ("driver", "🚚", "Driver Portal & Journey Risk"),
    ("map", "🗺️", "Highway Map & Safe Routes"),
    ("alert", "🔊", "Multilingual Alert & Voice"),
    ("road", "🛣️", "Road Clearance & Logs"),
]
NAV_LABELS = {k: lbl for k, _, lbl in NAV_ITEMS}
NAV_ICONS = {k: ic for k, ic, _ in NAV_ITEMS}


if "_db_initialized" not in st.session_state:
    init_db()
    seed()
    st.session_state["_db_initialized"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Semi+Condensed:wght@500;600;700;800&family=JetBrains+Mono:wght@500;700&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

:root {
  --navy-0: #06122a;
  --navy-1: #0a1f44;
  --navy-2: #0f2d5e;
  --royal: #1f55b3;
  --royal-2: #19418f;
  --cyan: #17b3c6;
  --aqua: #52d6e0;
  --sos: #ee4b23;
  --green: #9be15d;
  --amber: #f6b93b;
  --text-main: #ffffff;
  --text-muted: #9db4d6;
  --font-head: 'Barlow Semi Condensed', 'Barlow', sans-serif;
}

html, body, .stApp { font-family: 'Barlow', 'Inter', sans-serif; }

.stApp {
  background:
    radial-gradient(110% 38% at 50% 104%, rgba(23, 179, 198, 0.55) 0%, rgba(23, 179, 198, 0) 70%),
    radial-gradient(60% 40% at 15% 0%, rgba(31, 85, 179, 0.35) 0%, transparent 70%),
    linear-gradient(180deg, #06122a 0%, #0a1f44 52%, #0c3566 100%);
  background-attachment: fixed;
  color: var(--text-main);
}
[data-testid="stHeader"] { background: transparent; }

.block-container { padding-top: 1rem; padding-bottom: 2.5rem; max-width: 1700px; }

h1, h2, h3, h4 {
  color: #ffffff !important;
  font-family: var(--font-head);
  letter-spacing: 0.01em;
  text-transform: uppercase;
  font-weight: 700 !important;
}

/* ---------- Left navigation rail (sidebar) ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #081a3b 0%, #0b2a58 100%);
  border-right: 1px solid rgba(82, 214, 224, 0.2);
  min-width: 290px; max-width: 290px;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0.8rem; }
[data-testid="stSidebar"] hr { border-color: rgba(157, 180, 214, .18); margin: .9rem 0; }
.nav-caption {
  font-family: var(--font-head); font-size: 12px; font-weight: 700; letter-spacing: 1.4px;
  color: var(--aqua); margin: 4px 2px 6px 2px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap: .3rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  width: 100%; margin: 0; padding: .72rem .9rem; border-radius: 12px;
  border: 1px solid transparent; border-left: 4px solid transparent;
  transition: background .15s ease; cursor: pointer;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child { display: none; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: rgba(82, 214, 224, 0.09); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: linear-gradient(90deg, rgba(23, 179, 198, .42) 0%, rgba(23, 179, 198, .10) 100%);
  border-left-color: var(--aqua);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label p {
  font-family: var(--font-head); font-weight: 600; font-size: 1.02rem; color: #ffffff;
  filter: grayscale(1) brightness(1.8); letter-spacing: .01em;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] label {
  color: #cfe0f7 !important; font-weight: 700; font-size: 0.82rem;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  min-height: 44px; border-radius: 10px; background: #0c2552; border-color: rgba(82,214,224,.35);
}
[data-testid="stSidebar"] .stButton > button { min-height: 42px; }

.side-brand { display: flex; align-items: center; gap: 12px; padding: 4px 0 12px 0; }
.side-brand .t1 { font-family: var(--font-head); font-weight: 800; font-size: 16px; color: #fff; letter-spacing: .6px; line-height: 1.1; }
.side-brand .t2 { font-size: 10px; color: var(--aqua); font-weight: 700; letter-spacing: 1.2px; }
.side-user {
  background: rgba(5, 16, 38, .6); border: 1px solid rgba(82, 214, 224, .28);
  border-radius: 12px; padding: 10px 12px; margin-bottom: 14px;
}
.side-user .k { font-size: 10px; color: var(--aqua); font-weight: 700; letter-spacing: .9px; }
.side-user .n { font-size: 14px; font-weight: 700; color: #fff; margin-top: 2px; }
.side-user .r { font-size: 11px; color: var(--text-muted); }
.side-vision {
  margin-top: 12px; padding: 11px; background: rgba(5, 16, 38, .55);
  border: 1px solid rgba(157, 180, 214, .2); border-radius: 12px; font-size: 11px; color: var(--text-muted);
}

/* ---------- Header bar ---------- */
.cmd-topbar {
  background: linear-gradient(100deg, rgba(4, 12, 28, .96) 0%, rgba(7, 22, 48, .94) 60%, rgba(8, 30, 60, .94) 100%);
  border: 1px solid rgba(82, 214, 224, .22);
  border-radius: 16px;
  padding: 12px 22px;
  margin-bottom: 14px;
  display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap;
  box-shadow: 0 14px 36px rgba(0, 0, 0, .45);
}
.cmd-brand { display: flex; align-items: center; gap: 14px; min-width: 0; }
.cmd-brand-small {
  font-family: var(--font-head); font-weight: 700; font-size: 12px; line-height: 1.15; color: #dbe8ff;
  letter-spacing: .5px; border-right: 1px solid rgba(157, 180, 214, .3); padding-right: 14px; text-transform: uppercase;
}
.cmd-title {
  font-family: var(--font-head); font-size: clamp(20px, 2.6vw, 34px); font-weight: 700; color: #fff; margin: 0;
  letter-spacing: .01em; text-transform: uppercase; line-height: 1.05;
}
.cmd-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.cmd-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
.tagline-pill {
  background: rgba(23, 179, 198, .16); border: 1px solid rgba(82, 214, 224, .5);
  color: #9cf0f6; padding: 5px 13px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: .5px;
  font-family: var(--font-head);
}
.live-badge {
  display: inline-flex; align-items: center; gap: 7px; background: rgba(155, 225, 93, .14);
  border: 1px solid rgba(155, 225, 93, .55); color: var(--green); padding: 5px 13px; border-radius: 999px;
  font-size: 11px; font-weight: 800; letter-spacing: .8px;
}
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); }

/* ---------- Cards ---------- */
.stat-card {
  background: linear-gradient(160deg, rgba(31, 85, 179, .55) 0%, rgba(14, 40, 92, .75) 100%);
  border: 1px solid rgba(82, 214, 224, .24);
  border-radius: 18px; padding: 15px 17px; min-height: 112px;
  box-shadow: 0 10px 26px rgba(0, 0, 0, .3);
}
.stat-label { font-family: var(--font-head); font-size: 13px; text-transform: uppercase; letter-spacing: .9px; color: #b8cdee; font-weight: 700; }
.stat-val { font-family: var(--font-head); font-size: 34px; font-weight: 800; color: #fff; margin: 3px 0; line-height: 1.1; }
.stat-foot { font-size: 11px; color: var(--aqua); font-weight: 600; }

.ticker-bar {
  background: rgba(5, 16, 38, .72); border: 1px solid rgba(82, 214, 224, .22); border-radius: 14px;
  padding: 9px 16px; margin-bottom: 14px; display: flex; flex-wrap: wrap; justify-content: space-between;
  align-items: center; gap: 10px; font-size: 12px;
}
.gauge-box {
  background: linear-gradient(160deg, rgba(31, 85, 179, .5) 0%, rgba(12, 36, 84, .8) 100%);
  border: 1px solid rgba(82, 214, 224, .22); border-radius: 18px; padding: 12px 8px; text-align: center;
  box-shadow: 0 6px 18px rgba(0, 0, 0, .25);
}
.gauge-ring {
  width: 72px; height: 72px; border-radius: 50%; margin: 6px auto; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-head); font-weight: 800; font-size: 15px; color: #fff;
}
.gauge-title { font-family: var(--font-head); font-size: 12px; text-transform: uppercase; letter-spacing: .9px; color: #b8cdee; font-weight: 700; }
.gauge-sub { font-size: 10px; color: #8ea8cf; }

.side-panel-card {
  background: linear-gradient(180deg, rgba(8, 26, 60, .88) 0%, rgba(6, 18, 42, .9) 100%);
  border: 1px solid rgba(82, 214, 224, .24); border-radius: 18px; padding: 14px; margin-bottom: 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .3);
}
.panel-h { font-family: var(--font-head); font-size: 14px; font-weight: 700; letter-spacing: 1px; margin: 4px 0 8px 0; }
.auth-card {
  background: linear-gradient(160deg, rgba(14, 40, 92, .96) 0%, rgba(6, 18, 42, .98) 100%);
  border: 1px solid rgba(82, 214, 224, .36); border-top: 3px solid var(--sos);
  border-radius: 22px; padding: 28px 30px; box-shadow: 0 24px 55px rgba(0, 0, 0, .65);
}
.sos-banner {
  background: linear-gradient(90deg, rgba(190, 40, 20, .65) 0%, rgba(140, 28, 20, .5) 100%);
  border: 1px solid #ff6b4a; border-radius: 14px; padding: 12px 18px; margin-bottom: 14px;
  display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;
}
.notif-item {
  background: rgba(12, 37, 82, .7); border: 1px solid rgba(157, 180, 214, .14); border-left: 4px solid var(--amber);
  border-radius: 12px; padding: 9px 11px; margin-bottom: 9px;
}
.notif-item.danger { border-left-color: #ff5a4a; }
.notif-item.safe { border-left-color: var(--green); }
.urdu-box {
  font-family: 'Noto Nastaliq Urdu', 'Inter', sans-serif; direction: rtl; text-align: right; line-height: 2.0; font-size: 15px;
  background: rgba(5, 16, 38, .8); border: 1px solid rgba(155, 225, 93, .4); border-radius: 12px; padding: 14px 18px; color: #f1f5f9;
}
.ltr-box {
  font-family: 'Barlow', 'Inter', sans-serif; direction: ltr; text-align: left; line-height: 1.65; font-size: 14px;
  background: rgba(5, 16, 38, .8); border: 1px solid rgba(82, 214, 224, .4); border-radius: 12px; padding: 14px 18px; color: #f1f5f9;
}

/* ---------- Map frame ---------- */
.stApp iframe { border-radius: 18px; }
[data-testid="stIFrame"], .stApp iframe[title*="components"] { border: 1px solid rgba(82, 214, 224, .3); box-shadow: 0 16px 40px rgba(0,0,0,.45); }

/* ---------- Weather zone ---------- */
.wx-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin: 14px 4px 8px 4px; }
.wx-head .l { font-size: 13px; color: #d4e7ff; letter-spacing: .3px; }
.wx-pill {
  background: rgba(8, 26, 60, .9); border: 1px solid rgba(82, 214, 224, .4); color: #fff; border-radius: 10px;
  padding: 7px 14px; font-size: 13px; font-weight: 600;
}
.wx-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; padding: 16px;
  background: linear-gradient(180deg, rgba(23, 179, 198, .28) 0%, rgba(23, 179, 198, .55) 100%);
  border-radius: 22px; border: 1px solid rgba(160, 240, 250, .25);
}
.wx-card {
  background: linear-gradient(165deg, #2a5fc0 0%, #1b429a 100%);
  border: 1px solid rgba(190, 220, 255, .22); border-radius: 20px; padding: 14px 16px 12px 16px;
  box-shadow: 0 10px 22px rgba(4, 18, 50, .45);
}
.wx-top { display: flex; justify-content: space-between; align-items: baseline; }
.wx-name { font-family: var(--font-head); font-weight: 800; font-size: 20px; color: #fff; text-transform: uppercase; letter-spacing: .3px; }
.wx-elev { font-size: 11px; color: #bcd4f5; }
.wx-mid { display: flex; align-items: center; gap: 12px; margin: 6px 0 4px 0; }
.wx-temp { font-family: var(--font-head); font-weight: 700; font-size: 46px; color: #fff; line-height: 1; }
.wx-wind { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; color: #fff; margin: 6px 0 8px 0; }
.wx-foot { border-top: 1px solid rgba(255,255,255,.18); padding-top: 8px; text-align: center; font-family: var(--font-head);
  font-weight: 700; font-size: 13px; letter-spacing: .5px; text-transform: uppercase; }
.wx-low { color: #9be15d; } .wx-mod { color: #f6b93b; } .wx-high { color: #ff9a4d; } .wx-sev { color: #ff7b7b; }

/* ---------- Quick actions (right panel) ---------- */
.qa-title { font-family: var(--font-head); font-size: 22px; font-weight: 700; letter-spacing: .5px; color: #fff; margin: 4px 0 12px 0; }
.st-key-dash_fast_sos_btn { display: flex; justify-content: center; margin: 4px 0 14px 0; }
.st-key-dash_fast_sos_btn button {
  width: 188px; height: 188px; border-radius: 50% !important; padding: 0 !important;
  background: radial-gradient(circle at 50% 30%, #ff7a4a 0%, #ee4b23 62%, #cf3a14 100%) !important;
  border: 6px solid rgba(255, 140, 100, .45) !important;
  box-shadow: 0 0 0 14px rgba(238, 75, 35, .16), 0 0 0 28px rgba(238, 75, 35, .08), 0 18px 40px rgba(238, 75, 35, .5) !important;
}
.st-key-dash_fast_sos_btn button p { font-family: var(--font-head); font-size: 3.1rem; font-weight: 800; line-height: 1; text-align: center; color: #fff; }
.st-key-dash_fast_sos_btn button p::first-line { font-size: 1.05rem; letter-spacing: 1px; }
.st-key-dash_fast_sos_btn button:hover { filter: brightness(1.08); }
.st-key-qa_phone button, .st-key-qa_bell button, .st-key-qa_mail button {
  height: 58px; border-radius: 16px !important; font-size: 1.5rem; min-height: 58px;
  background: linear-gradient(160deg, #2a5fc0 0%, #1b429a 100%) !important; border: 1px solid rgba(190, 220, 255, .3) !important;
}

/* ---------- Buttons & inputs ---------- */
.stButton > button, .stApp [data-testid="stFormSubmitButton"] button {
  min-height: 42px; padding: .45rem .9rem; border-radius: 12px; white-space: normal; line-height: 1.25;
  border: 1px solid rgba(190, 220, 255, .3);
  background: linear-gradient(160deg, #2a62c4 0%, #1a3f8f 100%);
  color: #fff; font-family: var(--font-head); font-weight: 700; font-size: 1rem; letter-spacing: .3px;
  transition: all .18s ease;
}
.stButton > button:hover, .stApp [data-testid="stFormSubmitButton"] button:hover {
  border-color: var(--aqua); box-shadow: 0 0 18px rgba(82, 214, 224, .4); color: #fff;
}
.stApp button[kind="primary"], .stApp [data-testid="stBaseButton-primary"], .stApp [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(160deg, #ff6a3d 0%, #d8401a 100%);
  border-color: rgba(255, 150, 110, .6);
}
.stApp button[kind="primary"]:hover, .stApp [data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 0 20px rgba(238, 75, 35, .6); border-color: #ffb199;
}

.stApp [data-testid="stMarkdownContainer"] p { line-height: 1.55; }
.stApp h1 { font-size: clamp(1.45rem, 2.4vw, 2rem) !important; }
.stApp h2 { font-size: clamp(1.2rem, 2vw, 1.55rem) !important; }
.stApp h3 { font-size: clamp(1.05rem, 1.6vw, 1.25rem) !important; }
.stApp [data-testid="stSubheader"] { margin-top: .35rem; margin-bottom: .85rem; }
.stApp [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] { min-width: 0; }

.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div { border-radius: 10px !important; }
.stApp [data-baseweb="input"] > div, .stApp [data-baseweb="textarea"] > div, .stApp [data-baseweb="select"] > div {
  background: rgba(8, 26, 60, .85) !important; border-color: rgba(82, 214, 224, .28) !important;
}
.stApp input:focus, .stApp textarea:focus { border-color: var(--aqua) !important; box-shadow: 0 0 0 2px rgba(82, 214, 224, .18) !important; }
.stApp [data-testid="stTextInput"] label, .stApp [data-testid="stTextArea"] label, .stApp [data-testid="stSelectbox"] label,
.stApp [data-testid="stMultiSelect"] label, .stApp [data-testid="stNumberInput"] label, .stApp [data-testid="stDateInput"] label,
.stApp [data-testid="stSlider"] label, .stApp [data-testid="stRadio"] > label, .stApp [data-testid="stCheckbox"] label {
  color: #d4e7ff !important; font-size: .86rem; font-weight: 600;
}
.stApp [data-testid="stExpander"] {
  border: 1px solid rgba(82, 214, 224, .26) !important; border-radius: 16px !important; background: rgba(8, 26, 60, .6);
}
.stApp [data-testid="stExpander"] summary { padding: .75rem 1rem; font-family: var(--font-head); font-weight: 700; font-size: 1.02rem; }
.stApp [data-testid="stDataFrame"], .stApp [data-testid="stTable"] {
  border: 1px solid rgba(82, 214, 224, .22); border-radius: 14px; overflow: hidden;
}
.stApp [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid rgba(82, 214, 224, .25); }
.stApp [data-testid="stTabs"] button[role="tab"] { border-radius: 10px 10px 0 0; padding: .55rem .9rem; font-family: var(--font-head); font-weight: 700; font-size: 1rem; }
.stApp [data-testid="stAlert"] { border-radius: 14px; }
.stApp [data-testid="stMetric"] {
  background: rgba(12, 37, 82, .7); border: 1px solid rgba(82, 214, 224, .2); border-radius: 14px; padding: .75rem .9rem;
}

@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .cmd-brand-small { display: none; }
  .cmd-right { justify-content: flex-start; }
  .stat-val { font-size: 26px; }
}
@media (max-width: 600px) {
  .cmd-topbar { padding: 12px; }
  .cmd-sub { font-size: 10px; }
  .tagline-pill, .live-badge { font-size: 9px; padding: 4px 8px; }
  .stat-card { min-height: 96px; padding: 11px; }
  .stat-label, .stat-foot { font-size: 10px; }
  .stat-val { font-size: 22px; }
  .wx-temp { font-size: 38px; }
}
</style>
""", unsafe_allow_html=True)

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if st.session_state["auth_user"] is None:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1.05, 1.35, 1.05])

    with center_col:
        st.markdown(f"""
        <div class="auth-card" style="text-align:center;margin-bottom:14px;">
          {logo_svg(68)}
          <div style="font-family:'Barlow Semi Condensed',sans-serif;font-size:26px;font-weight:800;color:#f8fafc;margin-top:10px;letter-spacing:.3px;">
            BALOCHISTAN TRANSPORT SAFETY SYSTEM
          </div>
          <div style="font-size:12px;color:#52d6e0;font-weight:700;letter-spacing:1px;margin-top:3px;">
            PROACTIVE TRANSPORT SAFETY & WEATHER INTELLIGENCE
          </div>
          <div style="font-size:12px;color:#cbd5e1;font-style:italic;margin-top:8px;">
            “We don’t just predict dangerous journeys. We help prevent them.”
          </div>
        </div>
        """, unsafe_allow_html=True)

        tab_signin, tab_signup = st.tabs(["🔐 Sign In (Control Room)", "📝 Sign Up (Register Officer)"])

        with tab_signin:
            with st.form("signin_form"):
                u_login = st.text_input("Username", placeholder="Enter username (default: admin)")
                p_login = st.text_input("Password", type="password", placeholder="Enter password (default: admin123)")
                btn_login = st.form_submit_button("Sign In to Command Center", use_container_width=True)

            if btn_login:
                uname_clean = u_login.strip()
                if uname_clean and p_login:
                    matched = rows("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (uname_clean,))
                    if matched:
                        user_rec = matched[0]
                        is_ok, needs_upg = verify_password(p_login, user_rec["password_hash"])
                        if is_ok:
                            if needs_upg:
                                new_h = hash_password(p_login)
                                run("UPDATE users SET password_hash=? WHERE id=?", (new_h, user_rec["id"]))
                                user_rec["password_hash"] = new_h
                            st.session_state["auth_user"] = user_rec
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please try again.")
                    else:
                        st.error("Invalid username or password. Please try again.")
                else:
                    st.warning("Please enter both username and password.")

            st.caption("Default Control Room Credentials: Username `admin` • Password `admin123`")

        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                s_fullname = st.text_input("Officer Full Name", placeholder="e.g., Capt. Tariq Mahmood")
                s_username = st.text_input("Choose Username", placeholder="e.g., tariq_nha (letters, numbers, _, .)")
                c_dept, c_role = st.columns(2)
                s_dept = c_dept.selectbox("Department / Wing", ["PDMA Balochistan", "National Highway Authority (NHA)", "Balochistan Levies Force", "Highway Police", "District Administration"])
                s_role = c_role.selectbox("Designation / Role", ["Control Room Operator", "Checkpoint Supervisor", "Regional Coordinator", "Command Officer"])
                c_p1, c_p2 = st.columns(2)
                s_pass1 = c_p1.text_input("Create Password", type="password", placeholder="Min 6 characters")
                s_pass2 = c_p2.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                btn_signup = st.form_submit_button("Create Official Account", use_container_width=True)

            if btn_signup:
                fn = s_fullname.strip()
                un = s_username.strip()
                if not (fn and un and s_pass1):
                    st.error("Please fill all required fields.")
                elif not is_valid_username(un):
                    st.error("Username must be 3–30 characters using only letters, numbers, '_', '.', or '-'.")
                elif len(s_pass1) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif s_pass1 != s_pass2:
                    st.error("Passwords do not match.")
                else:
                    exists = rows("SELECT id FROM users WHERE LOWER(username)=LOWER(?)", (un,))
                    if exists:
                        st.error("This username is already taken. Choose another username.")
                    else:
                        try:
                            new_uid = run(
                                "INSERT INTO users(full_name,username,department,role,password_hash,created_at) VALUES(?,?,?,?,?,?)",
                                (fn, un, s_dept, s_role, hash_password(s_pass1), datetime.now().strftime("%Y-%m-%d %H:%M"))
                            )
                            created_user = rows("SELECT * FROM users WHERE id=?", (new_uid,))[0]
                            st.session_state["auth_user"] = created_user
                            st.success("Account created! Entering Command Center...")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("This username is already registered.")

    st.stop()

current_user = st.session_state["auth_user"]
road_rows_all = rows("SELECT * FROM road_status")
road_lookup = {(r["route"], r["area"]): r for r in road_rows_all}
all_drivers_global = rows("SELECT * FROM drivers ORDER BY id DESC")
active_sos_global = rows("SELECT * FROM sos_incidents WHERE status='ACTIVE SOS' ORDER BY id DESC")
overdue_drivers_global = get_overdue_drivers(all_drivers_global)

if "nav_key" not in st.session_state:
    st.session_state["nav_key"] = "dash"

with st.sidebar:
    st.markdown(f"""<div class="side-brand">{logo_svg(50)}<div><div class="t1">HIGHWAY WATCH</div><div class="t2">SAFETY &amp; MONITORING</div></div></div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="side-user"><div class="k">SIGNED IN OPERATOR</div><div class="n">{current_user['full_name']}</div><div class="r">{current_user['role']} • {current_user['department']}</div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="nav-caption">OPERATIONS MENU</div>', unsafe_allow_html=True)
    sos_badge_txt = f"  ({len(active_sos_global)} ACTIVE)" if active_sos_global else ""
    nav_key = st.radio(
        "Operations Menu",
        [k for k, _, _ in NAV_ITEMS],
        key="nav_key",
        format_func=lambda k: f"{NAV_ICONS[k]}  {NAV_LABELS[k]}{sos_badge_txt if k == 'sos' else ''}",
        label_visibility="collapsed",
        help="Choose a workspace. All existing modules are available here.",
    )
    nav_choice = NAV_LABELS[nav_key]

    st.markdown("---")
    selected_corridor = st.selectbox("Active Highway Corridor", ROUTES, key="active_corridor_sel")

    st.markdown('<div style="margin-top:8px;margin-bottom:4px;font-size:11px;font-weight:800;letter-spacing:1px;color:#ffb4a3;">INSTANT EMERGENCY DISPATCH</div>', unsafe_allow_html=True)
    if st.button("🚨 SOS", type="primary", key="sidebar_instant_sos_btn", use_container_width=True):
        top_drv = all_drivers_global[0] if all_drivers_global else None
        sec_def = (top_drv.get("current_sector") if top_drv and top_drv.get("current_sector") else ROUTES_DATA[selected_corridor]["points"][0]["name"])
        code_sent = trigger_instant_sos(
            route_name=selected_corridor,
            sector_name=sec_def,
            emergency_type="Accident / Collision",
            source="Sidebar Quick SOS Button",
            notes=f"Instant SOS triggered by {current_user['full_name']} ({current_user['role']}).",
            driver_obj=top_drv,
        )
        st.error(f"🚨 {code_sent} SENT to Control Room ({selected_corridor} — {sec_def})!")
        st.rerun()


    if st.button("Sync Live Weather Feed", use_container_width=True):
        fetch_weather.clear()
        st.rerun()

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state["auth_user"] = None
        st.rerun()

    st.markdown("""<div class="side-vision"><div style="color:#52d6e0;font-weight:700;margin-bottom:3px;letter-spacing:.8px;">VISION STATEMENT</div><div style="font-style:italic;color:#d4e7ff;">“We don’t just predict dangerous journeys. We help prevent them.”</div></div>""", unsafe_allow_html=True)

now_str = datetime.now().strftime("%d %b %Y • %H:%M PKT")
st.markdown(f"""<div class="cmd-topbar">
<div class="cmd-brand">{logo_svg(48)}<div class="cmd-brand-small">Smart<br>Highway<br>Watch</div>
<div><div class="cmd-title">Balochistan Transport Safety System</div>
<div class="cmd-sub">Smart Highway &amp; Weather Intelligence • “We don’t just predict dangerous journeys. We help prevent them.” • Operator: {current_user['full_name']}</div></div></div>
<div class="cmd-right"><span class="tagline-pill">PROVINCIAL COMMAND CENTER</span>
<span style="font-size:12px;color:#9db4d6;font-family:'JetBrains Mono',monospace;">{now_str}</span>
<span class="live-badge"><span class="live-dot"></span> LIVE</span></div>
</div>""", unsafe_allow_html=True)

if active_sos_global:
    top_sos = active_sos_global[0]
    st.markdown(f"""<div class="sos-banner"><div>
<span style="background:#ee4b23;color:#fff;font-weight:900;font-size:11px;padding:3px 9px;border-radius:6px;margin-right:8px;">🚨 ACTIVE EMERGENCY SOS</span>
<strong style="color:#fff;">{top_sos['sos_code']} • {top_sos['vehicle']} ({top_sos['driver_name']})</strong>
<span style="color:#ffd5cc;font-size:13px;"> — {top_sos['emergency_type']} at <b>{top_sos['sector']}</b> ({top_sos['route']})</span></div>
<div style="font-size:12px;color:#ffd5cc;font-family:'JetBrains Mono',monospace;">Response: {top_sos['dispatched_unit']}</div></div>""", unsafe_allow_html=True)

def get_corridor_weather(route_name):
    cache = {}
    full_payloads = {}
    failed_points = []
    for pt in ROUTES_DATA[route_name]["points"]:
        try:
            res = fetch_weather(pt["lat"], pt["lon"])
            cache[pt["name"]] = res.get("current", {})
            full_payloads[pt["name"]] = res
        except Exception:
            cache[pt["name"]] = {}
            failed_points.append(pt["name"])
    return cache, full_payloads, failed_points

def compute_corridor_overall_risk(route_name, w_cache):
    max_s = 1
    worst_sector = ROUTES_DATA[route_name]["points"][0]["name"]
    for pt in ROUTES_DATA[route_name]["points"]:
        cur = w_cache.get(pt["name"], {})
        r_obj = road_lookup.get((route_name, pt["name"]), {})
        sc = compute_risk_score(cur, r_obj.get("status", "Open (Verified)"), r_obj.get("risk_score"))
        if sc >= max_s:
            max_s = sc
            worst_sector = pt["name"]
    tier, color, bg = journey_risk_tier(max_s)
    return max_s, tier, color, bg, worst_sector

if nav_choice == "Admin Control Dashboard":
    checkpoints = rows("SELECT * FROM checkpoints")
    alerts_log = rows("SELECT * FROM alerts ORDER BY id DESC")
    restricted_count = sum(1 for r in road_rows_all if "Closed" in r["status"] or "Restricted" in r["status"])

    w_cache, w_full, failed_pts = get_corridor_weather(selected_corridor)
    c_score, c_tier, c_color, c_bg, c_worst = compute_corridor_overall_risk(selected_corridor, w_cache)

    # Provincial Corridor Status Ribbon
    ribbon_items = []
    for r_n, r_info in ROUTES_DATA.items():
        r_max = 1
        for p_item in r_info["points"]:
            ro = road_lookup.get((r_n, p_item["name"]), {})
            r_max = max(r_max, compute_risk_score({}, ro.get("status", "Open (Verified)"), ro.get("risk_score")))
        t_lbl, t_col, _ = journey_risk_tier(r_max)
        active_border = f"border:1px solid {t_col};background:rgba(31,85,179,0.45);" if r_n == selected_corridor else "border:1px solid rgba(157,180,214,0.22);"
        ribbon_items.append(
            f'<span style="{active_border}padding:3px 9px;border-radius:8px;font-size:11px;display:inline-flex;align-items:center;gap:5px;">'
            f'<b style="color:#e2e8f0;">{r_info["code"]}</b>'
            f'<span style="color:{t_col};font-weight:800;">● {t_lbl}</span></span>'
        )
    st.markdown(
        f'<div class="ticker-bar">'
        f'<span style="font-weight:800;color:#52d6e0;letter-spacing:0.8px;font-size:12px;font-family:\'Barlow Semi Condensed\',sans-serif;">PROVINCIAL NETWORK STATUS:</span>'
        f'<div style="display:flex;flex-wrap:wrap;gap:7px;">{"".join(ribbon_items)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f'<div class="stat-card"><div class="stat-label">Registered Vehicles</div><div class="stat-val">{len(all_drivers_global)}</div><div class="stat-foot">Active Journeys Tracked</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="stat-card"><div class="stat-label">Active SOS Alerts</div><div class="stat-val" style="color:#ff7b6b;">{len(active_sos_global)}</div><div class="stat-foot">Emergency Beacons</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="stat-card"><div class="stat-label">Dangerous Sectors</div><div class="stat-val" style="color:#f6b93b;">{restricted_count}</div><div class="stat-foot">Caution / Blocked Roads</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="stat-card"><div class="stat-label">Overdue Checkpoints</div><div class="stat-val" style="color:#ff9a4d;">{len(overdue_drivers_global)}</div><div class="stat-foot">Auto Welfare Monitor</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div class="stat-card"><div class="stat-label">Corridor Risk Rating</div><div class="stat-val" style="color:{c_color};">{c_tier}</div><div class="stat-foot">Peak: {c_worst} ({c_score}/10)</div></div>', unsafe_allow_html=True)

    if "demo_banner_msg" not in st.session_state:
        st.session_state["demo_banner_msg"] = None

    if st.session_state["demo_banner_msg"]:
        b_type, b_text = st.session_state["demo_banner_msg"]
        if b_type == "success":
            st.success(b_text)
        else:
            st.info(b_text)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    if c_score >= 6:
        st.warning(
            f"**⚠️ {c_tier} RISK DETECTED ON {selected_corridor} (Peak Sector: {c_worst})** — "
            f"**Recommended Verified Alternative Route:** `{ROUTES_DATA[selected_corridor]['alt_route']}` "
            f"({ROUTES_DATA[selected_corridor]['alt_reason']})"
        )

    col_main, col_right = st.columns([3.15, 1.0], gap="medium")

    with col_main:
        render_balochistan_map(
            selected_corridor,
            w_cache,
            road_lookup,
            {"highways": True, "weather_radar": True, "checkpoints": True, "facilities": True},
            sos_list=active_sos_global,
            facilities_list=NEARBY_FACILITIES
        )

        # Checkpoint-by-checkpoint weather & clearance cards for the active corridor
        pts_list = ROUTES_DATA[selected_corridor]["points"]
        wx_cards = []
        for pt_item in pts_list:
            p_cur = w_cache.get(pt_item["name"], {})
            p_robj = road_lookup.get((selected_corridor, pt_item["name"]), {})
            p_status = p_robj.get("status", "Open (Verified)")
            p_sc = compute_risk_score(p_cur, p_status, p_robj.get("risk_score"))
            p_tier, p_cname, p_css = risk_tier_label(p_sc)
            has_p = bool(p_cur)
            icon_svg = wx_icon_svg(p_cur.get("weather_code") if has_p else None)
            t_val = safe_float(p_cur.get("temperature_2m"))
            t_p = f"{t_val:.0f}°C" if t_val is not None else "—"
            w_val = safe_float(p_cur.get("wind_speed_10m"))
            w_p = f"W: {w_val:.0f} km/h {wind_compass(p_cur.get('wind_direction_10m'))}".strip() if w_val is not None else "W: —"
            wx_cards.append(
                f'<div class="wx-card"><div class="wx-top"><span class="wx-name">{pt_item["name"]}</span><span class="wx-elev">{pt_item["elevation"]}</span></div>'
                f'<div class="wx-mid">{icon_svg}<span class="wx-temp">{t_p}</span></div>'
                f'<div class="wx-wind">{WIND_ICON_SVG}<span>{w_p}</span></div>'
                f'<div class="wx-foot {p_css}">{pt_item["name"]}: {p_tier} ({p_cname})</div></div>'
            )
        st.markdown(
            f'<div class="wx-head"><span class="l">{selected_corridor.upper()} — multilingual alerts and dangerous routes</span>'
            f'<span class="wx-pill">Journey Risk Score: <b style="color:{c_color};">{c_tier} ({c_score}/10)</b></span></div>'
            f'<div class="wx-grid">{"".join(wx_cards)}</div>',
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        hub_point = ROUTES_DATA[selected_corridor]["points"][-1]["name"]
        hub_cur = w_cache.get(hub_point, {})
        hub_road_obj = road_lookup.get((selected_corridor, hub_point), {})
        hub_road = hub_road_obj.get("status", "Open (Verified)")

        wind_f = safe_float(hub_cur.get("wind_speed_10m"))
        rain_f = safe_float(hub_cur.get("precipitation"))
        press_f = safe_float(hub_cur.get("surface_pressure"))
        hum_f = safe_float(hub_cur.get("relative_humidity_2m"))

        wind_disp = f"{wind_f:.1f}" if wind_f is not None else "—"
        rain_disp = f"{rain_f:.1f}" if rain_f is not None else "—"
        press_disp = f"{int(press_f)}" if press_f is not None else "—"
        hum_disp = f"{int(hum_f)}%" if hum_f is not None else "—"

        r_score = compute_risk_score(hub_cur, hub_road, hub_road_obj.get("risk_score"))
        r_tier, r_color, _ = journey_risk_tier(r_score)

        g1, g2, g3, g4, g5 = st.columns(5)
        gauges = [
            (g1, "WIND SPEED", wind_disp, "km/h", "#52d6e0", min(int((wind_f or 0) * 2), 100)),
            (g2, "RAINFALL", rain_disp, "mm/hr", "#9be15d", min(int((rain_f or 0) * 15), 100)),
            (g3, "PRESSURE", press_disp, "hPa", "#a5b4fc", min(max(int(((press_f or 1012) - 960) * 1.1), 10), 100)),
            (g4, "HUMIDITY", hum_disp, "Relative", "#38bdf8", min(max(int(hum_f or 0), 0), 100)),
            (g5, "JOURNEY RISK", r_tier, f"Score {r_score}/10", r_color, r_score * 10),
        ]
        for col_obj, title, val, sub, color, pct in gauges:
            col_obj.markdown(f"""<div class="gauge-box"><div class="gauge-title">{title}</div><div class="gauge-ring" style="background: radial-gradient(closest-side, #0c2352 76%, transparent 80% 100%), conic-gradient({color} {pct}%, #1c3a6e 0);">{val}</div><div class="gauge-sub">{sub}</div></div>""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="qa-title">QUICK ACTIONS</div>', unsafe_allow_html=True)

        # Big emergency SOS button (same one-click SOS as the old Fast Desk)
        if st.button("EMERGENCY  \nSOS", type="primary", key="dash_fast_sos_btn", help="One-click emergency SOS for the active corridor"):
            top_drv = all_drivers_global[0] if all_drivers_global else None
            sec_def = ROUTES_DATA[selected_corridor]["points"][0]["name"]
            s_sent = trigger_instant_sos(
                route_name=selected_corridor,
                sector_name=sec_def,
                emergency_type="Accident / Collision",
                source="Admin / Check Post Fast Desk SOS",
                notes=f"Fast Desk SOS by {current_user['full_name']} ({current_user['role']}).",
                driver_obj=top_drv,
            )
            st.error(f"🚨 SOS {s_sent} Active at {sec_def} ({selected_corridor})!")
            st.rerun()

        qa1, qa2, qa3 = st.columns(3)
        qa1.button("📞", key="qa_phone", help="Open Emergency SOS & Welfare", on_click=_go_nav, args=("sos",), use_container_width=True)
        qa2.button("🔔", key="qa_bell", help="Open Multilingual Alert & Voice", on_click=_go_nav, args=("alert",), use_container_width=True)
        qa3.button("✉️", key="qa_mail", help="Open Road Clearance & Dispatch Logs", on_click=_go_nav, args=("road",), use_container_width=True)

        with st.expander("⚡ Fast Desk — Check-In, Road Status & Resolve", expanded=True):
            st.markdown('<div style="font-size:12px;font-weight:800;color:#52d6e0;margin-bottom:4px;letter-spacing:.8px;">CHECK POST QR / SAFE HALT</div>', unsafe_allow_html=True)
            if all_drivers_global:
                cp_drv_map = {f"{d['vehicle']} • {d['name']}": d for d in all_drivers_global}
                cp_sel = cp_drv_map[st.selectbox("Select Vehicle", list(cp_drv_map.keys()), key="fast_cp_drv", label_visibility="collapsed")]
                cpa, cpb = st.columns(2)
                if cpa.button("✅ Gate Scan", key="fast_gate_scan", use_container_width=True):
                    pts_c = ROUTES_DATA[cp_sel["route"]]["points"]
                    names_c = [p["name"] for p in pts_c]
                    cur_c = cp_sel.get("next_checkpoint") or names_c[0]
                    idx_c = names_c.index(cur_c) if cur_c in names_c else 0
                    nxt_c = names_c[min(idx_c + 1, len(names_c) - 1)]
                    now_c = datetime.now().strftime("%Y-%m-%d %H:%M")
                    eta_c = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                    run("UPDATE drivers SET status='Verified at Gate', current_sector=?, next_checkpoint=?, expected_eta=?, last_checkin=? WHERE id=?",
                        (cur_c, nxt_c, eta_c, now_c, cp_sel["id"]))
                    st.success(f"{cp_sel['vehicle']} verified at {cur_c} -> Next: {nxt_c}")
                    st.rerun()
                if cpb.button("🛡️ Halt Safe", key="fast_halt_safe", use_container_width=True):
                    run("UPDATE drivers SET status='Halted at Safe Haven (Prevented)', last_checkin=? WHERE id=?",
                        (datetime.now().strftime("%Y-%m-%d %H:%M"), cp_sel["id"]))
                    st.info(f"{cp_sel['vehicle']} halted safely.")
                    st.rerun()

            st.markdown('<div style="font-size:12px;font-weight:800;color:#52d6e0;margin:10px 0 4px 0;letter-spacing:.8px;">QUICK ROAD STATUS</div>', unsafe_allow_html=True)
            corr_roads = [r for r in road_rows_all if r["route"] == selected_corridor] or road_rows_all
            if corr_roads:
                rd_map = {f"{r['area']} ({r['status'].split(' ')[0]})": r for r in corr_roads}
                rd_sel = rd_map[st.selectbox("Select Sector", list(rd_map.keys()), key="fast_rd_sec", label_visibility="collapsed")]
                st_choice = st.selectbox("New Status", ROAD_STATUSES, key="fast_rd_status", label_visibility="collapsed")
                if st.button("💾 Update Sector", key="fast_rd_save", use_container_width=True):
                    r_sc_new = 10 if "Closed" in st_choice else (6 if "Restricted" in st_choice else 2)
                    run("UPDATE road_status SET status=?, risk_score=?, verified_by=?, updated_at=? WHERE id=?",
                        (st_choice, r_sc_new, current_user["full_name"], datetime.now().strftime("%Y-%m-%d %H:%M"), rd_sel["id"]))
                    st.success(f"{rd_sel['area']} -> {st_choice}")
                    st.rerun()

            st.markdown('<div style="font-size:12px;font-weight:800;color:#f6b93b;margin:10px 0 4px 0;letter-spacing:.8px;">RESOLVE TOP SOS / FEED</div>', unsafe_allow_html=True)
            if active_sos_global:
                top_s = active_sos_global[0]
                if st.button(f"✅ Resolve {top_s['sos_code']} ({top_s['vehicle']})", key="fast_res_top_sos", use_container_width=True):
                    run("UPDATE sos_incidents SET status='RESOLVED', dispatched_unit='Rescue Completed' WHERE id=?", (top_s["id"],))
                    if top_s.get("driver_id"):
                        run("UPDATE drivers SET status='Safe — Assisted' WHERE id=?", (top_s["driver_id"],))
                    st.success(f"{top_s['sos_code']} resolved!")
                    st.rerun()
            else:
                st.caption("No active SOS alerts in queue.")
            if st.button("🔄 Refresh Weather", key="fast_sync_weather", use_container_width=True):
                fetch_weather.clear()
                st.rerun()

        # Live monitor panel (one real wrapping card)
        panel = ['<div class="side-panel-card">', '<div class="panel-h" style="color:#ff8a78;">🚨 LIVE SOS &amp; WELFARE MONITOR</div>']
        if active_sos_global:
            for s in active_sos_global[:3]:
                panel.append(
                    f'<div class="notif-item danger"><div style="display:flex;justify-content:space-between;gap:6px;font-size:11px;font-weight:800;">'
                    f'<span style="color:#ffc9bf;">{s["sos_code"]} • {s["vehicle"]}</span><span style="color:#ff7b6b;">{s["emergency_type"]}</span></div>'
                    f'<div style="font-size:11px;color:#f1f5f9;margin-top:2px;"><b>{s["driver_name"]}</b> at <b>{s["sector"]}</b></div>'
                    f'<div style="font-size:10px;color:#cbd5e1;margin-top:2px;">{s.get("details","")}</div></div>'
                )
        else:
            panel.append('<div class="notif-item safe"><div style="font-size:11px;color:#9be15d;font-weight:700;">All SOS beacons clear.</div></div>')

        if overdue_drivers_global:
            panel.append('<div class="panel-h" style="color:#ff9a4d;margin-top:10px;">⏱️ AUTO WELFARE CHECK (MISSED ETA)</div>')
            for od in overdue_drivers_global[:3]:
                panel.append(
                    f'<div class="notif-item"><div style="display:flex;justify-content:space-between;gap:6px;font-size:11px;font-weight:800;">'
                    f'<span style="color:#fed7aa;">{od["vehicle"]} ({od["name"]})</span><span style="color:#ff9a4d;">+{od["mins_late"]}m Late</span></div>'
                    f'<div style="font-size:11px;color:#9db4d6;margin-top:2px;">Expected at <b>{od.get("next_checkpoint","Checkpoint")}</b> ({od["route"]})</div></div>'
                )

        panel.append('<div class="panel-h" style="color:#52d6e0;margin-top:10px;">🚛 ACTIVE FLEET STATUS</div>')
        for d in all_drivers_global[:4]:
            st_d = d.get("status") or "Active on Route"
            cls_d = "danger" if ("Overdue" in st_d or "SOS" in st_d) else ("safe" if ("Safe" in st_d or "Verified" in st_d or "Halted" in st_d) else "")
            panel.append(
                f'<div class="notif-item {cls_d}"><div style="display:flex;justify-content:space-between;gap:6px;font-size:11px;font-weight:700;">'
                f'<span style="color:#f8fafc;">{d["vehicle"]} • {d["name"]}</span><span style="color:#9be15d;">{st_d}</span></div>'
                f'<div style="font-size:10px;color:#9db4d6;margin-top:2px;">{d["route"]} • Sector: {d.get("current_sector","Quetta")}</div></div>'
            )

        panel.append('<div class="panel-h" style="color:#9be15d;margin-top:10px;">📡 RECENT DISPATCHED ALERTS</div>')
        if alerts_log:
            for al_item in alerts_log[:2]:
                panel.append(
                    f'<div class="notif-item safe"><div style="display:flex;justify-content:space-between;gap:6px;font-size:10px;font-weight:700;color:#8fd3ff;">'
                    f'<span>{al_item["route"]} ({al_item.get("language","Urdu")})</span><span>{al_item["created_at"]}</span></div>'
                    f'<div style="font-size:11px;color:#e2e8f0;margin-top:3px;">{al_item["message"][:95]}...</div></div>'
                )
        else:
            panel.append('<div style="font-size:12px;color:#9db4d6;">No alerts dispatched yet.</div>')
        panel.append('</div>')
        st.markdown("".join(panel), unsafe_allow_html=True)

    with st.expander("🎯 Live Safety Demonstration Simulator (Quetta → Karachi N-25)", expanded=bool(st.session_state["demo_banner_msg"])):
        st.markdown("""
        **Demonstrate the complete preventive safety lifecycle in 1 click:**
        1. Registers Truck **QTA-9921 (Driver: Ustad Gul Muhammad)** at Quetta Toll Plaza on **Quetta–Karachi (N-25)**.
        2. Triggers severe weather/flash-flood alert at **Kalat & Khuzdar** (`SEVERE` Journey Risk).
        3. Sends multilingual SMS/Voice warning recommending halt at **Mastung NHA Safe Haven** + suggests **N-65 Sibi-Sukkur Alternative Route**.
        4. Updates vehicle status to **Halted at Safe Haven (Prevented Hazard)** on the Admin Dashboard.
        """)
        sim_c1, sim_c2 = st.columns([1.2, 1])
        if sim_c1.button("▶️ Run Live Quetta → Karachi Preventive Demo", key="btn_run_demo", use_container_width=True):
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
            eta_s = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
            existing_demo = rows("SELECT id FROM drivers WHERE vehicle='QTA-9921'")
            if existing_demo:
                demo_id = existing_demo[0]["id"]
                run(
                    "UPDATE drivers SET status='Halted at Safe Haven (Prevented)', current_sector='Mastung', next_checkpoint='Kalat', expected_eta=?, last_checkin=? WHERE id=?",
                    (eta_s, now_s, demo_id)
                )
            else:
                demo_id = run(
                    """INSERT INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("BHW-9921", "Ustad Gul Muhammad", "0300-9214455", "QTA-9921", "Cargo Truck", "Quetta–Karachi (N-25)", "Urdu",
                     "Halted at Safe Haven (Prevented)", "Mastung", "Kalat", eta_s, now_s, now_s)
                )
            run(
                "UPDATE road_status SET status='Restricted — Caution', risk_score=9, authority_note='Severe rain & flash flood risk near Kalat & Khuzdar. Heavy trucks advised to halt at Mastung Safe Haven.', updated_at=? WHERE route='Quetta–Karachi (N-25)' AND area IN ('Kalat','Khuzdar')",
                (now_s,)
            )
            run("DELETE FROM alerts WHERE driver_id=?", (demo_id,))
            run(
                "INSERT INTO alerts(driver_id,route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (demo_id, "Quetta–Karachi (N-25)", "Urdu", "Emergency",
                 "ہنگامی انتباہ (QTA-9921): قلات اور خضدار میں شدید بارش کے باعث خطرہ شدید (SEVERE) ہے۔ براہِ کرم مستونگ NHA سیف ہیون پر رک جائیں یا سبی-سکھر متبادل راستہ اختیار کریں۔",
                 "SMS Gateway, Automated Voice Call (IVR)", "Delivered — Truck Halted Safely", now_s)
            )
            st.session_state["demo_banner_msg"] = (
                "success",
                "✅ Live Demo Executed! Truck QTA-9921 registered on N-25, warned via Urdu SMS & IVR Voice, and safely halted at Mastung Safe Haven (Hazard Prevented)."
            )
            st.rerun()

        if sim_c2.button("🔄 Reset Demo Scenario", key="btn_reset_demo", use_container_width=True):
            existing_demo = rows("SELECT id FROM drivers WHERE vehicle='QTA-9921'")
            for ed in existing_demo:
                run("DELETE FROM alerts WHERE driver_id=?", (ed["id"],))
            run("DELETE FROM drivers WHERE vehicle='QTA-9921'")
            run("UPDATE road_status SET status='Open (Verified)', risk_score=2, authority_note='Normal traffic flow; regular patrol active.' WHERE route='Quetta–Karachi (N-25)' AND area IN ('Kalat','Khuzdar')")
            st.session_state["demo_banner_msg"] = (
                "info",
                "🔄 Demo scenario reset to normal baseline."
            )
            st.rerun()

elif nav_choice.startswith("Emergency SOS & Welfare"):
    st.subheader("🚨 One-Tap Driver Emergency SOS & Automatic Welfare Monitoring")
    c_sos_trigger, c_sos_board = st.columns([1.05, 1.55], gap="large")

    with c_sos_trigger:
        st.markdown('<div class="side-panel-card"><div style="font-weight:800;font-size:15px;color:#fca5a5;margin-bottom:6px;">Driver One-Button Emergency SOS</div><div style="font-size:12px;color:#94a3b8;margin-bottom:10px;">Instantly transmits vehicle plate, GPS coordinates, and emergency category to PDMA/Levies Control Room.</div>', unsafe_allow_html=True)
        with st.form("driver_sos_form", clear_on_submit=True):
            if all_drivers_global:
                drv_choices = {f"{d['vehicle']} • {d['name']} ({d['route']})": d for d in all_drivers_global}
                chosen_drv = drv_choices[st.selectbox("Select Registered Vehicle / Driver", list(drv_choices.keys()))]
                def_route_idx = ROUTES.index(chosen_drv["route"]) if chosen_drv["route"] in ROUTES else 0
            else:
                chosen_drv = None
                def_route_idx = 0

            sos_route = st.selectbox("Highway Corridor", ROUTES, index=def_route_idx)
            sos_sector = st.selectbox("Nearest Checkpoint / Location", [p["name"] for p in ROUTES_DATA[sos_route]["points"]])
            sos_type = st.selectbox("Emergency Category", SOS_TYPES)
            sos_notes = st.text_input("Brief Situation Note (Optional)", placeholder="e.g., Brake failure on descent / Medical emergency")
            send_sos = st.form_submit_button("🚨 TRIGGER EMERGENCY SOS NOW", use_container_width=True)

        if send_sos:
            pt_obj = next((p for p in ROUTES_DATA[sos_route]["points"] if p["name"] == sos_sector), ROUTES_DATA[sos_route]["points"][0])
            s_code = generate_unique_sos_code()
            d_id = chosen_drv["id"] if chosen_drv else None
            d_name = chosen_drv["name"] if chosen_drv else "Unregistered Motorist"
            d_veh = chosen_drv["vehicle"] if chosen_drv else "TEMP-SOS"
            d_ph = chosen_drv["phone"] if chosen_drv else "0300-0000000"
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M")

            run(
                """INSERT INTO sos_incidents
                (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s_code, d_id, d_name, d_veh, d_ph, sos_route, sos_sector, pt_obj["lat"], pt_obj["lon"],
                 sos_type, "Driver One-Tap SOS", sos_notes.strip() or f"Driver pressed Emergency SOS at {sos_sector}.",
                 "ACTIVE SOS", "Rescue 1122 & Levies Dispatched", now_s)
            )
            if d_id:
                run("UPDATE drivers SET status='ACTIVE SOS', current_sector=? WHERE id=?", (sos_sector, d_id))
            st.error(f"🚨 SOS {s_code} TRANSMITTED! Control Room alerted with GPS ({pt_obj['lat']}, {pt_obj['lon']}) for {d_veh}.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_sos_board:
        st.markdown("### Active Control Room SOS Queue")
        all_sos = rows("SELECT * FROM sos_incidents ORDER BY id DESC")
        if all_sos:
            for item in all_sos:
                is_act = item["status"] == "ACTIVE SOS"
                border_c = "#ef4444" if is_act else "#10b981"
                st.markdown(f"""
                <div style="background:#0b1829;border:1px solid {border_c};border-left:5px solid {border_c};border-radius:12px;padding:12px 16px;margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:800;font-size:14px;color:#f8fafc;">{item['sos_code']} • {item['vehicle']} ({item['driver_name']})</span>
                    <span style="background:{border_c};color:#fff;font-size:10px;font-weight:800;padding:3px 9px;border-radius:999px;">{item['status']}</span>
                  </div>
                  <div style="font-size:12px;color:#cbd5e1;margin-top:4px;">
                    <b>Type:</b> {item['emergency_type']} | <b>Sector:</b> {item['sector']} ({item['route']}) | <b>Phone:</b> {item['phone']}
                  </div>
                  <div style="font-size:11px;color:#94a3b8;margin-top:3px;">
                    GPS: {item.get('lat')}, {item.get('lon')} • Source: {item.get('source')} • {item.get('details')}
                  </div>
                </div>
                """, unsafe_allow_html=True)
                if is_act:
                    b1, b2 = st.columns([1.3, 1])
                    if b1.button(f"✅ Mark {item['sos_code']} Resolved & Safe", key=f"res_{item['id']}", use_container_width=True):
                        run("UPDATE sos_incidents SET status='RESOLVED', dispatched_unit='Rescue Completed' WHERE id=?", (item["id"],))
                        if item.get("driver_id"):
                            run("UPDATE drivers SET status='Safe — Assisted' WHERE id=?", (item["driver_id"],))
                        st.rerun()

        st.markdown("### ⏱️ Automatic Checkpoint Monitoring (Overdue Welfare Flagging)")
        if overdue_drivers_global:
            for od in overdue_drivers_global:
                st.warning(
                    f"**Welfare Flag:** Vehicle **{od['vehicle']}** ({od['name']}, {od['phone']}) is **{od['mins_late']} mins overdue** "
                    f"at **{od.get('next_checkpoint')}** on **{od['route']}**."
                )
                c_w1, c_w2 = st.columns(2)
                if c_w1.button(f"🚨 Escalate {od['vehicle']} to Auto-SOS", key=f"esc_{od['id']}", use_container_width=True):
                    pt_o = next((p for p in ROUTES_DATA[od["route"]]["points"] if p["name"] == od.get("current_sector")), ROUTES_DATA[od["route"]]["points"][0])
                    s_c = generate_unique_sos_code()
                    now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                    run(
                        """INSERT INTO sos_incidents
                        (sos_code,driver_id,driver_name,vehicle,phone,route,sector,lat,lon,emergency_type,source,details,status,dispatched_unit,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (s_c, od["id"], od["name"], od["vehicle"], od["phone"], od["route"], od.get("current_sector", "En Route"),
                         pt_o["lat"], pt_o["lon"], "Missed Checkpoint / Welfare Check", "Automatic Journey Monitor",
                         f"Vehicle missed {od.get('next_checkpoint')} ETA by {od['mins_late']} mins.", "ACTIVE SOS", "Patrol Welfare Check", now_s)
                    )
                    run("UPDATE drivers SET status='ACTIVE SOS' WHERE id=?", (od["id"],))
                    st.rerun()
                if c_w2.button(f"✓ Confirm Driver Safe ({od['vehicle']})", key=f"ok_{od['id']}", use_container_width=True):
                    new_eta = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                    run("UPDATE drivers SET status='Active on Route', expected_eta=?, last_checkin=? WHERE id=?", (new_eta, datetime.now().strftime("%Y-%m-%d %H:%M"), od["id"]))
                    st.rerun()
        else:
            st.success("All active vehicles are within expected checkpoint arrival windows.")

elif nav_choice == "Driver Portal & Journey Risk":
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")
    checkpoints = rows("SELECT * FROM checkpoints ORDER BY id ASC")

    st.subheader("Pre-Journey Risk Assessment & Vehicle Registration")

    jr1, jr2 = st.columns([1.15, 1.35], gap="large")
    with jr1:
        st.markdown('<div class="side-panel-card"><div style="font-weight:800;font-size:15px;margin-bottom:6px;">🧭 Journey Risk Score Calculator</div><div style="font-size:12px;color:#94a3b8;margin-bottom:10px;">Evaluates Low, Moderate, High, or Severe journey risk using live Open-Meteo weather + verified NHA/PDMA road clearance.</div>', unsafe_allow_html=True)
        calc_route = st.selectbox("Select Planned Corridor", ROUTES, index=ROUTES.index(selected_corridor), key="calc_rt")
        w_calc, _, _ = get_corridor_weather(calc_route)
        j_score, j_tier, j_color, j_bg, j_worst = compute_corridor_overall_risk(calc_route, w_calc)

        st.markdown(f"""
        <div style="background:{j_bg};border:2px solid {j_color};border-radius:14px;padding:16px;text-align:center;margin-top:8px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:1px;color:#cbd5e1;">OVERALL JOURNEY RISK RATING</div>
          <div style="font-size:32px;font-weight:900;color:{j_color};margin:4px 0;font-family:'JetBrains Mono',monospace;">{j_tier} ({j_score}/10)</div>
          <div style="font-size:12px;color:#f1f5f9;">Critical Sector: <b>{j_worst}</b> • Distance: {ROUTES_DATA[calc_route]['distance']}</div>
        </div>
        """, unsafe_allow_html=True)
        if j_score >= 6:
            st.info(f"**Preventive Detour:** `{ROUTES_DATA[calc_route]['alt_route']}`")
        st.markdown("</div>", unsafe_allow_html=True)

    with jr2:
        st.markdown("#### Register Vehicle & Start Monitored Journey")
        with st.form("driver_reg_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d_name = c1.text_input("Driver Full Name", placeholder="e.g., Muhammad Aslam")
            d_phone = c2.text_input("Mobile Number (SMS/Voice)", placeholder="0300-XXXXXXX")
            c3, c4 = st.columns(2)
            d_veh = c3.text_input("Vehicle Plate No.", placeholder="QTA-9081")
            d_vtype = c4.selectbox("Vehicle Category", ["Cargo Truck", "Passenger Coach", "Oil Tanker", "Ambulance / Emergency", "Private SUV / Car"])
            c5, c6, c7 = st.columns(3)
            d_route = c5.selectbox("Assigned Corridor", ROUTES)
            d_lang = c6.selectbox("Alert Language", LANGUAGES)
            eta_hrs = c7.number_input("Next Checkpoint ETA (hrs)", min_value=1, max_value=12, value=2)
            submitted = st.form_submit_button("Register & Issue Digital QR Pass", use_container_width=True)

        if submitted:
            fn_d = d_name.strip()
            ph_d = d_phone.strip()
            vh_d = re.sub(r"\s+", "", d_veh.strip().upper())
            if not (fn_d and ph_d and vh_d):
                st.error("Please fill Driver Name, Mobile Number, and Vehicle Plate.")
            elif not is_valid_pk_phone(ph_d):
                st.error("Please enter a valid Pakistani mobile number (e.g., 0300-1234567).")
            elif not is_valid_plate(vh_d):
                st.error("Please enter a valid vehicle plate number (e.g., QTA-9081).")
            else:
                d_code = generate_unique_driver_code()
                pts = ROUTES_DATA[d_route]["points"]
                start_sec = pts[0]["name"]
                next_sec = pts[1]["name"] if len(pts) > 1 else pts[0]["name"]
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                eta_s = (datetime.now() + timedelta(hours=int(eta_hrs))).strftime("%Y-%m-%d %H:%M")
                run(
                    """INSERT INTO drivers(driver_code,name,phone,vehicle,vehicle_type,route,language,status,current_sector,next_checkpoint,expected_eta,last_checkin,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (d_code, fn_d, ph_d, vh_d, d_vtype, d_route, d_lang, "Active on Route", start_sec, next_sec, eta_s, now_s, now_s)
                )
                st.success(f"Vehicle registered! Pass ID: {d_code} • Next Checkpoint: {next_sec} (ETA {eta_s})")
                st.rerun()

    st.markdown("---")
    col_tbl, col_qr = st.columns([1.65, 1.0], gap="large")
    with col_tbl:
        st.markdown("#### Active Monitored Vehicles")
        if drivers:
            df_drv = pd.DataFrame(drivers)[["driver_code", "name", "vehicle", "route", "current_sector", "next_checkpoint", "expected_eta", "status"]]
            df_drv.columns = ["Pass ID", "Driver", "Plate", "Corridor", "Current Sector", "Next Gate", "Expected ETA", "Status"]
            st.dataframe(df_drv, use_container_width=True, hide_index=True)

    with col_qr:
        st.markdown("#### Checkpoint QR Scan & Safe Haven Check-In")
        if drivers:
            label_to_driver = {f"{d.get('driver_code')} • {d['name']} ({d['vehicle']})": d for d in drivers}
            sel_d = label_to_driver[st.selectbox("Select Vehicle", list(label_to_driver.keys()))]
            code_disp = sel_d.get("driver_code") or f"BHW-{sel_d['id']}"
            qr_payload = urllib.parse.quote(f"BHW-PASS|{code_disp}|{sel_d['name']}|{sel_d['vehicle']}|{sel_d['route']}")
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=155x155&data={qr_payload}&bgcolor=0b1829&color=2dd4bf"

            st.markdown(f"""
            <div class="side-panel-card" style="text-align:center;">
              <div style="font-size:11px;color:#2dd4bf;font-weight:700;">DIGITAL CHECKPOINT PASS</div>
              <div style="font-size:16px;font-weight:800;margin:3px 0;">{sel_d['name']} ({sel_d['vehicle']})</div>
              <img src="{qr_url}" alt="QR Pass" style="border-radius:10px;border:2px solid #14b8a6;padding:5px;background:#0b1829;margin:6px 0;"/>
              <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#38bdf8;">{code_disp} • {sel_d['language']}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚨 SOS", type="primary", key=f"cp_tab_sos_{sel_d['id']}", use_container_width=True):
                s_cp = trigger_instant_sos(
                    route_name=sel_d["route"],
                    sector_name=sel_d.get("current_sector") or ROUTES_DATA[sel_d["route"]]["points"][0]["name"],
                    emergency_type="Accident / Collision",
                    source="Check Post Officer SOS Button",
                    notes=f"Check post SOS for {sel_d['vehicle']} ({sel_d['name']}) by {current_user['full_name']}.",
                    driver_obj=sel_d,
                )
                st.error(f"🚨 SOS {s_cp} dispatched for {sel_d['vehicle']}!")
                st.rerun()

            b_scan, b_halt = st.columns(2)
            if b_scan.button("✅ Checkpoint QR Scan", use_container_width=True):
                pts = ROUTES_DATA[sel_d["route"]]["points"]
                names = [p["name"] for p in pts]
                cur_s = sel_d.get("next_checkpoint") or names[0]
                idx_n = names.index(cur_s) if cur_s in names else 0
                nxt_s = names[min(idx_n + 1, len(names) - 1)]
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                eta_s = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                run("UPDATE drivers SET status='Verified at Gate', current_sector=?, next_checkpoint=?, expected_eta=?, last_checkin=? WHERE id=?",
                    (cur_s, nxt_s, eta_s, now_s, sel_d["id"]))
                st.success(f"Scanned at {cur_s}! Next ETA: {nxt_s}")
                st.rerun()
            if b_halt.button("🛡️ Halt at Safe Haven", use_container_width=True):
                run("UPDATE drivers SET status='Halted at Safe Haven (Prevented)' WHERE id=?", (sel_d["id"],))
                st.info("Vehicle marked safely halted at rest area.")
                st.rerun()

elif nav_choice == "Highway Map & Safe Routes":
    st.subheader("Alternative Safe Routes & Roadside Emergency Facilities")
    c_opt, c_map = st.columns([1.15, 2.85], gap="medium")

    with c_opt:
        map_route = st.selectbox("Select Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        w_cache, _, _ = get_corridor_weather(map_route)
        m_score, m_tier, m_color, m_bg, m_worst = compute_corridor_overall_risk(map_route, w_cache)

        st.markdown(f"""
        <div style="background:{m_bg};border:1px solid {m_color};border-radius:12px;padding:12px;margin-bottom:10px;">
          <div style="font-size:10px;font-weight:800;color:{m_color};">CORRIDOR RISK RATING: {m_tier} ({m_score}/10)</div>
          <div style="font-size:12px;font-weight:700;color:#f8fafc;margin-top:4px;">Verified Alternative Safe Route:</div>
          <div style="font-size:11px;color:#5eead4;margin-top:2px;">{ROUTES_DATA[map_route]['alt_route']}</div>
          <div style="font-size:10px;color:#cbd5e1;margin-top:4px;">{ROUTES_DATA[map_route]['alt_reason']}</div>
        </div>
        """, unsafe_allow_html=True)

        show_fac = st.checkbox("Show Hospitals, Fuel, Workshops & Safe Havens", value=True)
        show_all_fac = st.checkbox("Show Facilities Across All Corridors", value=False)
        fac_filter = st.selectbox("Filter Facility Type", ["All Types", "Hospital / Trauma", "Safe Rest Area", "Petrol / Fuel", "Repair Workshop"])

        st.markdown("**Nearby Verified Facilities**")
        filtered_facs = [
            f for f in NEARBY_FACILITIES
            if (show_all_fac or f["route"] == map_route)
            and (fac_filter == "All Types" or f["type"] == fac_filter)
        ]
        for fc in filtered_facs:
            st.markdown(f"""
            <div class="notif-item safe">
              <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:800;">
                <span style="color:#f8fafc;">{fc['name']}</span>
                <span style="color:#38bdf8;">{fc['type']}</span>
              </div>
              <div style="font-size:11px;color:#2dd4bf;margin-top:2px;">Sector: {fc['sector']} • 📞 {fc['phone']}</div>
              <div style="font-size:10px;color:#94a3b8;">{fc['notes']}</div>
            </div>
            """, unsafe_allow_html=True)

    with c_map:
        render_balochistan_map(
            map_route,
            w_cache,
            road_lookup,
            {"highways": True, "weather_radar": True, "checkpoints": True, "facilities": show_fac, "all_facilities": show_all_fac},
            sos_list=active_sos_global,
            facilities_list=filtered_facs
        )

elif nav_choice == "Multilingual Alert & Voice":
    st.subheader("Multilingual Emergency & Preventive Alerts (Urdu • English • Pashto • Balochi)")
    drivers = rows("SELECT * FROM drivers ORDER BY id DESC")

    c_left, c_right = st.columns([1.15, 1.35], gap="large")
    with c_left:
        target_mode = st.radio("Target Audience", ["All Drivers on Corridor", "Individual Registered Driver"], horizontal=True)
        al_route = st.selectbox("Highway Corridor", ROUTES, index=ROUTES.index(selected_corridor))
        al_area = st.selectbox("Checkpoint / Sector", [p["name"] for p in ROUTES_DATA[al_route]["points"]])
        al_lang = st.selectbox("Broadcast Language (4 Languages)", LANGUAGES)
        al_channel = st.multiselect("Dispatch Channels", ["SMS Gateway", "Automated Voice Call (IVR)", "Checkpoint Display"], default=["SMS Gateway", "Automated Voice Call (IVR)"])

        sel_driver_id = None
        if target_mode == "Individual Registered Driver":
            if drivers:
                d_opts = {f"{d.get('driver_code')} • {d['name']} ({d['phone']})": d for d in drivers}
                chosen_d = d_opts[st.selectbox("Select Driver", list(d_opts.keys()))]
                sel_driver_id = chosen_d["id"]
            else:
                st.warning("No registered drivers found.")

    with c_right:
        w_cache, _, _ = get_corridor_weather(al_route)
        cur_w = w_cache.get(al_area, {})
        has_w = cur_w is not None and cur_w.get("weather_code") is not None
        w_en, w_ur, _, _ = weather_info(cur_w.get("weather_code")) if has_w else ("Clear Sky", "صاف موسم", "", 1)
        road_st = road_lookup.get((al_route, al_area), {}).get("status", "Open (Verified)")

        msg_body, travel_guidance = generate_multilingual_alert(al_area, al_route, w_en, w_ur, road_st, al_lang)
        edited_msg = st.text_area(f"{al_lang} Alert Message Preview", value=msg_body, height=110)

        box_cls = "ltr-box" if al_lang == "English" else "urdu-box"
        st.markdown(f'<div class="{box_cls}">{edited_msg}</div>', unsafe_allow_html=True)
        st.info(f"**Preventive Travel Guidance:** {travel_guidance}")

        spoken_preview_text, _ = to_phonetic_tts_script(edited_msg, al_lang)
        mp3_bytes = synthesize_voice_mp3(edited_msg, al_lang)
        custom_voice = get_custom_voice_sample(al_lang)

        with st.expander(f"🎙️ Apni Aawaz (Custom Voice Sample — {al_lang}) Record / Upload Karein", expanded=False):
            st.caption("Apni aawaz ka 5–10 sec ka sample record ya upload karein taake aapki aawaz ka sample app mein save rahe aur IVR/preview mein play ho sake.")
            rec_audio = None
            if hasattr(st, "audio_input"):
                rec_audio = st.audio_input(f"Record Your Voice ({al_lang})", key=f"rec_voice_{al_lang}")
            up_audio = st.file_uploader(
                f"Ya Audio File Upload Karein ({al_lang})",
                type=["wav", "mp3", "ogg", "m4a"],
                key=f"up_voice_{al_lang}"
            )
            if rec_audio is not None:
                raw_b = rec_audio.getvalue()
                if raw_b and st.button("💾 Save Recorded Voice Sample", key=f"save_rec_{al_lang}", use_container_width=True):
                    save_custom_voice_sample(al_lang, raw_b, "wav")
                    st.success(f"Aapki recorded aawaz ({al_lang}) save ho gayi!")
                    st.rerun()
            if up_audio is not None:
                raw_u = up_audio.getvalue()
                ext_u = up_audio.name.rsplit(".", 1)[-1] if "." in up_audio.name else "wav"
                if raw_u and st.button("💾 Save Uploaded Voice Sample", key=f"save_up_{al_lang}", use_container_width=True):
                    save_custom_voice_sample(al_lang, raw_u, ext_u)
                    st.success(f"Aapki uploaded aawaz ({al_lang}) save ho gayi!")
                    st.rerun()

            if custom_voice:
                c_bytes, c_mime = custom_voice
                st.markdown("**Saved Custom Voice Reference:**")
                st.audio(c_bytes, format=c_mime)
                if st.button("🗑️ Remove Saved Custom Voice", key=f"del_voice_{al_lang}"):
                    for f_del in VOICE_SAMPLES_DIR.glob("*"):
                        f_del.unlink(missing_ok=True)
                    st.rerun()

        st.markdown(f"**🔊 Automated IVR Voice Call Preview ({al_lang} — Full Message Audio)**")
        if custom_voice:
            c_bytes, c_mime = custom_voice
            st.caption("Aapki saved custom voice reference play ho rahi hai (saath neeche full message TTS bhi available hai):")
            st.audio(c_bytes, format=c_mime)
        if mp3_bytes:
            st.audio(mp3_bytes, format="audio/mp3")
        else:
            st.caption("Using browser speech synthesizer.")

        safe_speech_text = json.dumps(spoken_preview_text).replace("</", "<\\/")
        speech_lang_code = "en-US" if al_lang == "English" else ("ps-AF" if al_lang == "Pashto" else "ur-PK")
        components.html(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:4px 0 10px 0;">
          <button onclick="playAlertVoice()" style="background:#0ea5e9;color:#fff;border:none;padding:8px 15px;border-radius:8px;font-weight:700;cursor:pointer;font-family:Inter,sans-serif;font-size:12px;">
            ▶️ Speak Full {al_lang} Text (Browser Voice)
          </button>
          <button onclick="stopAlertVoice()" style="background:#1e293b;color:#cbd5e1;border:1px solid #334155;padding:8px 13px;border-radius:8px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif;font-size:12px;">
            ⏹ Stop
          </button>
          <span id="vstat" style="font-size:12px;color:#94a3b8;font-family:Inter,sans-serif;">Ready</span>
        </div>
        <script>
          let stopRequested = false;
          function stopAlertVoice() {{
            stopRequested = true;
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            document.getElementById('vstat').innerText = 'Stopped.';
          }}
          function pickBestVoice(voices, preferredLang) {{
            if (!voices || !voices.length) return null;
            const isFemale = v => /uzma|latifa|sonia|aria|jenny|zira|sara|neerja|swara|female|woman|girl|google/i.test(v.name) && !/asad|salman|male|david|mark|ravi/i.test(v.name);
            const isNatural = v => /natural|neural|online|google|microsoft/i.test(v.name);
            if (preferredLang.startsWith('en')) {{
              const enVoices = voices.filter(v => v.lang.toLowerCase().startsWith('en'));
              return (
                enVoices.find(v => isFemale(v) && isNatural(v)) ||
                enVoices.find(isFemale) ||
                enVoices.find(isNatural) ||
                enVoices[0] ||
                voices[0]
              );
            }}
            const langMatches = voices.filter(v =>
              v.lang.toLowerCase() === preferredLang.toLowerCase() ||
              v.lang.toLowerCase().startsWith('ur') ||
              v.lang.toLowerCase().startsWith('ps') ||
              v.lang.toLowerCase().startsWith('hi')
            );
            return (
              langMatches.find(v => isFemale(v) && isNatural(v)) ||
              langMatches.find(isFemale) ||
              langMatches.find(isNatural) ||
              langMatches[0] ||
              voices[0]
            );
          }}
          function splitIntoSentences(txt) {{
            return txt.split(/(?<=[۔\\.!؟\\?])\\s+|\\n+/).map(s => s.trim()).filter(Boolean);
          }}
          function playAlertVoice() {{
            if (!('speechSynthesis' in window)) return;
            stopRequested = false;
            window.speechSynthesis.cancel();
            const chunks = splitIntoSentences({safe_speech_text});
            const chosenVoice = pickBestVoice(window.speechSynthesis.getVoices(), '{speech_lang_code}');
            let idx = 0;
            function speakNext() {{
              if (stopRequested || idx >= chunks.length) {{
                if (!stopRequested) document.getElementById('vstat').innerText = 'Completed full {al_lang} broadcast.';
                return;
              }}
              const utter = new SpeechSynthesisUtterance(chunks[idx]);
              if (chosenVoice) {{ utter.voice = chosenVoice; utter.lang = chosenVoice.lang; }}
              else {{ utter.lang = '{speech_lang_code}'; }}
              utter.rate = 0.92;
              utter.pitch = 1.08;
              utter.onstart = () => document.getElementById('vstat').innerText = `Speaking part ${{idx + 1}}/${{chunks.length}} ({al_lang})...`;
              utter.onend = () => {{ idx += 1; speakNext(); }};
              utter.onerror = () => {{ idx += 1; speakNext(); }};
              window.speechSynthesis.speak(utter);
            }}
            speakNext();
          }}
        </script>
        """, height=46)

        if st.button("Dispatch Official Alert Now", use_container_width=True):
            if not edited_msg.strip():
                st.error("Alert message cannot be empty.")
            elif target_mode == "Individual Registered Driver" and sel_driver_id is None:
                st.error("Please select a valid individual driver.")
            else:
                ch_str = ", ".join(al_channel) if al_channel else "SMS Gateway"
                sev = "Emergency" if "Closed" in road_st else ("Warning" if "Restricted" in road_st else "Advisory")
                run(
                    "INSERT INTO alerts(driver_id,route,language,severity,message,channel,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (sel_driver_id, al_route, al_lang, sev, edited_msg.strip(), ch_str, "Dispatched & Logged", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                st.success(f"Alert dispatched in {al_lang} via {ch_str}!")

elif nav_choice == "Road Clearance & Logs":
    st.subheader("Road Clearance Control & Provincial Dispatch Logs")
    all_roads = rows("SELECT * FROM road_status ORDER BY route, id")
    seg_map = {f"{r['route']}  |  {r['area']}  ({r['status']})": r for r in all_roads}

    c1, c2 = st.columns([1.1, 1.5], gap="large")
    with c1:
        if seg_map:
            seg = seg_map[st.selectbox("Select Highway Segment", list(seg_map.keys()))]
            with st.form("clearance_form"):
                new_st = st.selectbox("Official Road Status", ROAD_STATUSES, index=ROAD_STATUSES.index(seg["status"]) if seg["status"] in ROAD_STATUSES else 0)
                new_risk = st.slider("Operator Risk Override (1=Low, 10=Severe)", 1, 10, int(seg.get("risk_score") or 3))
                new_officer = st.text_input("Verifying Authority", value=seg.get("verified_by") or current_user["full_name"])
                new_note = st.text_area("Official Directive / Reason", value=seg.get("authority_note") or "", height=85)
                if st.form_submit_button("Verify & Publish Status", use_container_width=True):
                    if new_officer.strip() and new_note.strip():
                        run(
                            "UPDATE road_status SET status=?, risk_score=?, verified_by=?, authority_note=?, updated_at=? WHERE id=?",
                            (new_st, new_risk, new_officer.strip(), new_note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M"), seg["id"])
                        )
                        st.success("Road clearance updated across live map and risk calculator.")
                        st.rerun()
                    else:
                        st.error("Authority and directive are required.")

    with c2:
        st.markdown("**Provincial Highway Clearance Matrix**")
        if all_roads:
            df_roads = pd.DataFrame(all_roads)[["route", "area", "status", "risk_score", "verified_by", "updated_at"]]
            df_roads.columns = ["Corridor", "Sector", "Clearance Status", "Risk (1-10)", "Verified By", "Updated"]
            st.dataframe(df_roads, use_container_width=True, hide_index=True, height=280)

    st.markdown("### Provincial Alert Dispatch History")
    logs = rows("""
        SELECT alerts.id, alerts.created_at, alerts.route, alerts.language, alerts.severity,
               COALESCE(drivers.name, 'Corridor Broadcast') AS recipient,
               alerts.channel, alerts.status, alerts.message
        FROM alerts
        LEFT JOIN drivers ON drivers.id = alerts.driver_id
        ORDER BY alerts.id DESC
    """)
    if logs:
        df_logs = pd.DataFrame(logs)
        df_logs.columns = ["ID", "Timestamp", "Corridor", "Language", "Severity", "Recipient", "Channels", "Status", "Message"]
        st.dataframe(df_logs, use_container_width=True, hide_index=True)

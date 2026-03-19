"""
============================================================
WANDR — Smart Travel Planner
app.py  — Flask backend with SQLite + Claude AI
============================================================
"""

from flask import Flask, render_template, request, jsonify, session
import sqlite3, json, os, anthropic
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wandr-secret-dev-key-2025")

# ── DATABASE ────────────────────────────────────────────────
DB_PATH = "wandr.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables and seed destination + hotel data."""
    conn = get_db()
    c = conn.cursor()

    # --- destinations ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS destinations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            country     TEXT,
            region      TEXT,
            emoji       TEXT,
            description TEXT,
            budget_min  INTEGER,
            budget_max  INTEGER,
            tags        TEXT,       -- JSON array string
            best_months TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # --- hotels ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_id  INTEGER REFERENCES destinations(id),
            name            TEXT,
            stars           INTEGER,
            tier            TEXT,
            price_per_night INTEGER,
            amenities       TEXT,   -- JSON array string
            rating          REAL
        )
    """)

    # --- attractions ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS attractions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_id  INTEGER REFERENCES destinations(id),
            name            TEXT,
            category        TEXT,
            description     TEXT,
            entry_fee_inr   INTEGER DEFAULT 0,
            avg_duration    INTEGER,
            tags            TEXT    -- JSON array string
        )
    """)

    # --- itineraries (saved AI plans) ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS itineraries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT,
            destination  TEXT,
            country      TEXT,
            duration     INTEGER,
            travellers   TEXT,
            style        TEXT,
            interests    TEXT,   -- JSON array string
            budget       INTEGER,
            hotel_pref   TEXT,
            special_req  TEXT,
            plan_json    TEXT,   -- Full AI plan JSON
            total_cost   INTEGER,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── SEED DESTINATIONS ───────────────────────────────────
    c.execute("SELECT COUNT(*) FROM destinations")
    if c.fetchone()[0] == 0:
        destinations = [
            ("Paris",      "France",      "Europe",      "🗼", "The City of Light — romance, fashion, and iconic landmarks.",       50000, 200000, '["Romance","Culture","Art","Food"]',      "April–October"),
            ("Tokyo",      "Japan",       "Asia",        "⛩️", "Ultramodern meets ancient tradition in Japan's electric capital.",  60000, 220000, '["Culture","Food","Technology","History"]',"March–May, Oct–Nov"),
            ("New York",   "USA",         "Americas",    "🗽", "The city that never sleeps — skyscrapers, Broadway, and parks.",    70000, 280000, '["Urban","Art","Shopping","Nightlife"]',   "April–June, Sept–Nov"),
            ("Bali",       "Indonesia",   "Asia",        "🌴", "Lush rice terraces, sacred temples, and pristine beaches.",         25000, 120000, '["Nature","Beach","Wellness","Culture"]',  "May–September"),
            ("Rome",       "Italy",       "Europe",      "🏛️", "Walk through millennia of history in the Eternal City.",           45000, 180000, '["History","Food","Culture","Art"]',       "April–June, Sept–Oct"),
            ("Dubai",      "UAE",         "Middle East", "🌇", "Futuristic skyline, world-class malls, and desert adventures.",     70000, 300000, '["Luxury","Shopping","Urban","Adventure"]',"November–March"),
            ("London",     "UK",          "Europe",      "🎡", "Royal palaces, world-class museums, and vibrant neighbourhoods.",   60000, 240000, '["Culture","History","Art","Shopping"]',   "May–September"),
            ("Singapore",  "Singapore",   "Asia",        "🦁", "Garden city at the crossroads of culture, cuisine, and commerce.", 55000, 200000, '["Urban","Food","Shopping","Culture"]',    "February–April"),
            ("Barcelona",  "Spain",       "Europe",      "🎭", "Gaudí's architecture, tapas culture, and sun-drenched beaches.",   45000, 180000, '["Art","Beach","Food","Nightlife"]',       "May–June, Sept–Oct"),
            ("Maldives",   "Maldives",    "Asia",        "🏝️", "Overwater bungalows, crystal lagoons, and vibrant coral reefs.",   90000, 400000, '["Beach","Luxury","Wellness","Romance"]',  "November–April"),
            ("Kyoto",      "Japan",       "Asia",        "🌸", "Traditional tea houses, bamboo forests, and thousands of shrines.",50000, 160000, '["Culture","History","Nature","Art"]',     "March–May, Oct–Nov"),
            ("Amsterdam",  "Netherlands", "Europe",      "🚲", "Picturesque canals, world-class museums, and vibrant culture.",    50000, 180000, '["Culture","Art","History","Nightlife"]',  "April–August"),
            ("Istanbul",   "Turkey",      "Europe",      "🕌", "Where East meets West — bazaars, mosques, and Bosphorus views.",   30000, 120000, '["Culture","Food","History","Shopping"]',  "March–May, Sept–Nov"),
            ("Sydney",     "Australia",   "Oceania",     "🦘", "Iconic Opera House, Harbour Bridge, and golden beaches.",          75000, 260000, '["Beach","Urban","Nature","Culture"]',     "September–November"),
            ("Bangkok",    "Thailand",    "Asia",        "🛺", "Ornate temples, bustling street markets, and incredible food.",    20000, 100000, '["Food","Culture","Shopping","Nightlife"]',"November–February"),
            ("Prague",     "Czech Republic","Europe",    "🏰", "Fairytale architecture and bohemian spirit in central Europe.",    30000, 120000, '["History","Culture","Art","Nightlife"]',  "May–September"),
            ("Santorini",  "Greece",      "Europe",      "🌊", "Iconic blue domes, volcanic beaches, and Aegean sunsets.",         65000, 220000, '["Beach","Romance","Food","Photography"]', "June–September"),
            ("Cape Town",  "South Africa","Africa",      "🏔️", "Table Mountain, Cape Winelands, and diverse cultural mosaic.",     45000, 160000, '["Nature","Culture","Adventure","Food"]',  "November–February"),
        ]
        c.executemany(
            "INSERT INTO destinations (name,country,region,emoji,description,budget_min,budget_max,tags,best_months) VALUES (?,?,?,?,?,?,?,?,?)",
            destinations
        )

    # ── SEED HOTELS ─────────────────────────────────────────
    c.execute("SELECT COUNT(*) FROM hotels")
    if c.fetchone()[0] == 0:
        # destination_id, name, stars, tier, price_per_night, amenities, rating
        hotels = [
            # Paris (1)
            (1,"Hôtel de Crillon",         5,"luxury",  15000,'["Spa","Pool","Concierge","Bar"]',   4.9),
            (1,"Hôtel du Louvre",          4,"mid",      6500,'["WiFi","Bar","Restaurant"]',         4.5),
            (1,"Generator Paris Hostel",   2,"budget",   1800,'["WiFi","Lounge","Tours"]',            4.0),
            # Tokyo (2)
            (2,"Park Hyatt Tokyo",         5,"luxury",  18000,'["Spa","Pool","Bar","Restaurant"]',   4.9),
            (2,"Shinjuku Granbell Hotel",  4,"mid",      5500,'["WiFi","Bar","Gym"]',                 4.4),
            (2,"Khaosan Tokyo Origami",    2,"budget",   1500,'["WiFi","Lounge","Lockers"]',          4.1),
            # New York (3)
            (3,"The Plaza Hotel",          5,"luxury",  22000,'["Spa","Concierge","Bar","Restaurant"]',4.8),
            (3,"citizenM New York Bowery", 4,"mid",      8000,'["WiFi","Bar","Gym"]',                 4.5),
            (3,"HI NYC Hostel",            2,"budget",   2200,'["WiFi","Lounge","Tours"]',            3.9),
            # Bali (4)
            (4,"COMO Shambhala Estate",    5,"luxury",  20000,'["Spa","Pool","Yoga","Restaurant"]',  4.9),
            (4,"Komaneka at Bisma",        4,"mid",      6000,'["Pool","WiFi","Restaurant"]',         4.6),
            (4,"Puri Garden Hotel",        2,"budget",   1200,'["Pool","WiFi","Breakfast"]',          4.0),
        ]
        c.executemany(
            "INSERT INTO hotels (destination_id,name,stars,tier,price_per_night,amenities,rating) VALUES (?,?,?,?,?,?,?)",
            hotels
        )

    conn.commit()
    conn.close()
    print("✅ Database initialised successfully.")


# ── ROUTES ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/planner")
def planner():
    return render_template("planner.html")

@app.route("/result")
def result():
    return render_template("result.html")

@app.route("/destinations")
def destinations_page():
    return render_template("destinations.html")

@app.route("/about")
def about():
    return render_template("about.html")


# ── API: DESTINATIONS ────────────────────────────────────────

@app.route("/api/destinations")
def api_destinations():
    region = request.args.get("region", "")
    conn = get_db()
    if region and region != "All":
        rows = conn.execute(
            "SELECT * FROM destinations WHERE region=? ORDER BY name", (region,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM destinations ORDER BY name").fetchall()
    conn.close()
    dests = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"] or "[]")
        dests.append(d)
    return jsonify(dests)


@app.route("/api/destinations/<int:dest_id>/hotels")
def api_hotels(dest_id):
    tier = request.args.get("tier", "")
    conn = get_db()
    if tier:
        rows = conn.execute(
            "SELECT * FROM hotels WHERE destination_id=? AND tier=? ORDER BY stars DESC",
            (dest_id, tier)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM hotels WHERE destination_id=? ORDER BY stars DESC",
            (dest_id,)
        ).fetchall()
    conn.close()
    hotels = []
    for r in rows:
        h = dict(r)
        h["amenities"] = json.loads(h["amenities"] or "[]")
        hotels.append(h)
    return jsonify(hotels)


# ── API: GENERATE ITINERARY ─────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    dest      = data.get("dest", "")
    country   = data.get("destCountry", "")
    duration  = int(data.get("duration", 5))
    travellers= data.get("travellers", "2 people")
    style     = data.get("style", "Comfort Traveller")
    interests = data.get("interests", [])
    budget    = int(data.get("budget", 80000))
    hotel_pref= data.get("hotelPref", "Mid-range Hotel")
    special   = data.get("specialReq", "")

    if not dest:
        return jsonify({"error": "Destination is required"}), 400

    # Fetch matching hotels from DB for context
    conn = get_db()
    dest_row = conn.execute(
        "SELECT id FROM destinations WHERE name LIKE ?", (f"%{dest}%",)
    ).fetchone()

    hotel_context = ""
    if dest_row:
        tier_map = {
            "Hostel / Guesthouse": "budget",
            "Budget Hotel": "budget",
            "Mid-range Hotel": "mid",
            "4-Star Hotel": "mid",
            "5-Star / Luxury": "luxury",
            "Boutique / Heritage": "mid",
        }
        tier = tier_map.get(hotel_pref, "mid")
        hotels_db = conn.execute(
            "SELECT name, stars, price_per_night FROM hotels WHERE destination_id=? ORDER BY stars DESC LIMIT 3",
            (dest_row["id"],)
        ).fetchall()
        if hotels_db:
            hotel_context = "Database hotels for reference: " + ", ".join(
                f"{h['name']} ({h['stars']}★ ₹{h['price_per_night']}/night)" for h in hotels_db
            )
    conn.close()

    # Build Claude prompt
    prompt = f"""You are a professional travel planner. Generate a detailed personalised travel itinerary as a JSON object.

Trip details:
- Destination: {dest}{', ' + country if country else ''}
- Duration: {duration} days/nights
- Travellers: {travellers}
- Travel style: {style}
- Interests: {', '.join(interests) if interests else 'general sightseeing'}
- Total budget: Rs.{budget:,}
- Accommodation: {hotel_pref}
- Special requirements: {special or 'None'}
{hotel_context}

Return ONLY valid JSON (no markdown, no preamble):
{{
  "summary": "2-sentence engaging trip overview",
  "days": [
    {{
      "day": 1,
      "theme": "Arrival & First Impressions",
      "activities": [
        {{
          "time": "09:00",
          "icon": "☕",
          "name": "Activity name",
          "description": "1-2 sentence description",
          "cost": 500
        }}
      ],
      "dayCost": 10000
    }}
  ],
  "budget": {{
    "accommodation": 28000,
    "food": 16000,
    "transport": 10000,
    "activities": 14000,
    "shopping": 8000,
    "miscellaneous": 4000
  }},
  "hotels": [
    {{ "name": "Hotel name", "stars": 3, "pricePerNight": 3500 }}
  ],
  "tips": ["tip1", "tip2", "tip3"]
}}

Rules:
- Use REAL landmark and restaurant names for {dest}
- All costs as integers in Indian Rupees
- Generate exactly {duration} days with 5-7 activities each
- Budget total ≈ Rs.{budget:,}
- Tailor to interests: {', '.join(interests) if interests else 'general'}
- Match hotel tier to: {hotel_pref}"""

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text

        # Extract JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError("No JSON in response")
        plan = json.loads(json_match.group())

        # Persist to DB
        total_cost = sum(plan.get("budget", {}).values())
        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO itineraries
            (session_id, destination, country, duration, travellers, style,
             interests, budget, hotel_pref, special_req, plan_json, total_cost)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session.get("sid", "anonymous"),
            dest, country, duration, travellers, style,
            json.dumps(interests), budget, hotel_pref, special,
            json.dumps(plan), total_cost
        ))
        itinerary_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"success": True, "plan": plan, "itinerary_id": itinerary_id})

    except anthropic.APIError as e:
        return jsonify({"success": False, "error": f"Claude API error: {str(e)}", "fallback": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "fallback": True}), 200


# ── API: PAST ITINERARIES ────────────────────────────────────

@app.route("/api/itineraries")
def api_itineraries():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, destination, country, duration, travellers, style, budget, total_cost, created_at FROM itineraries ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/itineraries/<int:itin_id>")
def api_itinerary(itin_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM itineraries WHERE id=?", (itin_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    r = dict(row)
    r["plan_json"] = json.loads(r["plan_json"])
    r["interests"] = json.loads(r.get("interests", "[]"))
    return jsonify(r)


# ── API: BUDGET CALCULATOR ───────────────────────────────────

@app.route("/api/budget-split", methods=["POST"])
def api_budget_split():
    """Server-side budget category calculation."""
    data   = request.get_json()
    budget = int(data.get("budget", 80000))
    style  = data.get("style", "Comfort Traveller")
    days   = int(data.get("duration", 5))

    # Allocation weights by style
    weights = {
        "Budget Explorer":      {"accommodation":0.30,"food":0.25,"transport":0.15,"activities":0.15,"shopping":0.10,"miscellaneous":0.05},
        "Backpacker":           {"accommodation":0.25,"food":0.28,"transport":0.18,"activities":0.18,"shopping":0.06,"miscellaneous":0.05},
        "Comfort Traveller":    {"accommodation":0.34,"food":0.22,"transport":0.13,"activities":0.15,"shopping":0.10,"miscellaneous":0.06},
        "Luxury Seeker":        {"accommodation":0.45,"food":0.20,"transport":0.10,"activities":0.12,"shopping":0.10,"miscellaneous":0.03},
        "Business Blend":       {"accommodation":0.40,"food":0.22,"transport":0.18,"activities":0.08,"shopping":0.08,"miscellaneous":0.04},
        "Family Adventure":     {"accommodation":0.35,"food":0.24,"transport":0.14,"activities":0.16,"shopping":0.07,"miscellaneous":0.04},
        "Honeymoon / Romance":  {"accommodation":0.42,"food":0.22,"transport":0.10,"activities":0.14,"shopping":0.08,"miscellaneous":0.04},
    }
    w = weights.get(style, weights["Comfort Traveller"])

    split = {cat: round(budget * pct) for cat, pct in w.items()}
    split["per_day"] = round(budget / days)
    split["total"]   = budget

    return jsonify(split)


# ── API: STATS ───────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    conn = get_db()
    total_plans = conn.execute("SELECT COUNT(*) FROM itineraries").fetchone()[0]
    total_dests = conn.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
    top_dests   = conn.execute(
        "SELECT destination, COUNT(*) as cnt FROM itineraries GROUP BY destination ORDER BY cnt DESC LIMIT 5"
    ).fetchall()
    avg_budget  = conn.execute("SELECT AVG(budget) FROM itineraries").fetchone()[0]
    conn.close()
    return jsonify({
        "total_plans": total_plans,
        "total_destinations": total_dests,
        "top_destinations": [dict(r) for r in top_dests],
        "avg_budget": round(avg_budget or 0)
    })


# ── ENTRY POINT ──────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("🌍 Wandr Smart Travel Planner running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

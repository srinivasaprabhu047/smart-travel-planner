# Wandr — Smart Travel Planner (Python Edition)

A full-stack travel planning application built with **Flask + SQLite + Claude AI**.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."        # Mac/Linux
set ANTHROPIC_API_KEY=sk-ant-...             # Windows

# 3. Run the app
python app.py

# 4. Open browser
http://127.0.0.1:5000
```

The SQLite database (`wandr.db`) is created automatically with all seed data on first run.

---

## 📁 Project Structure

```
wandr_python/
│
├── app.py                     ← Flask app: routes, DB init, REST API
├── requirements.txt           ← flask, anthropic
├── wandr.db                   ← SQLite database (auto-created)
│
├── templates/                 ← Jinja2 HTML templates
│   ├── base.html              ← Shared layout (nav, footer, loading)
│   ├── index.html             ← Home page
│   ├── planner.html           ← 3-step trip planning form
│   ├── result.html            ← Itinerary result display
│   ├── destinations.html      ← Destination catalogue
│   └── about.html             ← Project docs + DB schema
│
└── static/
    ├── css/
    │   ├── main.css           ← Global styles
    │   ├── planner.css        ← Form & sidebar styles
    │   └── result.css         ← Itinerary & budget styles
    └── js/
        ├── planner.js         ← Form logic → POST /api/generate
        ├── result.js          ← Render itinerary from session
        └── destinations.js    ← Fetch from /api/destinations
```

---

## 🌐 REST API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Home page |
| GET | `/planner` | 3-step form |
| GET | `/result` | Itinerary display |
| GET | `/destinations` | Destination catalogue |
| GET | `/about` | Project documentation |
| GET | `/api/destinations` | All destinations (filter: `?region=Asia`) |
| GET | `/api/destinations/<id>/hotels` | Hotels for destination |
| **POST** | `/api/generate` | **Generate AI itinerary + save to DB** |
| **POST** | `/api/budget-split` | **Server-side budget calculation** |
| GET | `/api/itineraries` | Last 20 saved itineraries |
| GET | `/api/itineraries/<id>` | Single itinerary by ID |
| GET | `/api/stats` | Total plans, top destinations |

---

## 🗄️ SQLite Database Tables

| Table | Purpose |
|-------|---------|
| `destinations` | 18+ travel destinations with tags, budget ranges |
| `hotels` | Hotels per destination with tier, price, amenities |
| `attractions` | Tourist attractions per destination |
| `itineraries` | Every AI-generated plan, saved with full JSON |

---

## 🐍 Python Architecture

```
User Form (JS)
    ↓  POST /api/generate
Flask route (app.py)
    ↓  SELECT from SQLite (hotel context)
    ↓  Build structured prompt
    ↓  anthropic.Anthropic().messages.create()
    ↓  Parse JSON from Claude response
    ↓  INSERT INTO itineraries (SQLite)
    ↓  Return JSON to browser
JS result.js
    ↓  Render day blocks, budget chart, hotels
```

---

## ⚙️ Requirements

- Python 3.11+
- `flask>=3.0.0`
- `anthropic>=0.25.0`
- A valid `ANTHROPIC_API_KEY`

---

*Wandr — Flask + SQLite + Claude AI by Anthropic*

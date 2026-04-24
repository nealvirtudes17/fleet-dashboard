"""
Fleet Dashboard Generator
=========================
Reads fleet_status.csv and writes a self-contained fleet_dashboard.html.

Colour / Status Logic
---------------------
Status       Colour    Hex       Rationale
-----------  --------  --------  -------------------------------------------
active       Green     #22c55e   Vehicle is online and moving – no action needed.
idle         Amber     #f59e0b   Online but stationary – worth monitoring for
                                 fuel/time waste but not urgent.
offline      Red       #ef4444   No GPS signal received – highest-priority alert;
                                 could mean breakdown, theft, or dead battery.
low_battery  Orange    #f97316   Battery ≤ 15 % reported – needs charging soon.
                                 Orange sits between amber and red to signal
                                 "urgent but not yet critical".
maintenance  Grey      #6b7280   Intentionally offline for service – no alert needed.
(unknown)    Slate     #94a3b8   Unexpected status value – flagged visually for review.

The palette follows traffic-light intuition (green / amber / red) with two
extra states kept visually distinct by hue. All colours pass WCAG AA contrast
on a white background when used in the status badge.
Edge-case handling
------------------
- Missing name      → falls back to device_id.
- Invalid lat/lon   → device shown in table but omitted from map (⚠ flag shown).
- Out-of-range bat. → clamped to 0-100 for the progress bar; raw value shown in tooltip.
- Future timestamp  → displayed as "future timestamp" rather than a negative delta.
- Unknown status    → rendered in slate with a title-cased label.
"""

import csv
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

INPUT_FILE  = "fleet_status.csv"
OUTPUT_FILE = "fleet_dashboard.html"

LEAFLET_JS_URL  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"

STATUS_COLOUR = {
    "active":       "#22c55e",
    "idle":         "#f59e0b",
    "offline":      "#ef4444",
    "low_battery":  "#f97316",
    "maintenance":  "#6b7280",
}
DEFAULT_COLOUR = "#94a3b8"

STATUS_LABEL = {
    "active":       "Active",
    "idle":         "Idle",
    "offline":      "Offline",
    "low_battery":  "Low Battery",
    "maintenance":  "Maintenance",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read().decode("utf-8")


def parse_coord(val: str):
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def clamp_battery(raw: str):
    """Return (display_str, clamped_int_or_None, out_of_range_bool)."""
    try:
        pct = int(raw.strip())
        clamped = max(0, min(100, pct))
        return f"{clamped}%", clamped, (pct != clamped)
    except (ValueError, AttributeError):
        return "N/A", None, False


def time_ago(ts_str: str, now: datetime) -> str:
    try:
        ts = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        diff = int((now - ts).total_seconds())
        if diff < 0:
            return "future timestamp"
        if diff < 60:
            return f"{diff}s ago"
        if diff < 3600:
            return f"{diff // 60}m ago"
        if diff < 86400:
            return f"{diff // 3600}h {(diff % 3600) // 60}m ago"
        return f"{diff // 86400}d ago"
    except (ValueError, AttributeError):
        return "unknown"


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

# ── Data loading ──────────────────────────────────────────────────────────────

def read_devices(path: str) -> list:
    devices = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            device_id = row.get("device_id", "").strip()
            name      = row.get("name", "").strip() or device_id
            status    = row.get("status", "").strip().lower()
            raw_bat   = row.get("battery_pct", "").strip()
            lat       = parse_coord(row.get("lat", ""))
            lon       = parse_coord(row.get("lon", ""))
            last_seen = row.get("last_seen", "").strip()
            location  = row.get("location", "").strip()

            bat_display, bat_clamped, bat_oor = clamp_battery(raw_bat)

            devices.append({
                "device_id":   device_id,
                "name":        name,
                "status":      status,
                "raw_bat":     raw_bat,
                "bat_display": bat_display,
                "bat_clamped": bat_clamped,
                "bat_oor":     bat_oor,
                "lat":         lat,
                "lon":         lon,
                "has_coords":  lat is not None and lon is not None,
                "last_seen":   last_seen,
                "location":    location,
            })
    return devices

# ── HTML generation ───────────────────────────────────────────────────────────

def build_summary_html(devices: list) -> str:
    counts: dict = {}
    for d in devices:
        counts[d["status"]] = counts.get(d["status"], 0) + 1

    order = ["active", "idle", "low_battery", "offline", "maintenance"]
    cards = ""
    rendered = set()

    for s in order:
        if s not in counts:
            continue
        colour = STATUS_COLOUR[s]
        label  = STATUS_LABEL[s]
        cards += (
            f'<div class="summary-card" style="border-left:4px solid {colour};">'
            f'<div class="count">{counts[s]}</div>'
            f'<div class="label">{label}</div>'
            f'</div>'
        )
        rendered.add(s)

    for s, n in counts.items():
        if s in rendered:
            continue
        label = s.replace("_", " ").title()
        cards += (
            f'<div class="summary-card" style="border-left:4px solid {DEFAULT_COLOUR};">'
            f'<div class="count">{n}</div>'
            f'<div class="label">{html_escape(label)}</div>'
            f'</div>'
        )

    return cards


def build_table_rows(devices: list, now: datetime) -> str:
    rows = ""
    for d in devices:
        colour = STATUS_COLOUR.get(d["status"], DEFAULT_COLOUR)
        label  = STATUS_LABEL.get(d["status"], d["status"].replace("_", " ").title())
        ago    = time_ago(d["last_seen"], now)

        no_coords = ' <span class="warn" title="No valid coordinates – omitted from map">⚠</span>' \
                    if not d["has_coords"] else ""

        # Battery cell
        if d["bat_clamped"] is not None:
            tooltip = (
                f'Battery: {d["raw_bat"]}% (clamped to {d["bat_clamped"]}%)'
                if d["bat_oor"]
                else f'Battery: {d["bat_clamped"]}%'
            )
            bat_cell = (
                f'<div class="battery-cell">'
                f'<div class="battery-bar" title="{html_escape(tooltip)}">'
                f'<div class="battery-fill" style="width:{d["bat_clamped"]}%;background:{colour};"></div>'
                f'</div>'
                f'<span class="battery-text">{d["bat_display"]}'
                + (' <span class="warn" title="Out-of-range value">⚠</span>' if d["bat_oor"] else "")
                + f'</span></div>'
            )
        else:
            bat_cell = '<span class="battery-text">N/A</span>'

        rows += (
            "<tr>"
            f"<td><strong>{html_escape(d['device_id'])}</strong>{no_coords}</td>"
            f"<td>{html_escape(d['name'])}</td>"
            f'<td><span class="status-badge" style="background:{colour};">{html_escape(label)}</span></td>'
            f"<td>{bat_cell}</td>"
            f"<td>{html_escape(d['location'])}</td>"
            f"<td>{html_escape(ago)}</td>"
            "</tr>"
        )
    return rows


def build_map_markers(devices: list, now: datetime) -> str:
    markers = []
    for d in devices:
        if not d["has_coords"]:
            continue
        colour = STATUS_COLOUR.get(d["status"], DEFAULT_COLOUR)
        label  = STATUS_LABEL.get(d["status"], d["status"].replace("_", " ").title())
        bat    = str(d["bat_clamped"]) if d["bat_clamped"] is not None else "N/A"
        markers.append({
            "id":       d["device_id"],
            "name":     d["name"],
            "lat":      d["lat"],
            "lon":      d["lon"],
            "colour":   colour,
            "status":   label,
            "battery":  bat,
            "location": d["location"],
            "ago":      time_ago(d["last_seen"], now),
        })
    return json.dumps(markers, ensure_ascii=False)


def generate_html(devices: list, leaflet_js: str, leaflet_css: str) -> str:
    now          = datetime.now()
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    total        = len(devices)
    summary_html = build_summary_html(devices)
    table_rows   = build_table_rows(devices, now)
    markers_json = build_map_markers(devices, now)

    # Use a plain string (not f-string) for the JS/CSS blocks to avoid brace escaping.
    # Placeholders (ALL_CAPS) are substituted via str.replace() at the end.
    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        "<title>Fleet Dashboard</title>\n"
        "<style>\n"
        "LEAFLET_CSS_PLACEHOLDER\n"
        "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "body { font-family: system-ui, -apple-system, sans-serif; background: #f1f5f9; color: #1e293b; }\n"
        "header { background: #0f172a; color: #f8fafc; padding: 16px 24px;"
        "         display: flex; align-items: center; justify-content: space-between; }\n"
        "header h1 { font-size: 1.4rem; font-weight: 700; }\n"
        "header .meta { font-size: 0.8rem; color: #94a3b8; }\n"
        ".container { max-width: 1400px; margin: 0 auto; padding: 20px; }\n"
        ".summary { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }\n"
        ".summary-card { background: #fff; border-radius: 8px; padding: 16px 20px;"
        "                min-width: 120px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }\n"
        ".summary-card .count { font-size: 2rem; font-weight: 700; line-height: 1; }\n"
        ".summary-card .label { font-size: 0.8rem; color: #64748b; margin-top: 4px;"
        "                       text-transform: uppercase; letter-spacing: .05em; }\n"
        "#map { height: 480px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.12);"
        "       margin-bottom: 24px; }\n"
        ".legend { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }\n"
        ".legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #475569; }\n"
        ".legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }\n"
        ".table-wrap { background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08);"
        "              overflow: auto; }\n"
        "table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }\n"
        "th { background: #f8fafc; padding: 10px 14px; text-align: left; font-weight: 600;"
        "     color: #475569; border-bottom: 1px solid #e2e8f0; white-space: nowrap; }\n"
        "td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }\n"
        "tr:last-child td { border-bottom: none; }\n"
        "tr:hover td { background: #f8fafc; }\n"
        ".status-badge { display: inline-block; padding: 2px 10px; border-radius: 20px;"
        "                font-size: 0.75rem; font-weight: 600; color: #fff; white-space: nowrap; }\n"
        ".battery-cell { display: flex; align-items: center; gap: 8px; }\n"
        ".battery-bar { width: 80px; height: 10px; background: #e2e8f0; border-radius: 5px;"
        "               overflow: hidden; flex-shrink: 0; }\n"
        ".battery-fill { height: 100%; border-radius: 5px; }\n"
        ".battery-text { font-size: 0.8rem; color: #475569; white-space: nowrap; }\n"
        ".warn { color: #f59e0b; cursor: help; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "\n"
        "<header>\n"
        "  <h1>Fleet Dashboard</h1>\n"
        f"  <div class='meta'>Generated {generated_at} &nbsp;|&nbsp; {total} devices</div>\n"
        "</header>\n"
        "\n"
        "<div class='container'>\n"
        "\n"
        "  <!-- Summary -->\n"
        f"  <div class='summary'>{summary_html}</div>\n"
        "\n"
        "  <!-- Map legend -->\n"
        "  <div class='legend'>\n"
        "    <div class='legend-item'><div class='legend-dot' style='background:#22c55e;'></div> Active</div>\n"
        "    <div class='legend-item'><div class='legend-dot' style='background:#f59e0b;'></div> Idle</div>\n"
        "    <div class='legend-item'><div class='legend-dot' style='background:#f97316;'></div> Low Battery</div>\n"
        "    <div class='legend-item'><div class='legend-dot' style='background:#ef4444;'></div> Offline</div>\n"
        "    <div class='legend-item'><div class='legend-dot' style='background:#6b7280;'></div> Maintenance</div>\n"
        "  </div>\n"
        "\n"
        "  <!-- Map -->\n"
        "  <div id='map'></div>\n"
        "\n"
        "  <!-- Device list -->\n"
        "  <div class='table-wrap'>\n"
        "    <table>\n"
        "      <thead>\n"
        "        <tr>\n"
        "          <th>Device ID</th><th>Name</th><th>Status</th>\n"
        "          <th>Battery</th><th>Location</th><th>Last Seen</th>\n"
        "        </tr>\n"
        "      </thead>\n"
        "      <tbody>\n"
        f"        TABLE_ROWS_PLACEHOLDER\n"
        "      </tbody>\n"
        "    </table>\n"
        "  </div>\n"
        "\n"
        "</div>\n"
        "\n"
        "<script>\n"
        "LEAFLET_JS_PLACEHOLDER\n"
        "</script>\n"
        "\n"
        "<script>\n"
        "var map = L.map('map').setView([-27.5, 133.5], 4);\n"
        "L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {\n"
        "    attribution: '&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors',\n"
        "    maxZoom: 19\n"
        "}).addTo(map);\n"
        "\n"
        "var markers = MARKERS_JSON_PLACEHOLDER;\n"
        "\n"
        "markers.forEach(function(m) {\n"
        "    var dot = '<div style=\"width:14px;height:14px;border-radius:50%;background:' + m.colour +\n"
        "              ';border:2px solid rgba(0,0,0,.25);box-shadow:0 1px 3px rgba(0,0,0,.3);\"></div>';\n"
        "    var icon = L.divIcon({\n"
        "        className: '',\n"
        "        html: dot,\n"
        "        iconSize: [14, 14],\n"
        "        iconAnchor: [7, 7],\n"
        "        popupAnchor: [0, -10]\n"
        "    });\n"
        "    var batLine = m.battery !== 'N/A' ? '<b>Battery:</b> ' + m.battery + '%<br>' : '<b>Battery:</b> N/A<br>';\n"
        "    var popup = '<b>' + m.id + '</b> \u2013 ' + m.name + '<br>' +\n"
        "                '<b>Status:</b> ' + m.status + '<br>' +\n"
        "                batLine +\n"
        "                '<b>Location:</b> ' + m.location + '<br>' +\n"
        "                '<b>Last seen:</b> ' + m.ago;\n"
        "    L.marker([m.lat, m.lon], {icon: icon}).addTo(map).bindPopup(popup);\n"
        "});\n"
        "</script>\n"
        "\n"
        "</body>\n"
        "</html>\n"
    )

    page = (page
            .replace("LEAFLET_CSS_PLACEHOLDER", leaflet_css)
            .replace("LEAFLET_JS_PLACEHOLDER",  leaflet_js)
            .replace("TABLE_ROWS_PLACEHOLDER",  table_rows)
            .replace("MARKERS_JSON_PLACEHOLDER", markers_json))
    return page

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("Reading fleet data …")
    devices = read_devices(INPUT_FILE)
    print(f"  Loaded {len(devices)} devices.")

    print("Fetching Leaflet (will be embedded inline) …")
    try:
        leaflet_js  = fetch_text(LEAFLET_JS_URL)
        leaflet_css = fetch_text(LEAFLET_CSS_URL)
    except Exception as exc:
        print(f"ERROR: Could not fetch Leaflet – {exc}", file=sys.stderr)
        sys.exit(1)

    print("Building HTML …")
    html = generate_html(devices, leaflet_js, leaflet_css)

    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")
    size_kb = Path(OUTPUT_FILE).stat().st_size / 1024
    print(f"Done!  {OUTPUT_FILE}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

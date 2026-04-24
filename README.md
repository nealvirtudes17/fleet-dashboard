# Fleet Dashboard

A self-contained HTML fleet dashboard generated from a CSV snapshot of GPS tracking devices.

## How to run

**Standard Python**
```bash
python fleet_dashboard.py
```

**Using uv**
```bash
uv run fleet_dashboard.py
```

Requires Python 3.8+ and an internet connection (Leaflet.js is fetched once and embedded into the output file). Opens in any modern browser with no additional setup.

**Input:** `fleet_status.csv`  
**Output:** `fleet_dashboard.html`

---

## My Approach

### How I used AI to complete this task

I used Claude as a sounding board while building this. Before writing any code I talked through the main constraint — standard library only, but still needs a real map — and landed on fetching Leaflet.js at generation time and embedding it inline. That kept the output fully self-contained without reinventing a mapping library.

I also used it to pressure-test the CSV before building the parsing logic. It caught a few things I would have hit later anyway: the invalid latitude on TRK034, the out-of-range battery on TRK033, the future timestamp on TRK035, missing fields on TRK031. Knowing about them upfront meant I could handle them properly from the start.

For the HTML and CSS I used it to iterate quickly on layout rather than writing everything from scratch. The structure I had in my head (header, summary cards, map, table) came together faster that way, and I adjusted the output as I went.

---

### Colour / status logic I chose and why

| Status | Colour | Hex |
|---|---|---|
| Active | Green | `#22c55e` |
| Idle | Amber | `#f59e0b` |
| Low Battery | Orange | `#f97316` |
| Offline | Red | `#ef4444` |
| Maintenance | Grey | `#6b7280` |

I went with a traffic-light base — green is fine, amber needs watching, red needs action. It's intuitive enough that a fleet manager can read the map without looking at the legend.

Low battery gets orange rather than sharing amber with idle because the two need to be visually separable. A vehicle sitting idle is a minor concern; one about to die is more pressing, so it gets a colour closer to red.

Maintenance is grey because it's not an alert at all — it's a planned state. Removing it from the colour hierarchy means it doesn't draw attention away from vehicles that actually need it.

Anything with an unrecognised status falls back to slate so it's visible but clearly not in the normal range.

---

### One thing I would add if this were a real product

**Real-time auto-refresh.**

Right now the dashboard is a snapshot — it's stale the moment you open it. In a real product the page would poll a backend every 30–60 seconds and update the markers and table in place. The whole point of a live fleet tool is knowing when something goes wrong as it happens, not the next time someone reruns a script.

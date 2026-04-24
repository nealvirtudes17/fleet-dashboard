# Fleet Dashboard

A self-contained HTML fleet dashboard generated from a CSV snapshot of GPS tracking devices.

## How to run

```bash
python fleet_dashboard.py
```

Requires Python 3.8+ and an internet connection (Leaflet.js is fetched once and embedded into the output file). Opens in any modern browser with no additional setup.

**Input:** `fleet_status.csv`  
**Output:** `fleet_dashboard.html`

---

## My Approach

### How I used AI to complete this task

I used Claude (an AI assistant) as a collaborative tool throughout the build — not to write the code for me, but to accelerate the parts that would otherwise be slow and error-prone.

Concretely, I used it to:

- **Plan the architecture** before writing a line of code. I described the constraints (standard library only, self-contained HTML, map required) and talked through the tradeoff between embedding Leaflet.js via `urllib.request` versus rolling a pure SVG coordinate plot. Embedding Leaflet won because it gives a real interactive map with almost no extra code.
- **Spot edge cases in the CSV** that I might have skimmed past — the invalid latitude on TRK034, the out-of-range battery on TRK033, the future timestamp on TRK035, and the missing fields on TRK031. Having those flagged early meant the data-cleaning logic was built in from the start rather than bolted on.
- **Draft and iterate on the HTML/CSS layout.** I described the visual structure I wanted (header, summary cards, legend, map, table) and refined the output until it matched. This was faster than writing raw CSS from scratch and then tweaking by hand.

I reviewed every output, tested the script end-to-end, and made deliberate choices about what to keep or change. AI handled the mechanical parts; judgement calls (colour logic, edge-case handling, what to omit) stayed with me.

---

### Colour / status logic I chose and why

| Status | Colour | Hex |
|---|---|---|
| Active | Green | `#22c55e` |
| Idle | Amber | `#f59e0b` |
| Low Battery | Orange | `#f97316` |
| Offline | Red | `#ef4444` |
| Maintenance | Grey | `#6b7280` |

The palette is built on **traffic-light intuition** — green means fine, amber means watch it, red means act now. That mapping is already burned into most people's heads, so a fleet manager can read the map at a glance without consulting a legend.

Two extra states sit within that range rather than outside it:

- **Orange for low battery** — sits between amber and red because it is urgent but not yet a crisis. A driver can still get to a charging point; the vehicle has not gone dark. Giving it its own hue (rather than sharing amber with idle) means the two concerns are visually separable even when markers overlap.
- **Grey for maintenance** — deliberately colourless. A vehicle in planned maintenance is not an alert; it is an expected absence. Grey removes it from the urgency hierarchy without hiding it from the map entirely.

Unknown or unexpected status values fall back to slate (`#94a3b8`) — pale enough to signal "something is off with this record" without implying the severity of red.

---

### One thing I would add if this were a real product

**Real-time auto-refresh.**

The dashboard is currently a static snapshot — the moment a fleet manager opens it, the data starts going stale. In a real product, the page would poll a backend endpoint every 30–60 seconds (or hold open a WebSocket connection) and update the map markers and table rows in place, without a full reload.

This matters because the core value of a GPS fleet tool is *live awareness* — knowing a driver just went offline, or a battery just hit critical, the moment it happens rather than whenever someone remembers to regenerate the file. Every element on this dashboard (the map, the status badges, the "last seen" column) was designed with real-time in mind. Without the refresh loop, it is a report; with it, it becomes a genuine operational tool.

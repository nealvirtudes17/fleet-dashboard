Fleet Dashboard Challenge
A technical task for candidates applying to SolidGPS.

The Task
You have been given fleet_status.csv — a real-world snapshot of 30 GPS tracking devices currently in the field across Australia.

Write a Python script that reads the CSV and produces a single fleet_dashboard.html that a fleet manager could open in any browser with no setup.

Input
fleet_status.csv contains the following columns:

Column	Description
device_id	Unique tracker ID (e.g. TRK001)
name	Vehicle name
status	One of: active, idle, offline, low_battery
battery_pct	Battery percentage (0–100)
lat	Latitude
lon	Longitude
last_seen	Timestamp of last GPS ping (YYYY-MM-DD HH:MM:SS)
location	Nearest suburb/city

Requirements
Your fleet_dashboard.html must include:

A map — each device plotted at its GPS location, colour-coded by status
A device list — showing status, battery level, and how long ago the device was last seen
A summary — total count per status (active / idle / offline / low battery)

Rules:

Python standard library only — no pandas, folium, requests, or other third-party packages
One script → one output file (fleet_dashboard.html)
Must run in under 30 seconds
The HTML must be self-contained (no external files)
Add a comment on the code What colour/status logic you chose and why

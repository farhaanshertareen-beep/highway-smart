# Balochistan Transport Safety System
### Smart Highway & Weather Intelligence — Safety & Monitoring Command Center
> *"We don't just predict dangerous journeys. We help prevent them."*

## UI redesign
Interface restyled to match the Balochistan Transport Safety System reference screen:
- Navy / royal-blue / cyan theme with Barlow Semi Condensed headings
- Left navigation rail with icon menu (all 6 modules kept)
- Header bar: "BALOCHISTAN TRANSPORT SAFETY SYSTEM"
- Blue route map with risk-coloured routes, route labels, white city pins and red danger flags
- Per-checkpoint weather cards (temperature, wind + direction, risk label such as LOW (GREEN) / SEVERE (RED))
- Right "Quick Actions" panel with a big round Emergency SOS button, shortcut icons (SOS & Welfare, Alerts, Road Logs) and the Fast Desk tools

No feature, database table or workflow was removed or changed; this is a UI-only update.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Default login: `admin` / `admin123`

## Notes
- Needs Streamlit 1.40 or newer (for the round SOS button styling).
- The `.streamlit/config.toml` file sets the dark theme; keep it next to app.py.
- Back up your existing `highway_alerts.db` before replacing a deployed copy.

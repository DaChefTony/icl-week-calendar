# iCal Week Calendar for TRMNL / LaraPaper

A TRMNL-format plugin that shows a **rolling week** (today + 6 days) from any
published **iCalendar (ICS)** feed on e-ink dashboards – works with any
provider that can publish a calendar URL.

Two layouts, four viewports:

| View | Size | Layout |
|---|---|---|
| `full` | 800×480 | **list** (3 columns) *or* **week grid** with time axis |
| `half_horizontal` | 800×240 | list, 3 columns |
| `half_vertical` | 400×480 | list, day-grouped single column |
| `quadrant` | 400×300 | flat "upcoming events" list |

## Features

- **Polling strategy**: fetches your ICS URL every 15 minutes; server-side
  window filter −7d…+30d
- **`layout_mode`** (`full` view only): `list` or `week`
- **Week mode**: 7-day header, all-day strip, configurable hour window
  (`grid_start_hour` / `grid_end_hour`, defaults 7–21), past events dimmed
- **List mode**: content-based column chunking (no empty columns), today
  inverted, overflow engine with localized "+N more" counter
- **`list_font_size`**: framework-native size steps `small` / `base` /
  `large` / `xlarge` – titles, times, day headers and location scale together
  (day headers & location always match the time size)
- **Wall-clock correctness**: displayed times are read from the event string
  itself; the configured UTC offset is only used for day mapping (DST-safe)
- German overflow text via a tiny I18n shim (`+1 weiterer` / `+N weitere`);
  sizes follow the selected font step

## Configuration fields

| Field | Type | Default | Description |
|---|---|---|---|
| `ics_url` | string | – | Published iCal/ICS link of your calendar from your provider's share/publish settings. If it starts with `webcal://`, replace with `https://` |
| `utc_offset_hours` | select −12…12 | device | Only used for "which day is today" mapping. Empty = device timezone (DST-safe) |
| `layout_mode` | select | `list` | full view: `list` / `week` |
| `list_font_size` | select | `base` | Text size in list views (framework steps) |
| `grid_start_hour` | select 0–12 | `7` | week mode only |
| `grid_end_hour` | select 12–23 | `21` | week mode only |

## Installation

### LaraPaper
1. Download the [latest ZIP](https://github.com/DaChefTony/trmnl-icl-week-calendar/releases/latest)
   (built automatically from a tested tag).
2. Plugins → Import Recipe Archive → upload the ZIP.
3. Enter your ICS URL, pick layout and font size → Force Refresh.

### TRMNL Cloud
Install from [trmnl.com/recipes](https://trmnl.com/recipes) once published, or
upload the ZIP under Devices → Add Plugin.

## Build & Test

```bash
# build artifact (flat ZIP, 5 files; sources live in src/ for TRMNL GitHub sync)
rm -f trmnl-icl-week-calendar.zip
zip -j trmnl-icl-week-calendar.zip src/settings.yml \
    src/full.liquid \
    src/half_horizontal.liquid \
    src/half_vertical.liquid \
    src/quadrant.liquid

# render tests (python-liquid harness with patched date filter)
pip install python-liquid
python3 tests/render_test.py   # expect ALL PASS
```

CI runs the test suite on every push (see `.github/workflows/test.yml`).

## Known limitations

- Overlapping events overlap in week mode (no lane resolution yet)
- Empty calendar payloads are guarded (`events` stays undefined instead of
  crashing keepsuit/php-liquid sort)
- half_horizontal/half_vertical/quadrant ignore `layout_mode` (always list)

## License

[MIT](LICENSE) © DaChefTony

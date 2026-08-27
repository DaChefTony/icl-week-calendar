"""Render-Test fuer iCal-Wochenkalender (full.liquid mit 2 Modi: list/week)."""
import datetime as dt
import re
from pathlib import Path

import liquid
from liquid import Environment

SRC = Path(__file__).resolve().parent.parent / "icl-week-calendar"

TZ = dt.timezone(dt.timedelta(hours=2))  # Europe/Berlin Sommerzeit
now = dt.datetime(2026, 8, 26, 10, 15, tzinfo=TZ)  # Mittwoch


def iso(y, mo, d, h=0, mi=0):
    return dt.datetime(y, mo, d, h, mi, tzinfo=TZ).isoformat()


MOCK = {
    "data": {"ical": [
        {"SUMMARY": "Daily Standup", "DTSTART": iso(2026, 8, 26, 9, 0), "DTEND": iso(2026, 8, 26, 9, 15), "LOCATION": "Raum B"},
        {"SUMMARY": "Sprint Review", "DTSTART": iso(2026, 8, 26, 15, 0), "DTEND": iso(2026, 8, 26, 16, 0)},
        {"SUMMARY": "Teamurlaub", "DTSTART": iso(2026, 8, 28), "DTEND": iso(2026, 8, 31)},          # Ganztages/Multiday
        {"SUMMARY": "Dentist", "DTSTART": iso(2026, 8, 27, 14, 0), "DTEND": iso(2026, 8, 27, 14, 45), "LOCATION": "Dr. Mert"},
        {"SUMMARY": "Vergangener Termin", "DTSTART": iso(2026, 8, 26, 7, 0), "DTEND": iso(2026, 8, 26, 8, 0)},
        {"SUMMARY": "Brunch", "DTSTART": iso(2026, 8, 30, 11, 0), "DTEND": iso(2026, 8, 30, 13, 0)},
        {"SUMMARY": "Frueh", "DTSTART": iso(2026, 8, 27, 5, 30), "DTDTEND": "", "DTEND": iso(2026, 8, 27, 6, 0)},  # vor Fenster (default 7h)
        {"SUMMARY": "Termin A1", "DTSTART": iso(2026, 8, 27, 9, 0), "DTEND": iso(2026, 8, 27, 10, 0)},
        # ausserhalb des 7-Tage-Fensters:
        {"SUMMARY": "Ausserhalb Fenster", "DTSTART": iso(2026, 9, 15, 9, 0), "DTEND": iso(2026, 9, 15, 10, 0)},
        {"SUMMARY": "Vor Fenster", "DTSTART": iso(2026, 8, 20, 9, 0), "DTEND": iso(2026, 8, 20, 10, 0)},
        {"LOCATION": "Nirgendwo"},  # kein DTSTART -> ignorieren
    ]},
    "trmnl": {"user": {"utc_offset": 7200}},
}

env = Environment()
_real_date = env.filters["date"]


def date_filter(value, fmt="%d %b %Y", environment=None, **kw):
    """Emuliert Ruby-Liquid/keepsuit-UTC-Verhalten (python-liquids %s ist buggy)."""
    if isinstance(value, str) and value.strip() == "now":
        value = now
    if fmt == "%s":
        if isinstance(value, str):
            try:
                return str(int(dt.datetime.fromisoformat(value).timestamp()))
            except ValueError:
                pass
        if isinstance(value, dt.datetime):
            return str(int(value.timestamp()))
    if isinstance(value, int):
        value = dt.datetime.fromtimestamp(value, dt.timezone.utc)
    return _real_date(value, fmt, environment=env, **kw)


env.filters["date"] = date_filter

tpl = env.from_string((SRC / "full.liquid").read_text())
out_dir = Path("/tmp/opencode/wk-test")
out_dir.mkdir(parents=True, exist_ok=True)
ok = True


def render(extra_config=None):
    cfg = dict(MOCK.get("config", {}))
    if extra_config:
        cfg.update(extra_config)
    return tpl.render(data=MOCK["data"], trmnl=MOCK["trmnl"], **({"config": cfg} if cfg else {}))


def check(label, cond):
    global ok
    print(f"[{'OK  ' if cond else 'FAIL'}] {label}")
    ok = ok and cond


# ---------- Modus list (default, kein layout_mode gesetzt) ----------
html_list = render()
(out_dir / "full_list.html").write_text(html_list)
print(f"--- Modus list ({len(html_list)} bytes) ---")
check("list: .columns + 3 .column", html_list.count('class="column"') == 3)
check("list: kein Index-Streifen", 'class="index"' not in html_list)
check("list: leerer Akzent-Streifen (meta)", '<div class="meta"></div>' in html_list)
check("list: .wkl Top-Ausrichtung", "justify-content: flex-start" in html_list)
# Spalten nach INHALT: Mock-Event-Tage = Mi,Do (Spalte 1), Fr,So (Spalte 2), Spalte 3 leer
parts = html_list.split('class="column"')
check("list: Spalte 1 hat Mi/Do-Termine", "Daily Standup" in parts[1] and "Dentist" in parts[1])
check("list: Spalte 2 hat Fr/So-Termine", "Teamurlaub" in parts[2] and "Brunch" in parts[2])
check("list: Spalte 3 leer", "Standup" not in parts[3] and "Brunch" not in parts[3] and "Teamurlaub" not in parts[3])
check("list: heute invers (label--inverted)", "label--inverted" in html_list)
check("list: past grau (text--gray-40)", "text--gray-40" in html_list)
check("list: ganztägig + Teamurlaub", "ganzt" in html_list and "Teamurlaub" in html_list)
check("list: Zeitraum-Label", "&ndash;" in html_list and "09:00" in html_list)
check("list: Overflow-Engine", 'data-overflow="true"' in html_list)
check("list: ausserhalb Fenster weg", "Ausserhalb Fenster" not in html_list and "Vor Fenster" not in html_list)
check("list: title_bar unten", html_list.rfind("title_bar") > html_list.find("Standup"))
check("list: Kalender-Icon (data:URI)", "data:image/svg+xml" in html_list and "trmnl--render.svg" not in html_list)
seq = [html_list.find(x) for x in ["Vergangener", "Daily Standup", "Sprint Review", "Termin A1", "Dentist"]]
check("list: Chronologie", all(a >= 0 for a in seq) and seq == sorted(seq))

# ---------- Schriftgroesse (list_font_size, Default base) ----------
check("list: Default title--base", 'class="title title--base"' in html_list)
check("list: Default label--base", "label label--base" in html_list)
h_fs_hdr = render({"list_font_size": "large"})
check("list: Tages-Header skaliert (large)", "label label--large label--gray" in h_fs_hdr)
for fs_val, d_cls in [("small", "description--base"), ("base", "description--large"),
                      ("large", "description--xlarge"), ("xlarge", "description--xxlarge")]:
    h_d = render({"list_font_size": fs_val})
    check(f"list: Ort skaliert fs={fs_val} -> {d_cls}", f'class="description {d_cls}"' in h_d)
check("list: Default Ort = description--large", 'class="description description--large"' in html_list)
# v4.3.3: Titel-Clamp entfernt – mehrzeilige Titel wieder erlaubt,
# Overflow-Fix laeuft ueber .columns-Pfad statt Clamp
check("list: Titel ungeklemmt", '<span class="title title--base">' in html_list)
# v4.3.4: Overflow-Counter folgt list_font_size (Framework-CSS-Variablen)
CNT_SEL = '.wkl .item[data-overflow-label="true"] .label'
for fs_val, css_var in [("base", "--label-font-size"), ("small", "--label-small-font-size"),
                        ("large", "--label-large-font-size"), ("xlarge", "--label-xlarge-font-size")]:
    h_cnt = render({"list_font_size": fs_val})
    check(f"list: Counter-Groesse fs={fs_val} -> {css_var}",
          f"{CNT_SEL} {{ font-size: var({css_var}); }}" in h_cnt)
check("list: I18n-Hook (deutsch)", "andXMore" in html_list and "'+1 weiterer'" in html_list)
for fs_val, t_cls, l_cls in [("small", "title--small", "label--small"),
                             ("large", "title--large", "label--large"),
                             ("xlarge", "title--xlarge", "label--xlarge")]:
    h_fs = render({"layout_mode": None, "list_font_size": fs_val})
    check(f"list: fs={fs_val} -> {t_cls}", f'class="title {t_cls}"' in h_fs)
    check(f"list: fs={fs_val} -> {l_cls}", f"label {l_cls} label--underline" in h_fs)
# week-Modus ignoriert die Stufe (kein title--xlarge im Raster)
h_week_fs = render({"layout_mode": "week", "list_font_size": "xlarge"})
check("week: font_size ignoriert", "wkw-ev-title" in h_week_fs and 'class="title title--xlarge"' not in h_week_fs)

# ---------- Zusaetzliche Views (immer List-Stil) ----------
for view in ["half_horizontal", "half_vertical", "quadrant"]:
    tpl_v = env.from_string((SRC / f"{view}.liquid").read_text())
    html_v = tpl_v.render(data=MOCK["data"], trmnl=MOCK["trmnl"])
    (out_dir / f"{view}.html").write_text(html_v)
    print(f"--- {view} ({len(html_v)} bytes) ---")
    check(f"{view}: kein Index-Streifen", 'class="index"' not in html_v)
    check(f"{view}: leerer Akzent-Streifen (meta)", '<div class="meta"></div>' in html_v)
    check(f"{view}: past grau", "text--gray-40" in html_v)
    check(f"{view}: Ganztages + Teamurlaub", "Teamurlaub" in html_v)
    check(f"{view}: Zeitraum Wanduhrzeit (09:00)", "09:00 &ndash;" in html_v)
    check(f"{view}: Overflow-Engine", 'data-overflow="true"' in html_v)
    check(f"{view}: ausserhalb Fenster weg", "Ausserhalb Fenster" not in html_v and "Vor Fenster" not in html_v)
    check(f"{view}: title_bar unten", html_v.rfind("title_bar") > html_v.find("Standup"))
    check(f"{view}: Kalender-Icon (data:URI)", "data:image/svg+xml" in html_v and "trmnl--render.svg" not in html_v)
    if view == "half_horizontal":
        check("half_horizontal: 3 Spalten", html_v.count('class="column"') == 3)
        check("half_horizontal: .wkl Top-Ausrichtung", "justify-content: flex-start" in html_v)
        parts = html_v.split('class="column"')
        check("half_horizontal: Spalte 1 Mi/Do", "Daily Standup" in parts[1] and "Dentist" in parts[1])
        check("half_horizontal: Spalte 2 Fr/So", "Teamurlaub" in parts[2] and "Brunch" in parts[2])
    if view == "half_vertical":
        check("half_vertical: columns/column-Wrapper (1 Spalte)", html_v.count('class="column"') == 1
              and 'class="columns wkl"' in html_v)
        check("half_vertical: kein flex-Wrapper mehr", "flex flex--col gap--small" not in html_v)
        check("half_vertical: Tages-Header (Mi/So)", "Mittwoch" in html_v and "Sonntag" in html_v)
    if view == "quadrant":
        check("quadrant: columns/column-Wrapper (1 Spalte)", html_v.count('class="column"') == 1
              and 'class="columns wkl"' in html_v)
        check("quadrant: kein flex-Wrapper mehr", "flex flex--col gap--small" not in html_v)
        check("quadrant: Heute/Morgen-Tags", "Heute" in html_v and "Morgen" in html_v)
    if view != "half_horizontal":
        # v4.3.3: half_vertical/quadrant nutzen jetzt den .columns-Overflow-Pfad wie full/half_horizontal
        check(f"{view}: Titel ungeklemmt", '<span class="title title--base">' in html_v)
    check(f"{view}: Default title--base", 'class="title title--base"' in html_v)
    check(f"{view}: Default label--base", "label label--base" in html_v)
    if view == "quadrant":
        check("quadrant: keine Orts-Zeile (description)", 'class="description' not in html_v)
    else:
        h_d = tpl_v.render(data=MOCK["data"], trmnl=MOCK["trmnl"], config={"list_font_size": "base"})
        check(f"{view}: Ort skaliert (default base -> description--large)", 'class="description description--large"' in h_d)
    h_fs = tpl_v.render(data=MOCK["data"], trmnl=MOCK["trmnl"], config={"list_font_size": "large"})
    check(f"{view}: fs=large -> title--large", 'class="title title--large"' in h_fs)
    h_cnt = tpl_v.render(data=MOCK["data"], trmnl=MOCK["trmnl"], config={"list_font_size": "large"})
    check(f"{view}: Counter-Groesse fs=large",
          f"{CNT_SEL} {{ font-size: var(--label-large-font-size); }}" in h_cnt)
    # v4.3.5: deutscher Counter-Text via I18n-Hook
    check(f"{view}: I18n-Hook (deutsch)", "andXMore" in html_v and "'+1 weiterer'" in html_v)

# ---------- Modus week ----------
html_week = render({"layout_mode": "week"})
(out_dir / "full_week.html").write_text(html_week)
print(f"--- Modus week ({len(html_week)} bytes) ---")
check("week: scoped CSS vorhanden", "<style>" in html_week and ".wkw" in html_week)
check("week: volle Breite (width:100%)", ".wkw { display: flex; flex-direction: column; width: 100%;" in html_week)
check("week: Gutter position:relative", ".wkw-gutter { width: 3.4em; flex: none; position: relative; }" in html_week)
check("week: kein translateY mehr", "translateY(-50%)" not in html_week)
check("week: 7 Tageskoepfe", html_week.count('class="wkw-dayhead') == 7)
check("week: heute invers (inverse)", 'wkw-dayhead inverse' in html_week)
check("week: Stundenlabels (13 = span_h)", html_week.count('class="wkw-hour"') == 13)
check("week: Gitterlinien (7 Spalten x 14 = 98)", html_week.count('class="wkw-line"') == 98)
check("week: positionierte Event-Bloecke", len(re.findall(r'wkw-ev[^-]', html_week)) >= 5
      and 'style="top:' in html_week)
check("week: Block-Positionen plausibel (Standup 09:00 -> top ~13%)",
      bool(re.search(r'top: 1[0-9]%; height: [12]%;[^>]*">\s*<span class="wkw-ev-time">09:00', html_week))
      or bool(re.search(r'wkw-ev" style="top: 1[0-9]%; height: [12]%;">\s*<span class="wkw-ev-time">09:00', html_week)))
check("week: Ganztages-Streifen mit Teamurlaub", "wkw-allday-ev" in html_week and "Teamurlaub" in html_week)
check("week: Teamurlaub 3x (28./29./30. im Streifen)", html_week.count("Teamurlaub") == 3)
check("week: past grau (wkw-ev-past)", "wkw-ev-past" in html_week)
check("week: Frueh (05:30, vor 7h-Fenster) geklemmt bei top:0",
      bool(re.search(r'wkw-ev" style="top: 0%; height: [12]%;">\s*<span class="wkw-ev-time">05:30', html_week)))
check("week: ausserhalb Fenster weg", "Ausserhalb Fenster" not in html_week and "Vor Fenster" not in html_week)
check("week: title_bar unten", html_week.rfind("title_bar") > html_week.find("Standup"))
check("week: Kalender-Icon (data:URI)", "data:image/svg+xml" in html_week and "trmnl--render.svg" not in html_week)

# ---------- Zeitbasis: Wanduhrzeit aus dem Termin, offset-unabhaengig ----------
for offval, label in [("0", "09:00"), ("-5", "09:00"), ("2", "09:00"), (None, "09:00")]:
    cfg = {"layout_mode": "week"}
    if offval is not None:
        cfg["utc_offset_hours"] = offval
    h = render(cfg)
    check(f"week: Wanduhrzeit off={offval} -> Standup {label}", f'wkw-ev-time">{label}<' in h)
# Position stabil: Standup-Block immer bei ~14% (09:00, 7-21h-Fenster)
for offval in ("0", "-5", "2"):
    h = render({"layout_mode": "week", "utc_offset_hours": offval})
    m = re.search(r'wkw-ev[^"]*" style="top: 14%; height: 2%;">\s*<span class="wkw-ev-time">09:00<', h)
    check(f"week: Position stabil off={offval} (top 14%)", bool(m))
# list-Modus: Zeitraum aus Wanduhrzeit
h_list_tz = render({"utc_offset_hours": "0"})
check("list: Zeitraum Wanduhrzeit (Standup 09:00)", "09:00 &ndash;" in h_list_tz)

# ---------- Leerer Payload (noch nichts geladen) ----------
for view in ["full", "half_horizontal", "half_vertical", "quadrant"]:
    tpl_e = env.from_string((SRC / f"{view}.liquid").read_text())
    try:
        html_e = tpl_e.render(data={}, trmnl={"user": {"utc_offset": 7200}})
        check(f"leer: {view} rendert ohne Exception", True)
        check(f"leer: {view} zeigt 'Keine Termine'", "Keine Termine" in html_e)
    except Exception as e:
        check(f"leer: {view} rendert ohne Exception", False)
        print(f"       -> {type(e).__name__}: {e}")

print("ALL PASS" if ok else "PROBLEME GEFUNDEN")

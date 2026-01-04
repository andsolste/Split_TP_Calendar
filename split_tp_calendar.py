"""
Konfigurerbart script for å splitte NTNU TP (Timeplan) iCal-feed i flere kalendere,
med ryddig visning i Google Kalender + tydelig rapport.

================================================================================
✅ DET ENESTE DU TRENGER Å ENDRE ER "BRUKERINNSTILLINGER (USER_SETTINGS)" UNDER
================================================================================

Slik bruker du scriptet:
1) Lim inn TP-lenken din i "ICS_URL"
2) Legg inn fagene dine i "COURSES" (fagkode -> kortkode + filnavn)
3) (Valgfritt) Juster TYPE_RULES (mønstre -> typekode)
4) (Valgfritt) Legg inn EVENT_FILTERS for å fjerne repeterende ting (med unik "id")
5) Kjør scriptet

Tips:
- Sett DRY_RUN=True først for å teste uten å skrive .ics-filer.
- FAIL_FAST=True anbefales (stopper tidlig med tydelige feilmeldinger).

Du ba om:
- Dry-run toggle
- Fail fast
- Lokal tid (Europe/Oslo) i rapport + filter (slipper UTC/Z)
- Regel-ID + statistikk per filterregel
- Konfliktdetektor på tvers av ALLE output-kalendere (kun info)
- Pretty summary til slutt
"""

from __future__ import annotations
from dateutil import tz
from ics import Calendar, Event
import requests
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
import re

# =============================================================================
# BRUKERINNSTILLINGER (ALT DU SKAL ENDRE STÅR HER)
# =============================================================================
USER_SETTINGS = {
    # -------------------------------------------------------------------------
    # 1) TEST / KJØR
    # -------------------------------------------------------------------------
    "DRY_RUN": False,   # True = skriver ingen .ics-filer (trygt for testing)
    # True = stopp tidlig med tydelige feilmeldinger (anbefalt)
    "FAIL_FAST": True,

    # -------------------------------------------------------------------------
    # 2) TIDSSONE (du kan la denne stå)
    # -------------------------------------------------------------------------
    "LOCAL_TIMEZONE": "Europe/Oslo",

    # -------------------------------------------------------------------------
    # 3) TP iCal URL (LIM INN DIN HER)
    # -------------------------------------------------------------------------
    "ICS_URL": "https://tp.educloud.no/ntnu/timeplan/ical.php?sem=26v&id%5B0%5D=88047&type=student",

    # -------------------------------------------------------------------------
    # 4) FAG SOM SKAL SPLITTES UT (fagkode -> kortkode + filnavn)
    #
    # Eksempel:
    # "TDT4100": {"short": "00", "file": "00.ics"},
    #
    # - "short" brukes i kalendernavn/tittel (kort og ryddig)
    # - "file" er output-filen som skrives (må ende med .ics)
    # -------------------------------------------------------------------------
    "COURSES": {
        "TDT4100": {"short": "00", "file": "00.ics"},
        "IDATT2002": {"short": "02", "file": "02.ics"},
        "DCST1005": {"short": "05", "file": "05.ics"},
        "DCST1006": {"short": "06", "file": "06.ics"},
    },

    # -------------------------------------------------------------------------
    # 5) TYPEKODER (valgfritt, men anbefalt)
    #
    # For hvert fag: liste med regex-mønstre. Første match vinner.
    # typekoden havner i tittelen, f.eks: "00 f", "00 ØF", osv.
    # -------------------------------------------------------------------------
    "TYPE_RULES": {
        "TDT4100": [
            {"pattern": r"Øvingsforelesning", "type": "ØF"},
            {"pattern": r"Excited arbeidsdag|Excited", "type": "excited"},
            {"pattern": r"Forelesning", "type": "f"},
        ],
        "IDATT2002": [
            {"pattern": r".*", "type": "f"}
        ],
        "DCST1005": [
            {"pattern": r".*", "type": "f"}
        ],
        "DCST1006": [
            {"pattern": r".*", "type": "f"}
        ],
    },
    "DEFAULT_TYPE": "f",  # brukes hvis ingen regex i TYPE_RULES matcher

    # -------------------------------------------------------------------------
    # 6) RYDDING I DESCRIPTION
    # -------------------------------------------------------------------------
    "MAZEMAP_URL_REGEX": r"https?://use\.mazemap\.com/\S+",

    # -------------------------------------------------------------------------
    # 7) EVENT-FILTER (valgfritt): fjerner repeterende hendelser
    #
    # Viktig:
    # - Hver regel MÅ ha en unik "id" (Regel-ID)
    # - Første regel som matcher et event => event fjernes
    # - Tidspunkt (start/end) er i LOKAL tid (LOCAL_TIMEZONE)
    #
    # Nyttig workflow:
    # - Sett DRY_RUN=True
    # - Kjør og se i rapporten hva som matcher
    # - Når alt ser riktig ut: DRY_RUN=False
    # -------------------------------------------------------------------------
    "ENABLE_EVENT_FILTERS": True,
    "EVENT_FILTERS": [
        {
            # Regel-ID (PÅKREVD, unik)
            "id": "fjerne-00-man-1215-f1",

            # Match-felter (bruk kun de du trenger):
            "course_code": "TDT4100",        # valgfri: begrens til ett fag
            "title_contains": "Forelesning",  # valgfri
            "location_contains": "F1",       # valgfri
            # 0=man, 1=tir, ..., 6=søn (valgfri)
            "weekday": 0,
            "start_time": "12:15",           # "HH:MM" lokal tid (valgfri)
            "end_time": "14:00",             # "HH:MM" lokal tid (valgfri)

            # Visnings-tekst i rapporten
            "reason": "Filtrert: 00/TDT4100 Forelesning man 12:15–14:00 i F1",

            # Sikkerhets-garantier (valgfritt, men anbefalt):
            "require_at_least_one_match": True,  # FAIL_FAST hvis 0 treff
            "max_matches": 999999,               # FAIL_FAST hvis flere enn dette
        },
    ],

    # -------------------------------------------------------------------------
    # 8) KONFLIKTDETEKTOR (på tvers av ALLE output-kalendere)
    # -------------------------------------------------------------------------
    "CONFLICT_DETECTOR_ENABLED": True,
    "CONFLICTS_SHOW_MAX": 10,

    # -------------------------------------------------------------------------
    # 9) PRETTY SUMMARY (kort oppsummering helt til slutt)
    # -------------------------------------------------------------------------
    "PRETTY_SUMMARY": True,
}
# =============================================================================


# =============================================================================
# Imports (holdes samlet her for ryddighet; brukeren trenger ikke endre disse)
# =============================================================================


# =====================
# Intern CONFIG (bygges fra USER_SETTINGS)
# =====================
CONFIG = {
    "DRY_RUN": bool(USER_SETTINGS["DRY_RUN"]),
    "FAIL_FAST": bool(USER_SETTINGS["FAIL_FAST"]),
    "LOCAL_TIMEZONE": str(USER_SETTINGS["LOCAL_TIMEZONE"]),
    "ICS_URL": str(USER_SETTINGS["ICS_URL"]),
    "COURSES": dict(USER_SETTINGS["COURSES"]),
    "TYPE_RULES": dict(USER_SETTINGS["TYPE_RULES"]),
    "DEFAULT_TYPE": str(USER_SETTINGS["DEFAULT_TYPE"]),
    "MAZEMAP_URL_REGEX": str(USER_SETTINGS["MAZEMAP_URL_REGEX"]),
    "ENABLE_EVENT_FILTERS": bool(USER_SETTINGS["ENABLE_EVENT_FILTERS"]),
    "EVENT_FILTERS": list(USER_SETTINGS["EVENT_FILTERS"]),
    "CONFLICT_DETECTOR_ENABLED": bool(USER_SETTINGS["CONFLICT_DETECTOR_ENABLED"]),
    "CONFLICTS_SHOW_MAX": int(USER_SETTINGS["CONFLICTS_SHOW_MAX"]),
    "PRETTY_SUMMARY": bool(USER_SETTINGS["PRETTY_SUMMARY"]),
}

MAZEMAP_URL_RE = re.compile(CONFIG["MAZEMAP_URL_REGEX"], re.IGNORECASE)
LOCAL_TZ = tz.gettz(CONFIG["LOCAL_TIMEZONE"])


# =============================================================================
# Datamodeller
# =============================================================================
@dataclass
class ChangeFlags:
    title_changed: bool
    location_changed: bool
    description_changed: bool
    mazemap_removed: bool
    used_default_type: bool
    room_parse_failed: bool
    filtered_out: bool


@dataclass
class ReportItem:
    uid: str
    course_code: Optional[str]
    short_code: Optional[str]
    begin_raw: str
    end_raw: str
    begin_local: str
    end_local: str
    old_title: str
    new_title: Optional[str]
    old_location: str
    new_location: Optional[str]
    flags: ChangeFlags
    filter_reason: Optional[str]
    filter_id: Optional[str]


@dataclass
class FilterRuleStats:
    rule_id: str
    matched: int
    removed: int
    require_at_least_one_match: bool
    max_matches: Optional[int]
    reason: str


@dataclass
class OutputEventForConflicts:
    short_code: str
    begin_local_dt: Any
    end_local_dt: Any
    title: str
    location: str


# =============================================================================
# Fail-fast validering + små verktøy
# =============================================================================
def _die(msg: str) -> None:
    raise SystemExit(msg)


def _parse_hhmm(s: str) -> Tuple[int, int]:
    hh, mm = s.strip().split(":")
    hh_i = int(hh)
    mm_i = int(mm)
    if not (0 <= hh_i <= 23 and 0 <= mm_i <= 59):
        raise ValueError
    return (hh_i, mm_i)


def _match_optional_contains(hay: str, needle: Optional[str]) -> bool:
    if not needle:
        return True
    return needle in hay


def _match_optional_regex(text: str, pattern: Optional[str]) -> bool:
    if not pattern:
        return True
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def validate_config_fail_fast() -> None:
    if not CONFIG["ICS_URL"] or not isinstance(CONFIG["ICS_URL"], str):
        _die("FAIL_FAST: ICS_URL mangler eller er ikke tekst.")

    if not CONFIG["COURSES"] or not isinstance(CONFIG["COURSES"], dict):
        _die(
            "FAIL_FAST: COURSES er tom eller ugyldig. Legg inn fag i USER_SETTINGS['COURSES'].")

    for course_code, meta in CONFIG["COURSES"].items():
        if not isinstance(course_code, str) or not course_code.strip():
            _die("FAIL_FAST: Ugyldig fagkode i COURSES (må være ikke-tom streng).")
        if not isinstance(meta, dict):
            _die(
                f"FAIL_FAST: COURSES['{course_code}'] må være dict med 'short' og 'file'.")
        if "short" not in meta or "file" not in meta:
            _die(
                f"FAIL_FAST: COURSES['{course_code}'] må inneholde 'short' og 'file'.")
        if not isinstance(meta["short"], str) or not meta["short"]:
            _die(
                f"FAIL_FAST: COURSES['{course_code}']['short'] må være ikke-tom streng.")
        if not isinstance(meta["file"], str) or not meta["file"].endswith(".ics"):
            _die(
                f"FAIL_FAST: COURSES['{course_code}']['file'] må være et .ics filnavn.")

    # Valider TYPE_RULES-regex
    for course_code, rules in CONFIG["TYPE_RULES"].items():
        if not isinstance(rules, list):
            _die(f"FAIL_FAST: TYPE_RULES['{course_code}'] må være en liste.")
        for r in rules:
            if "pattern" not in r or "type" not in r:
                _die(
                    f"FAIL_FAST: TYPE_RULES['{course_code}'] regler må ha 'pattern' og 'type'.")
            try:
                re.compile(r["pattern"])
            except re.error as e:
                _die(
                    f"FAIL_FAST: Ugyldig regex i TYPE_RULES['{course_code}']: {e}")

    # Valider EVENT_FILTERS
    if CONFIG["ENABLE_EVENT_FILTERS"]:
        seen_ids = set()
        for idx, rule in enumerate(CONFIG.get("EVENT_FILTERS", []), start=1):
            if not isinstance(rule, dict):
                _die(f"FAIL_FAST: EVENT_FILTERS regel #{idx} må være dict.")
            rid = rule.get("id")
            if not rid or not isinstance(rid, str):
                _die(
                    f"FAIL_FAST: EVENT_FILTERS regel #{idx} mangler 'id' (må være unik streng).")
            if rid in seen_ids:
                _die(f"FAIL_FAST: EVENT_FILTERS har duplikat id: '{rid}'.")
            seen_ids.add(rid)

            weekday = rule.get("weekday")
            if weekday is not None:
                try:
                    w = int(weekday)
                except Exception:
                    _die(
                        f"FAIL_FAST: EVENT_FILTERS '{rid}': weekday må være 0-6.")
                if not (0 <= w <= 6):
                    _die(
                        f"FAIL_FAST: EVENT_FILTERS '{rid}': weekday må være 0-6.")

            for tfield in ("start_time", "end_time"):
                if rule.get(tfield):
                    try:
                        _parse_hhmm(str(rule[tfield]))
                    except Exception:
                        _die(
                            f"FAIL_FAST: EVENT_FILTERS '{rid}': {tfield} må være 'HH:MM'.")

            # max_matches
            if rule.get("max_matches") is not None:
                try:
                    mm = int(rule["max_matches"])
                    if mm < 1:
                        _die(
                            f"FAIL_FAST: EVENT_FILTERS '{rid}': max_matches må være >= 1.")
                except Exception:
                    _die(
                        f"FAIL_FAST: EVENT_FILTERS '{rid}': max_matches må være et heltall.")

    # Lokal tidssone må kunne resolves
    if LOCAL_TZ is None:
        _die(
            f"FAIL_FAST: Klarte ikke å tolke LOCAL_TIMEZONE='{CONFIG['LOCAL_TIMEZONE']}'.")


def download_ics_text_fail_fast() -> str:
    url = CONFIG["ICS_URL"]
    print("Laster ned kalender fra TP …")
    resp = requests.get(url, timeout=30)

    if resp.status_code != 200:
        _die(f"FAIL_FAST: ICS_URL returnerte status {resp.status_code}.")

    text = resp.text or ""
    if "BEGIN:VCALENDAR" not in text:
        # Typisk feil: HTML/innlogging
        snippet = text.strip().replace("\n", " ")[:200]
        _die(
            "FAIL_FAST: Nedlastet innhold ser ikke ut som iCalendar.\n"
            "Mulig innlogging/HTML eller feil URL.\n"
            f"Første tegn: {snippet}"
        )
    return text


# =============================================================================
# Tid, parsing, transform
# =============================================================================
def til_lokal_tid(dt) -> Any:
    """
    Konverter event.begin/end (typisk arrow.Arrow) til lokal tid.
    Du trenger ikke å forstå UTC/Z – rapport og filtre jobber alltid i lokal tid.
    """
    try:
        return dt.to(CONFIG["LOCAL_TIMEZONE"]).datetime  # arrow.Arrow
    except Exception:
        pass

    try:
        d = dt.datetime  # arrow.Arrow fallback
    except Exception:
        d = dt

    if getattr(d, "tzinfo", None) is None:
        d = d.replace(tzinfo=LOCAL_TZ)
    return d.astimezone(LOCAL_TZ)


def fmt_local(dt) -> str:
    d = til_lokal_tid(dt)
    # ISO-lik, men lesbart
    return d.strftime("%Y-%m-%d %H:%M")


def fjern_mazemap_lenker(tekst: str) -> Tuple[str, bool]:
    if not tekst:
        return ("", False)

    before = tekst
    after = MAZEMAP_URL_RE.sub("", before)
    removed = before != after

    after = re.sub(r"[ \t]*:[ \t]*\n", "\n", after)
    after = re.sub(r"[ \t]{2,}", " ", after)
    after = re.sub(r"\n{3,}", "\n\n", after)
    return (after.strip(), removed)


def parse_rom_og_bygg(lokasjon: str) -> Tuple[str, str, bool]:
    if not lokasjon:
        return ("", "", False)

    deler = [d.strip().strip(",")
             for d in lokasjon.strip().split() if d.strip()]
    if not deler:
        return ("", "", False)

    kandidat = deler[-1]
    rom_re = r"[A-Za-z]{0,3}\d{1,4}(?:-\d{1,4})?"

    if re.fullmatch(rom_re, kandidat):
        rom = kandidat
        bygg = lokasjon[: lokasjon.rfind(kandidat)].strip().rstrip(",").strip()
        return (rom, bygg, True)

    for tok in reversed(deler):
        if re.fullmatch(rom_re, tok):
            rom = tok
            bygg = lokasjon[: lokasjon.rfind(tok)].strip().rstrip(",").strip()
            return (rom, bygg, True)

    return (lokasjon.strip(), "", False)


def finn_fagkode(orig_tittel: str) -> Optional[str]:
    if not orig_tittel:
        return None
    for fagkode in CONFIG["COURSES"].keys():
        if fagkode in orig_tittel:
            return fagkode
    return None


def typekode_for_hendelse(fagkode: str, orig_tittel: str) -> Tuple[str, bool]:
    regler = CONFIG["TYPE_RULES"].get(fagkode, [])
    for regel in regler:
        if re.search(regel["pattern"], orig_tittel, flags=re.IGNORECASE):
            return (regel["type"], False)
    return (CONFIG["DEFAULT_TYPE"], True)


def filtrer_bort_event(
    event: Event,
    fagkode: str,
    filter_stats_by_id: Dict[str, FilterRuleStats],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returnerer (skal_filtreres, reason, rule_id).
    Oppdaterer filter-statistikk (matched/removed).
    """
    if not CONFIG.get("ENABLE_EVENT_FILTERS", True):
        return (False, None, None)

    title = event.name or ""
    loc = event.location or ""

    begin_local = til_lokal_tid(event.begin)
    end_local = til_lokal_tid(event.end)

    for regel in CONFIG.get("EVENT_FILTERS", []):
        rid = regel.get("id") or "unknown-id"

        # course_code
        if regel.get("course_code") and regel["course_code"] != fagkode:
            continue

        # title
        if not _match_optional_contains(title, regel.get("title_contains")):
            continue
        if not _match_optional_regex(title, regel.get("title_regex")):
            continue

        # location
        if not _match_optional_contains(loc, regel.get("location_contains")):
            continue
        if not _match_optional_regex(loc, regel.get("location_regex")):
            continue

        # weekday
        weekday = regel.get("weekday")
        if weekday is not None and begin_local.weekday() != int(weekday):
            continue

        # start_time
        start_time = regel.get("start_time")
        if start_time:
            hh, mm = _parse_hhmm(str(start_time))
            if not (begin_local.hour == hh and begin_local.minute == mm):
                continue

        # end_time
        end_time = regel.get("end_time")
        if end_time:
            hh, mm = _parse_hhmm(str(end_time))
            if not (end_local.hour == hh and end_local.minute == mm):
                continue

        # MATCH!
        st = filter_stats_by_id[rid]
        st.matched += 1

        max_matches = st.max_matches
        if max_matches is not None and st.matched > max_matches:
            _die(
                f"FAIL_FAST: Filterregel '{rid}' matchet mer enn max_matches={max_matches}.\n"
                f"Siste treff: '{title}' | LOCATION='{loc}' | {fmt_local(event.begin)}–{fmt_local(event.end)}"
            )

        reason = regel.get(
            "reason") or st.reason or "Filtrert: match på EVENT_FILTERS"
        st.removed += 1
        return (True, reason, rid)

    return (False, None, None)


def transformer_hendelse(
    event: Event,
    report: List[ReportItem],
    filter_stats_by_id: Dict[str, FilterRuleStats],
) -> Optional[Tuple[str, Event, OutputEventForConflicts]]:
    old_title = event.name or ""
    old_location = event.location or ""
    old_desc = event.description or ""
    uid = getattr(event, "uid", "") or ""

    begin_local_str = fmt_local(event.begin)
    end_local_str = fmt_local(event.end)

    fagkode = finn_fagkode(old_title)
    if fagkode is None:
        flags = ChangeFlags(
            title_changed=False,
            location_changed=False,
            description_changed=False,
            mazemap_removed=False,
            used_default_type=False,
            room_parse_failed=False,
            filtered_out=False,
        )
        report.append(
            ReportItem(
                uid=uid,
                course_code=None,
                short_code=None,
                begin_raw=str(event.begin),
                end_raw=str(event.end),
                begin_local=begin_local_str,
                end_local=end_local_str,
                old_title=old_title,
                new_title=None,
                old_location=old_location,
                new_location=None,
                flags=flags,
                filter_reason=None,
                filter_id=None,
            )
        )
        return None

    # Filter
    skal_filtreres, grunn, rid = filtrer_bort_event(
        event, fagkode, filter_stats_by_id)
    if skal_filtreres:
        kortkode = CONFIG["COURSES"][fagkode]["short"]
        flags = ChangeFlags(
            title_changed=False,
            location_changed=False,
            description_changed=False,
            mazemap_removed=False,
            used_default_type=False,
            room_parse_failed=False,
            filtered_out=True,
        )
        report.append(
            ReportItem(
                uid=uid,
                course_code=fagkode,
                short_code=kortkode,
                begin_raw=str(event.begin),
                end_raw=str(event.end),
                begin_local=begin_local_str,
                end_local=end_local_str,
                old_title=old_title,
                new_title=None,
                old_location=old_location,
                new_location=None,
                flags=flags,
                filter_reason=grunn,
                filter_id=rid,
            )
        )
        return None

    kortkode = CONFIG["COURSES"][fagkode]["short"]
    typekode, used_default = typekode_for_hendelse(fagkode, old_title)

    rom, bygg, ok = parse_rom_og_bygg(old_location)
    cleaned_desc, mazemap_removed = fjern_mazemap_lenker(old_desc)

    linjer = []
    linjer.append(f"Original tittel: {old_title}")
    if cleaned_desc:
        linjer.append(cleaned_desc)
    if bygg:
        linjer.append(f"Bygg: {bygg}")
    if rom:
        linjer.append(f"Rom: {rom}")
    new_desc = "\n\n".join(linjer).strip()

    new_title = f"{kortkode} {typekode}"
    new_location = rom

    flags = ChangeFlags(
        title_changed=(new_title != old_title),
        location_changed=(new_location != (
            old_location.strip() if old_location else "")),
        description_changed=(new_desc != (
            old_desc.strip() if old_desc else "")),
        mazemap_removed=mazemap_removed,
        used_default_type=used_default,
        room_parse_failed=not ok,
        filtered_out=False,
    )

    report.append(
        ReportItem(
            uid=uid,
            course_code=fagkode,
            short_code=kortkode,
            begin_raw=str(event.begin),
            end_raw=str(event.end),
            begin_local=begin_local_str,
            end_local=end_local_str,
            old_title=old_title,
            new_title=new_title,
            old_location=old_location,
            new_location=new_location,
            flags=flags,
            filter_reason=None,
            filter_id=None,
        )
    )

    ny = Event()
    ny.name = new_title
    ny.begin = event.begin
    ny.end = event.end
    ny.description = new_desc
    ny.location = new_location
    ny.uid = uid

    c = OutputEventForConflicts(
        short_code=kortkode,
        begin_local_dt=til_lokal_tid(event.begin),
        end_local_dt=til_lokal_tid(event.end),
        title=new_title,
        location=new_location,
    )

    return (kortkode, ny, c)


# =============================================================================
# Konfliktdetektor (tvers av ALLE output-kalendere)
# =============================================================================
def finn_konflikter_pa_tvers(
    events: List[OutputEventForConflicts],
    show_max: int,
) -> Tuple[int, List[Tuple[OutputEventForConflicts, OutputEventForConflicts]]]:
    """
    Returnerer (antall_konflikter, liste_med_par) der hvert par overlapper i tid.
    Vi informerer bare, vi prøver ikke å “løse” konfliktene.
    """
    if not events:
        return (0, [])

    # Sorter på start
    events_sorted = sorted(events, key=lambda e: e.begin_local_dt)

    conflicts: List[Tuple[OutputEventForConflicts,
                          OutputEventForConflicts]] = []
    active: List[OutputEventForConflicts] = []

    for ev in events_sorted:
        # Fjern events som er ferdig før denne starter
        active = [a for a in active if a.end_local_dt > ev.begin_local_dt]

        # Alt som fortsatt er "active" overlapper med ev
        for a in active:
            conflicts.append((a, ev))
            if len(conflicts) >= show_max:
                # vi trenger fortsatt totalt antall, så vi kan ikke stoppe helt her
                # men vi kan fortsette å telle uten å lagre flere detaljer
                pass

        active.append(ev)

    total_conflicts = 0
    # Tell nøyaktig antall konflikter uten å eksplodere minnet:
    # Vi gjør en ny runde som bare teller.
    active = []
    for ev in events_sorted:
        active = [a for a in active if a.end_local_dt > ev.begin_local_dt]
        total_conflicts += len(active)
        active.append(ev)

    # Begrens detaljlisten til show_max
    return (total_conflicts, conflicts[:show_max])


# =============================================================================
# Rapportering
# =============================================================================
def print_report(
    report: List[ReportItem],
    filter_stats_by_id: Dict[str, FilterRuleStats],
    conflict_total: int,
    conflict_samples: List[Tuple[OutputEventForConflicts, OutputEventForConflicts]],
    per_calendar_counts: Dict[str, int],
    dry_run: bool,
) -> None:
    total = len(report)
    matched = sum(1 for r in report if r.course_code is not None)
    unmatched = total - matched

    filtered_out = sum(1 for r in report if r.flags.filtered_out)

    title_changed = sum(1 for r in report if r.flags.title_changed)
    location_changed = sum(1 for r in report if r.flags.location_changed)
    desc_changed = sum(1 for r in report if r.flags.description_changed)
    mazemap_removed = sum(1 for r in report if r.flags.mazemap_removed)
    used_default = sum(1 for r in report if r.flags.used_default_type)
    room_parse_failed = sum(1 for r in report if (
        r.course_code is not None and r.flags.room_parse_failed and not r.flags.filtered_out))

    print("\n" + "=" * 72)
    print("RAPPORT")
    print("=" * 72)
    print(
        f"Modus:                          {'DRY RUN (ingen filer skrevet)' if dry_run else 'SKRIVER FILER'}")
    print(f"Lokal tidssone:                 {CONFIG['LOCAL_TIMEZONE']}")
    print("-" * 72)
    print(f"Totalt sett på events:            {total}")
    print(f"Matchet mot COURSES:              {matched}")
    print(f"IKKE matchet (sjekk nye fag?):    {unmatched}")
    print(f"Filtrert bort (bevisst regel):    {filtered_out}")
    print("-" * 72)
    print(f"Tittel endret (SUMMARY):          {title_changed}")
    print(f"Lokasjon endret (LOCATION):       {location_changed}")
    print(f"Beskrivelse endret (DESCRIPTION): {desc_changed}")
    print(f"MazeMap-lenke fjernet:            {mazemap_removed}")
    print(f"DEFAULT_TYPE brukt:               {used_default}")
    print(f"Fant ikke romtoken i LOCATION:    {room_parse_failed}")
    print("-" * 72)
    print(f"Konflikter på tvers av alle:      {conflict_total}")
    print("=" * 72)

    if unmatched:
        print("\n[1] Events som IKKE ble tatt med (matcher ingen fagkode i COURSES):")
        for r in report:
            if r.course_code is None:
                print(
                    f"- {r.begin_local}–{r.end_local} | '{r.old_title}' | LOCATION='{r.old_location}'")
        print("→ Løsning: Legg til fagkoden(e) i COURSES øverst.\n")

    if used_default:
        print("\n[2] Events som brukte DEFAULT_TYPE (ingen TYPE_RULE traff):")
        for r in report:
            if r.course_code is not None and r.flags.used_default_type and not r.flags.filtered_out:
                print(
                    f"- {r.course_code} | {r.begin_local}–{r.end_local} | '{r.old_title}' -> '{r.new_title}'")
        print("→ Løsning: Legg inn/juster regex i TYPE_RULES for dette faget.\n")

    if room_parse_failed:
        print("\n[3] Events der vi ikke klarte å hente ut romkode fra LOCATION:")
        for r in report:
            if r.course_code is not None and r.flags.room_parse_failed and not r.flags.filtered_out:
                print(
                    f"- {r.course_code} | {r.begin_local}–{r.end_local} | LOCATION='{r.old_location}'")
        print("→ Løsning: Sjekk hvordan LOCATION ser ut i TP, eller juster parse_rom_og_bygg().\n")

    # Filterseksjon med Regel-ID
    if CONFIG.get("ENABLE_EVENT_FILTERS", True) and filter_stats_by_id:
        print("\n[4] Filterregler (Regel-ID) – statistikk:")
        for rid, st in filter_stats_by_id.items():
            print(f"- Regel-ID: {rid}")
            print(f"  Matchet: {st.matched}")
            print(f"  Fjernet: {st.removed}")
            if st.max_matches is not None:
                print(f"  max_matches: {st.max_matches}")
            print(
                f"  require_at_least_one_match: {st.require_at_least_one_match}")
            print(f"  reason: {st.reason}")
        print()

    if filtered_out:
        print("[5] Events som ble FILTRERT BORT (bevisst regel):")
        for r in report:
            if r.flags.filtered_out:
                gr = r.filter_reason or "Filtrert (ukjent grunn)"
                rid = r.filter_id or "-"
                print(
                    f"- [{rid}] {r.course_code} | {r.begin_local}–{r.end_local} | '{r.old_title}' | LOCATION='{r.old_location}'")
                print(f"  → {gr}")
        print("→ Dette er forventet og betyr at filterregelen(e) traff.\n")

    # Konflikter (vis maks N)
    if CONFIG.get("CONFLICT_DETECTOR_ENABLED", True):
        print("[6] Konflikter på tvers av alle output-kalendere (viser inntil "
              f"{CONFIG['CONFLICTS_SHOW_MAX']}):")
        if conflict_total == 0:
            print("- Ingen konflikter funnet.\n")
        else:
            for a, b in conflict_samples:
                a_s = f"{a.begin_local_dt.strftime('%Y-%m-%d %H:%M')}–{a.end_local_dt.strftime('%H:%M')} [{a.short_code}] {a.title} ({a.location})"
                b_s = f"{b.begin_local_dt.strftime('%Y-%m-%d %H:%M')}–{b.end_local_dt.strftime('%H:%M')} [{b.short_code}] {b.title} ({b.location})"
                print(f"- Konflikt:")
                print(f"  A: {a_s}")
                print(f"  B: {b_s}")
            if conflict_total > len(conflict_samples):
                print(
                    f"- ... og {conflict_total - len(conflict_samples)} til.")
            print()

    # Eksempel-linjer
    print("[7] Eksempel-linjer (før -> etter) for de første 10 matchede events:")
    shown = 0
    for r in report:
        if r.course_code is None or r.flags.filtered_out:
            continue
        print(f"- {r.course_code} | {r.begin_local}–{r.end_local}")
        print(f"  Tittel:   '{r.old_title}' -> '{r.new_title}'")
        print(f"  Lokasjon: '{r.old_location}' -> '{r.new_location}'")
        shown += 1
        if shown >= 10:
            break

    # Pretty summary
    if CONFIG.get("PRETTY_SUMMARY", True):
        print("\n" + "=" * 72)
        print("PRETTY SUMMARY")
        print("=" * 72)
        mode = "DRY RUN (ingen filer skrevet)" if dry_run else "SKRIVER FILER"
        print(f"Modus: {mode}")
        print(f"Lokal tidssone: {CONFIG['LOCAL_TIMEZONE']}")
        print("-" * 72)
        print("Events skrevet per kalender:")
        # Stabil rekkefølge: sortér på kortkode
        for short_code in sorted(per_calendar_counts.keys()):
            print(f"  - {short_code}: {per_calendar_counts[short_code]}")
        print("-" * 72)
        if CONFIG.get("ENABLE_EVENT_FILTERS", True) and filter_stats_by_id:
            print("Filterregler:")
            for rid, st in filter_stats_by_id.items():
                print(f"  - {rid}: fjernet {st.removed} (matchet {st.matched})")
        else:
            print("Filterregler: av")
        print("-" * 72)
        print(f"DEFAULT_TYPE brukt: {used_default}")
        print(f"Rom-parse-feil:     {room_parse_failed}")
        print(f"Konflikter totalt:  {conflict_total}")
        print("=" * 72)

    print("=" * 72 + "\n")


# =============================================================================
# main
# =============================================================================
def main() -> None:
    # Fail fast: valider config før vi gjør noe
    if CONFIG["FAIL_FAST"]:
        validate_config_fail_fast()

    # Last ned ICS
    ics_text = download_ics_text_fail_fast() if CONFIG["FAIL_FAST"] else None
    if ics_text is None:
        print("Laster ned kalender fra TP …")
        resp = requests.get(CONFIG["ICS_URL"], timeout=30)
        resp.raise_for_status()
        ics_text = resp.text

    kilde = Calendar(ics_text)

    # Tom kalender for hver kortkode
    utkalendere: Dict[str, Calendar] = {}
    for _, meta in CONFIG["COURSES"].items():
        utkalendere[meta["short"]] = Calendar()

    report: List[ReportItem] = []

    # Filterstatistikk per Regel-ID
    filter_stats_by_id: Dict[str, FilterRuleStats] = {}
    if CONFIG.get("ENABLE_EVENT_FILTERS", True):
        for rule in CONFIG.get("EVENT_FILTERS", []):
            rid = rule.get("id") or "unknown-id"
            filter_stats_by_id[rid] = FilterRuleStats(
                rule_id=rid,
                matched=0,
                removed=0,
                require_at_least_one_match=bool(
                    rule.get("require_at_least_one_match", False)),
                max_matches=int(rule["max_matches"]) if rule.get(
                    "max_matches") is not None else None,
                reason=str(rule.get("reason")
                           or "Filtrert: match på EVENT_FILTERS"),
            )

    beholdt = 0
    hoppet_over = 0

    # Til konfliktsjekk (tvers av alle output-kalendere)
    all_output_events_for_conflicts: List[OutputEventForConflicts] = []

    for ev in kilde.events:
        res = transformer_hendelse(ev, report, filter_stats_by_id)
        if res is None:
            hoppet_over += 1
            continue

        kort, ny_ev, conflict_ev = res
        utkalendere[kort].events.add(ny_ev)
        all_output_events_for_conflicts.append(conflict_ev)
        beholdt += 1

    # Fail fast: krev at regler med require_at_least_one_match traff minst én gang
    if CONFIG["FAIL_FAST"] and CONFIG.get("ENABLE_EVENT_FILTERS", True):
        for rid, st in filter_stats_by_id.items():
            if st.require_at_least_one_match and st.matched == 0:
                _die(
                    f"FAIL_FAST: Filterregel '{rid}' krevde minst én match, men fant 0.\n"
                    "Sjekk at rom/tid/weekday stemmer med TP, eller slå av regelen midlertidig."
                )

    # Konfliktdetektor (tvers av alle)
    conflict_total = 0
    conflict_samples: List[Tuple[OutputEventForConflicts,
                                 OutputEventForConflicts]] = []
    if CONFIG.get("CONFLICT_DETECTOR_ENABLED", True):
        conflict_total, conflict_samples = finn_konflikter_pa_tvers(
            all_output_events_for_conflicts,
            show_max=CONFIG["CONFLICTS_SHOW_MAX"],
        )

    # Tell per kalender
    per_calendar_counts: Dict[str, int] = {k: 0 for k in utkalendere.keys()}
    for short_code, cal in utkalendere.items():
        per_calendar_counts[short_code] = len(cal.events)

    print(f"Behandlet events: {beholdt} (hoppet over: {hoppet_over})")

    # Skriv filer (med DRY_RUN toggle)
    if CONFIG["DRY_RUN"]:
        print("DRY RUN: skriver ingen .ics-filer.")
    else:
        print("Skriver .ics-filer …")
        for fagkode, meta in CONFIG["COURSES"].items():
            kort = meta["short"]
            filnavn = meta["file"]
            with open(filnavn, "w", encoding="utf-8", newline="\n") as f:
                f.write(utkalendere[kort].serialize())

        print("Filer skrevet:")
        for fagkode, meta in CONFIG["COURSES"].items():
            print(f" - {meta['file']}   (fag {fagkode} -> {meta['short']})")

    # Rapport til slutt
    print_report(
        report=report,
        filter_stats_by_id=filter_stats_by_id,
        conflict_total=conflict_total,
        conflict_samples=conflict_samples,
        per_calendar_counts=per_calendar_counts,
        dry_run=CONFIG["DRY_RUN"],
    )


if __name__ == "__main__":
    main()

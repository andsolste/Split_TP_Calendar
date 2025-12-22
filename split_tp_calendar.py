"""
Konfigurerbart script for å splitte NTNU TP (Timeplan) iCal-feed i flere kalendere,
med ryddig visning i Google Kalender + tydelig rapport.

✅ Designmål:
- Korte titler i kalenderoversikten (SUMMARY) på format: "<KORTKODE> <TYPE>"
- LOCATION viser kun romkode (R1, A2-107, EL3 …)
- DESCRIPTION inneholder all info (renset for MazeMap-lenke) + eksplisitt Bygg/Rom
- Eksporterer fortsatt .ics-filer

🧾 Rapport:
- Printer hvor mange events som ble:
  - endret (tittel/lokasjon/beskrivelse/mazemap)
  - ikke endret på enkelte felt (f.eks. hvis LOCATION allerede var rom)
- Printer alle events som:
  - ikke matcher noen fagkode (du har glemt å legge til fag i CONFIG["COURSES"])
  - matcher et fag, men faller tilbake til DEFAULT_TYPE (du har glemt TYPE_RULES for en ny tittel)
  - har LOCATION som vi ikke klarte å trekke ut rom fra (må sjekkes)

=====================
ALT DU SKAL ENDRE STÅR HER (CONFIG)
=====================
1) CONFIG["ICS_URL"]:
   - Lim inn studentgruppe-ICS URL fra TP

2) CONFIG["COURSES"]:
   - Legg til/fjern fag ved å legge inn en ny nøkkel (fagkode)
   - "short" er kortkoden du vil se i kalenderen (f.eks. "00")
   - "file" er filnavnet som skrives ut (f.eks. "00.ics")

3) CONFIG["TYPE_RULES"]:
   - For hvert fag: en liste med regler (regex) -> typekode
   - Første match vinner.
   - Hvis ingenting matcher: DEFAULT_TYPE brukes og rapporterer dette.

4) Etterarbeid (GitHub – én gang oppsett, deretter enkelt):
   - Gå til https://github.com og logg inn
   - Trykk “New repository”
   - Gi repoet et navn (f.eks. timeplan-ics)
   - Velg “Public” og trykk “Create repository”
   - Last opp .ics-filene via “Add file → Upload files”
   - Etter opplasting: klikk på en fil → “Raw” → kopier URL-en
   - Bruk denne raw-URL-en i Google Kalender (Innstillinger → Legg til kalender → Fra URL)

   Neste gang:
   - Kjør scriptet på nytt
   - Last opp og overskriv filene i samme repo
   - Google Kalender oppdaterer seg automatisk

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import requests
from ics import Calendar, Event


# =====================
#        CONFIG
# =====================
CONFIG = {
    # 1) TP iCal URL (studentgruppe). Lim inn din her:
    "ICS_URL": "https://tp.educloud.no/ntnu/timeplan/ical.php?sem=26v&id%5B0%5D=88047&type=student",

    # 2) Fag du vil splitte ut:
    "COURSES": {
        "TDT4100": {"short": "00", "file": "00.ics"},
        "IDATT2002": {"short": "02", "file": "02.ics"},
        "DCST1005": {"short": "05", "file": "05.ics"},
        "DCST1006": {"short": "06", "file": "06.ics"},
    },

    # 3) Typekoder per fag: (regex) -> typekode
    "TYPE_RULES": {
        "TDT4100": [
            {"pattern": r"Øvingsforelesning", "type": "ØF"},
            {"pattern": r"Excited arbeidsdag|Excited", "type": "excited"},
            {"pattern": r"Forelesning", "type": "f"},
        ],
        "IDATT2002": [
            {"pattern": r".*", "type": "f"},
        ],
        "DCST1005": [
            {"pattern": r".*", "type": "f"},
        ],
        "DCST1006": [
            {"pattern": r".*", "type": "f"},
        ],
    },

    # Default typekode hvis et fag mangler regler eller ingenting matcher:
    "DEFAULT_TYPE": "f",

    # MazeMap: hvilke URL-er som fjernes fra DESCRIPTION
    "MAZEMAP_URL_REGEX": r"https?://use\.mazemap\.com/\S+",
}
# =====================


MAZEMAP_URL_RE = re.compile(CONFIG["MAZEMAP_URL_REGEX"], re.IGNORECASE)


@dataclass
class ChangeFlags:
    title_changed: bool
    location_changed: bool
    description_changed: bool
    mazemap_removed: bool
    used_default_type: bool
    room_parse_failed: bool


@dataclass
class ReportItem:
    uid: str
    course_code: Optional[str]
    short_code: Optional[str]
    begin: str
    end: str
    old_title: str
    new_title: Optional[str]
    old_location: str
    new_location: Optional[str]
    flags: ChangeFlags


def fjern_mazemap_lenker(tekst: str) -> Tuple[str, bool]:
    """Fjerner MazeMap-URL-er. Returnerer (ny_tekst, fjernet_noe)."""
    if not tekst:
        return ("", False)

    before = tekst
    after = MAZEMAP_URL_RE.sub("", before)

    removed = before != after

    # Rydd opp i rester som "EL3: " etter lenkefjerning
    after = re.sub(r"[ \t]*:[ \t]*\n", "\n", after)
    after = re.sub(r"[ \t]{2,}", " ", after)
    after = re.sub(r"\n{3,}", "\n\n", after)
    return (after.strip(), removed)


def parse_rom_og_bygg(lokasjon: str) -> Tuple[str, str, bool]:
    """
    Returnerer (rom, bygg, ok) fra LOCATION.
    ok=False betyr at vi ikke fant et tydelig romtoken.
    """
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
    """Finn fagkode ved å sjekke om en av CONFIG['COURSES']-nøklene finnes i tittelen."""
    if not orig_tittel:
        return None
    for fagkode in CONFIG["COURSES"].keys():
        if fagkode in orig_tittel:
            return fagkode
    return None


def typekode_for_hendelse(fagkode: str, orig_tittel: str) -> Tuple[str, bool]:
    """
    Bestemmer typekode via CONFIG["TYPE_RULES"].
    Returnerer (typekode, brukt_default).
    """
    regler = CONFIG["TYPE_RULES"].get(fagkode, [])
    for regel in regler:
        if re.search(regel["pattern"], orig_tittel, flags=re.IGNORECASE):
            return (regel["type"], False)
    return (CONFIG["DEFAULT_TYPE"], True)


def transformer_hendelse(event: Event, report: List[ReportItem]) -> Optional[Tuple[str, Event]]:
    """
    Lager en ny, ryddet hendelse.
    Returnerer (kortkode, ny_hendelse) eller None hvis hendelsen ikke tilhører våre fag.
    Logger også alt som skjer til rapporten.
    """
    old_title = event.name or ""
    old_location = event.location or ""
    old_desc = event.description or ""
    uid = getattr(event, "uid", "") or ""

    fagkode = finn_fagkode(old_title)
    if fagkode is None:
        # Ikke vår hendelse: logg som "ikke matchet"
        flags = ChangeFlags(
            title_changed=False,
            location_changed=False,
            description_changed=False,
            mazemap_removed=False,
            used_default_type=False,
            room_parse_failed=False,
        )
        report.append(
            ReportItem(
                uid=uid,
                course_code=None,
                short_code=None,
                begin=str(event.begin),
                end=str(event.end),
                old_title=old_title,
                new_title=None,
                old_location=old_location,
                new_location=None,
                flags=flags,
            )
        )
        return None

    kortkode = CONFIG["COURSES"][fagkode]["short"]
    typekode, used_default = typekode_for_hendelse(fagkode, old_title)

    rom, bygg, ok = parse_rom_og_bygg(old_location)

    cleaned_desc, mazemap_removed = fjern_mazemap_lenker(old_desc)

    # Ny beskrivelse: behold info + Bygg/Rom eksplisitt
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
    new_location = rom  # kun rom i LOCATION

    # Endringsflagg
    flags = ChangeFlags(
        title_changed=(new_title != old_title),
        location_changed=(new_location != (
            old_location.strip() if old_location else "")),
        description_changed=(new_desc != (
            old_desc.strip() if old_desc else "")),
        mazemap_removed=mazemap_removed,
        used_default_type=used_default,
        room_parse_failed=not ok,
    )

    report.append(
        ReportItem(
            uid=uid,
            course_code=fagkode,
            short_code=kortkode,
            begin=str(event.begin),
            end=str(event.end),
            old_title=old_title,
            new_title=new_title,
            old_location=old_location,
            new_location=new_location,
            flags=flags,
        )
    )

    # Lag ny Event
    ny = Event()
    ny.name = new_title
    ny.begin = event.begin
    ny.end = event.end
    ny.description = new_desc
    ny.location = new_location
    ny.uid = uid

    return (kortkode, ny)


def print_report(report: List[ReportItem]) -> None:
    total = len(report)
    matched = sum(1 for r in report if r.course_code is not None)
    unmatched = total - matched

    title_changed = sum(1 for r in report if r.flags.title_changed)
    location_changed = sum(1 for r in report if r.flags.location_changed)
    desc_changed = sum(1 for r in report if r.flags.description_changed)
    mazemap_removed = sum(1 for r in report if r.flags.mazemap_removed)
    used_default = sum(1 for r in report if r.flags.used_default_type)
    room_parse_failed = sum(1 for r in report if (
        r.course_code is not None and r.flags.room_parse_failed))

    print("\n" + "=" * 72)
    print("RAPPORT")
    print("=" * 72)
    print(f"Totalt sett på events:            {total}")
    print(f"Matchet mot CONFIG['COURSES']:    {matched}")
    print(f"IKKE matchet (sjekk nye fag?):    {unmatched}")
    print("-" * 72)
    print(f"Tittel endret (SUMMARY):          {title_changed}")
    print(f"Lokasjon endret (LOCATION):       {location_changed}")
    print(f"Beskrivelse endret (DESCRIPTION): {desc_changed}")
    print(f"MazeMap-lenke fjernet:            {mazemap_removed}")
    print(f"DEFAULT_TYPE brukt (sjekk regler):{used_default}")
    print(f"Fant ikke romtoken i LOCATION:    {room_parse_failed}")
    print("=" * 72)

    # Detaljseksjoner (kun når relevant)
    if unmatched:
        print(
            "\n[1] Events som IKKE ble tatt med (matcher ingen fagkode i CONFIG['COURSES']):")
        for r in report:
            if r.course_code is None:
                print(
                    f"- {r.begin} | '{r.old_title}' | LOCATION='{r.old_location}'")
        print("→ Løsning: Legg til fagkoden(e) i CONFIG['COURSES'] øverst.\n")

    if used_default:
        print("\n[2] Events som brukte DEFAULT_TYPE (ingen TYPE_RULE traff):")
        for r in report:
            if r.course_code is not None and r.flags.used_default_type:
                print(
                    f"- {r.course_code} | {r.begin} | '{r.old_title}' -> '{r.new_title}'")
        print(
            "→ Løsning: Legg inn/juster regex i CONFIG['TYPE_RULES'] for dette faget.\n")

    if room_parse_failed:
        print("\n[3] Events der vi ikke klarte å hente ut romkode fra LOCATION:")
        for r in report:
            if r.course_code is not None and r.flags.room_parse_failed:
                print(
                    f"- {r.course_code} | {r.begin} | LOCATION='{r.old_location}'")
        print("→ Løsning: Sjekk hvordan LOCATION ser ut i TP, eller juster parse_rom_og_bygg().\n")

    print("\n[4] Eksempel-linjer (før -> etter) for de første 10 matchede events:")
    shown = 0
    for r in report:
        if r.course_code is None:
            continue
        print(f"- {r.course_code} | {r.begin}")
        print(f"  Tittel:   '{r.old_title}' -> '{r.new_title}'")
        print(f"  Lokasjon: '{r.old_location}' -> '{r.new_location}'")
        shown += 1
        if shown >= 10:
            break
    print("=" * 72 + "\n")


def main() -> None:
    ics_url = CONFIG["ICS_URL"]
    if "LIM_INN_ICS_LENKEN_DIN_HER" in ics_url:
        raise SystemExit(
            "Du må lime inn CONFIG['ICS_URL'] øverst før du kjører scriptet.")

    print("Laster ned kalender fra TP …")
    resp = requests.get(ics_url, timeout=30)
    resp.raise_for_status()
    kilde = Calendar(resp.text)

    # Tom kalender for hver kortkode
    utkalendere: Dict[str, Calendar] = {}
    for _, meta in CONFIG["COURSES"].items():
        utkalendere[meta["short"]] = Calendar()

    report: List[ReportItem] = []

    beholdt = 0
    hoppet_over = 0

    for ev in kilde.events:
        res = transformer_hendelse(ev, report)
        if res is None:
            hoppet_over += 1
            continue
        kort, ny_ev = res
        utkalendere[kort].events.add(ny_ev)
        beholdt += 1

    print(f"Behandlet events: {beholdt} (hoppet over: {hoppet_over})")
    print("Skriver .ics-filer …")
    for fagkode, meta in CONFIG["COURSES"].items():
        kort = meta["short"]
        filnavn = meta["file"]
        with open(filnavn, "w", encoding="utf-8", newline="\n") as f:
            f.write(utkalendere[kort].serialize())

    print("Filer skrevet:")
    for fagkode, meta in CONFIG["COURSES"].items():
        print(f" - {meta['file']}   (fag {fagkode} -> {meta['short']})")

    # Til slutt: print rapporten som gjør det tydelig om du har glemt noe
    print_report(report)


if __name__ == "__main__":
    main()

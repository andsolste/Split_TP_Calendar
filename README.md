# 📅 Split TP Calendar (NTNU)

Dette prosjektet gjør NTNU sin **TP-kalender (Timeplan)** mye enklere å bruke ved å splitte én stor iCal-kalender opp i **én ryddig kalender per fag**.

Resultatet er flere `.ics`-filer som kan abonneres på i **Google Kalender**, slik at du:
- kan gi hvert fag sin egen farge 🎨
- slipper lange og rotete titler
- får bedre oversikt i uke- og dagsvisning
- kan filtrere bort ting du ikke vil se

Prosjektet er laget for **NTNU-studenter**, også for deg uten IT-bakgrunn.

---

## 📖 Innholdsfortegnelse
1. Hva gjør scriptet?
2. Hvordan fungerer det i praksis?
3. Filer i prosjektet
4. Kom i gang (steg-for-steg)
5. Hva må du endre i Python-filen?
6. Event-filter (kort forklart)
7. Kjøring via .bat-fil
8. Automatisk kjøring med Task Scheduler (Windows)
9. Automatisk oppdatering til Google Kalender (GitHub)
10. Viktig å vite om Google Kalender
11. Status

---

## 🎯 Hva gjør scriptet?

Når du kjører `split_tp_calendar.py`:

- 📥 Laster ned **én samlet TP-kalender** (iCal-lenke fra NTNU)
- ✂️ Deler den opp i **én `.ics`-fil per fag**
- 🏷️ Gir korte, konsistente titler (f.eks. `00 f`, `00 ØF`)
- 📝 Flytter detaljer til beskrivelsen
- 🗺️ Fjerner MazeMap-lenker, men beholder bygg og rom
- 🚫 Kan filtrere bort uønskede hendelser (valgfritt)
- ⚠️ Sjekker konflikter på tvers av alle fag
- 📊 Gir tydelig rapport + kort *pretty summary*

Alt er optimalisert for **Google Kalender**.

---

## 🔄 Hvordan fungerer det i praksis?

1. Du abonnerer på hver `.ics`-fil i Google Kalender  
2. Scriptet kjøres automatisk på PC-en din  
3. `.ics`-filene oppdateres  
4. Google Kalender oppdaterer seg selv 🎉  

Du trenger **ikke** å importere på nytt hver gang.

---

## 📁 Filer i prosjektet

| Fil | Hva den brukes til |
|---|---|
| `split_tp_calendar.py` | Hovedscriptet |
| `00.ics`, `02.ics`, osv. | Ferdige kalendere (én per fag) |
| `click_to_run.bat` | Kjører Python-scriptet |
| `README.md` | Denne filen |

---

## 🚀 Kom i gang (steg-for-steg)

### 1️⃣ Klon eller last ned prosjektet
Legg prosjektet et sted som **ikke flyttes** (viktig for automatisering).

### 2️⃣ Installer Python (hvis du ikke har)
Last ned fra https://www.python.org  
✔️ Huk av for **Add Python to PATH** under installasjon.

### 3️⃣ Installer nødvendige pakker
Åpne **Kommandolinje / PowerShell** i prosjektmappen og kjør:
```bash
pip install ics requests python-dateutil
```

---

## ⚙️ Hva må du endre i Python-filen?

👉 **ALT du skal endre ligger samlet øverst i `split_tp_calendar.py`.**  
Du trenger aldri å røre resten av koden.

### 🔹 1. TP-lenke
Lim inn din egen TP-iCal-lenke:
```python
"ICS_URL": "https://tp.educloud.no/ntnu/timeplan/ical.php?...",
```

### 🔹 2. Fagene dine
Legg inn fagkode, kortkode og filnavn:
```python
"COURSES": {
  "TDT4100": {"short": "00", "file": "00.ics"},
  "IDATT2002": {"short": "02", "file": "02.ics"},
}
```

### 🔹 3. Test først (anbefalt)
```python
"DRY_RUN": True
```
Da skrives ingen filer – kun rapport.

Når alt ser riktig ut:
```python
"DRY_RUN": False
```

---

## 🚫 Event-filter (kort forklart)

Event-filter brukes for å fjerne bestemte hendelser automatisk, f.eks.:
- faste forelesninger du ikke vil se
- bestemte dager/tidspunkt
- spesifikke rom eller titler

Hver regel har:
- Regel-ID
- tydelig grunn (vises i rapporten)

👉 Alt er ment å være selvforklarende i toppen av fila.

---

## ▶️ Kjøring via .bat-fil

`click_to_run.bat`:
- starter Python-scriptet
- kan kjøres manuelt (dobbeltklikk)
- brukes av Task Scheduler

👉 Du trenger ikke endre `.bat`-fila så lenge filnavnene er de samme.

---

## ⏰ Automatisk kjøring med Task Scheduler (Windows)

1. Åpne **Task Scheduler**  
2. Velg **Create Task**
3. **General**:
   - Name: Split TP Calendar  
   - Huk av for *Run whether user is logged on or not*  
   - Huk av for *Run with highest privileges*
4. **Triggers**:
   - New → f.eks. *At log on* eller *Daily at 21:00*
5. **Actions**:
   - Program/script: `click_to_run.bat`
   - Start in: prosjektmappen (veldig viktig)
6. Lagre og skriv inn Windows-passord hvis du blir spurt

✅ Scriptet kjører nå automatisk.

---

## 🔄 Automatisk oppdatering til Google Kalender (GitHub)

1. Push `.ics`-filene til GitHub  
2. For hver kalender:
   - Åpne filen i GitHub
   - Klikk **Raw**
   - Kopier URL-en
   - Google Kalender → Innstillinger → Legg til kalender → Fra URL

Google vil nå hente oppdateringer automatisk.

---

## 📅 Viktig å vite om Google Kalender

- ⏳ Oppdatering skjer asynkront  
- ❌ Ikke slett og legg til på nytt  
- ✅ Bare vent – oppdateringen kommer  

Dette er helt normalt.

---

## ✅ Status

Dette prosjektet er:
- stabilt over tid
- lett å gjenbruke neste semester
- laget for ikke-tekniske brukere
- optimalisert for Google Kalender

Lykke til – og nyt en ryddigere timeplan 🙌

# Split TP Calendar (NTNU)

Dette prosjektet brukes til å **splitte NTNU sin TP (Timeplan)-kalender** i flere separate `.ics`-kalendere – én per fag – slik at de enkelt kan abonneres på i **Google Kalender** med egne farger.

Prosjektet er laget for å:
- filtrere bort irrelevante aktiviteter
- rydde titler og beskrivelser
- gjøre kalenderen mer lesbar i uke-/dagsvisning
- fungere stabilt over tid (og neste studieår)

---

## ✨ Hva scriptet gjør

- Leser én samlet TP-iCal (studentgruppe)
- Deler den opp i flere `.ics`-filer (én per fag)
- Gir korte og konsistente titler (f.eks. `06 f`, `00 ØF`, `00 excited`)
- Flytter all detaljert informasjon til beskrivelsen
- Fjerner MazeMap-lenker, men beholder bygg og rom
- Skriver Google-kompatible `.ics`-filer (RFC 5545)
- Kan kjøres **helt automatisk** ved oppstart
- Kan **automatisk commite og pushe** endringer til GitHub

---

## 📁 Output

Scriptet genererer én `.ics`-fil per fag, for eksempel:

```
00.ics   (TDT4100)
02.ics   (IDATT2002)
05.ics   (DCST1005)
06.ics   (DCST1006)
```

Disse kan legges til i Google Kalender via  
**Innstillinger → Legg til kalender → Fra URL**.

---

## ⚙️ Konfigurasjon (øverst i scriptet)

Alle ting som normalt må endres (nye fag, nytt semester) ligger samlet øverst i Python-scriptet:

- TP-lenke (`ICS_URL`)
- Fagkoder → kortkoder (`COURSES`)
- Regler for typer (`TYPE_RULES`)
- Standardtype (`DEFAULT_TYPE`)

Dette gjør scriptet enkelt å gjenbruke neste år.

---

## 🚀 Automatisk kjøring + auto-commit (Windows)

Prosjektet støtter full automatisering ved hjelp av en `.bat`-fil.

### Hva skjer automatisk?
Når du starter PC-en eller logger inn:

1. Python-scriptet kjøres
2. `.ics`-filene oppdateres
3. Endringer committes til Git
4. Endringer pushes til GitHub
5. Google Kalender oppdaterer seg selv via abonnement

---

## 🧩 `run_and_push.bat`

Lag en fil i prosjektmappen som heter:

```
run_and_push.bat
```

📄 Logg skrives til:
```
Desktop\split_tp_log.txt
```

---

## 🖥️ Kjør automatisk ved oppstart (Startup)

1. Trykk **Win + R**
2. Skriv:
   ```
   shell:startup
   ```
3. Trykk Enter
4. Lag en **snarvei** til `run_and_push.bat` i denne mappen

Scriptet kjøres nå automatisk hver gang du logger inn.

---

## 🔐 GitHub (én gangs oppsett)

For at push skal fungere automatisk:

1. Åpne terminal i prosjektmappen
2. Kjør:
   ```bash
   git push
   ```
3. Logg inn på GitHub hvis du blir spurt

Git lagrer legitimasjonen, slik at `.bat`-fila kan pushe uten input senere.

---

## 📅 Google Kalender

For hver `.ics`-fil:

1. Åpne fila i GitHub
2. Klikk **Raw**
3. Kopier URL-en
4. Google Kalender → **Innstillinger → Legg til kalender → Fra URL**
5. Lim inn URL-en

📌 Oppdatering skjer automatisk (kan ta litt tid).

---

## ℹ️ Viktig å vite

- Google Kalender oppdaterer eksterne kalendere **asynkront**
- Det er normalt at én kalender dukker opp før en annen
- Ikke slett og legg til på nytt – bare vent

---

## ✅ Status

Dette oppsettet er:
- stabilt
- Google-kompatibelt
- framtidssikkert
- laget for gjenbruk neste studieår
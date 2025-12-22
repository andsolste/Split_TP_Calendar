# 📅 NTNU Timeplan → Ryddig Google Kalender

Dette repoet inneholder et Python-script som **rydder og splitter NTNU TP (Timeplan) iCal-feed** til flere separate kalendere – én per fag – optimalisert for Google Kalender.

Målet er en **ren og oversiktlig kalender** der:

* fag vises med **korte koder**
* rom er lett synlige
* all detaljinformasjon fortsatt er tilgjengelig
* uregelmessige hendelser kan skilles tydelig fra vanlig undervisning

---

## ✨ Hva scriptet gjør

Scriptet:

* 📥 laster ned én samlet `.ics`-fil fra NTNU Timeplan (studentgruppe)
* ✂️ splitter kalenderen i **én fil per fag**
* 🏷️ forkorter titler til formatet:
  `KORTKODE TYPE` (f.eks. `00 f`, `00 ØF`, `00 excited`)
* 📍 viser **kun romkode** i kalenderoversikten (R1, A2-107, EL3 …)
* 🏢 legger **bygg + rom** i beskrivelsen
* 🧹 fjerner **MazeMap-lenker** (beholder tekst)
* 📊 skriver en **rapport i terminalen** som viser:

  * hva som er endret
  * hva som ikke er endret
  * hvilke hendelser som ikke matcher et fag
  * hvilke hendelser som bruker fallback-regler

Scriptet **eksporterer fortsatt `.ics`-filer**, klare til å brukes i Google Kalender via URL-abonnement.

---

## 🧠 Designfilosofi

* **Rolig kalender** → korte titler og dempede farger
* **Viktig info ved klikk** → alt ligger i beskrivelsen
* **Fremtidssikker** → fag og regler endres kun øverst i config
* **Feilsikker** → rapport varsler hvis noe er glemt

---

## 🛠️ Bruk

### 1️⃣ Installer avhengigheter

```bash
pip install ics requests
```

### 2️⃣ Konfigurer

Åpne `split_tp_calendar.py` og endre kun dette øverst:

* `ICS_URL` → TP-lenken din
* `COURSES` → fagkoder, kortkoder og filnavn
* `TYPE_RULES` → hvordan titler mappes til `f`, `ØF`, `excited`, osv.

### 3️⃣ Kjør

```bash
python split_tp_calendar.py
```

### 4️⃣ Last opp til GitHub

* Last opp de genererte `.ics`-filene til dette repoet
* Klikk på en fil → **Raw**
* Bruk raw-URL-en i Google Kalender:
  *Innstillinger → Legg til kalender → Fra URL*

Neste gang:

* Kjør scriptet på nytt
* Overskriv filene i repoet
* Google Kalender oppdateres automatisk 🎉

---

## 📄 Filer i repoet

* `split_tp_calendar.py` – hovedscript
* `00.ics`, `02.ics`, `05.ics`, `06.ics` – genererte kalendere (eksempel)

---

## 🎓 Målgruppe

* NTNU-studenter
* Folk som vil ha **full kontroll** på kalenderen sin
* Deg som liker **struktur, lav visuell støy og automatisering**

---

## ✅ Status

Prosjektet er ferdig, stabilt og i daglig bruk.


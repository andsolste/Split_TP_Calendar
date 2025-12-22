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
02.

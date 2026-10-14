---
generated-from-commit: nessuno
generated-from-branch: main
generated-date: 2026-10-14
covers-paths:
  - caso/media/**
  - tools/leggi-schermate.py
  - tools/aggiorna.py
  - caso/data/**
last-verified-commit: nessuno
stato: in corso
---

# Lavoro in corso

> La fonte di verità su cosa è fatto resta `memory/index.md` e il work-log, non le spunte di questo file.

## Feature: lettura delle immagini nuove del S25 Ultra

Cosa fa: il proprietario manda immagini nuove; si mettono in `caso/media/_arrivo/`, si assorbono con `python tools/aggiorna.py ingest`, il lettore locale ne fa la bozza e il foglio dei ritagli dubbi, e le letture si trascrivono in `caso/data/` dopo averle verificate.

Stato: il lettore è scritto e collaudato sulla finestra 4; il flusso `ingest` è provato sul caso del file già presente. Manca la prima prova su immagini davvero nuove.

Definition of done: immagini nuove in `caso/media/` con catalogo aggiornato; letture trascritte in una finestra di `caso/data/` (se il periodo è nuovo, finestra aggiunta a `FINESTRE` in `tools/catalogo.py` e decisione su come parametrizzare `tools/genera-grafici.py`, che legge la finestra 4 per nome); documenti aggiornati con un addendum se riguardano materiale già consegnato; `python tools/aggiorna.py` con otto controlli verdi.

Domande aperte: a quale periodo appartengono le immagini nuove; se vanno in un documento nuovo o in un addendum.

Limiti d'ambiente: `caso/media/` è fuori da git ed è l'unica copia degli originali.

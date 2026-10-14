---
generated-from-commit: nessuno
generated-from-branch: main
generated-date: 2026-10-14
covers-paths:
  - tools/**
  - caso/data/**
  - caso/media/CATALOGO.csv
last-verified-commit: nessuno
---

# Stack e flussi

Python 3.13 su Windows, senza dipendenze di rete. Librerie: Pillow e numpy per le immagini, `rapidocr_onnxruntime` per l'OCR locale, Edge o Chrome in modalità headless per la stampa in PDF (`tools/genera-pdf.py`, profilo in `caso/lavorazione/.profilo-stampa`).

Il flusso è in due comandi di `tools/aggiorna.py`. `ingest` assorbe in `caso/media/` i file di `caso/media/_arrivo/` o di una cartella data, salta per hash quelli già presenti, aggiorna il catalogo con `tools/catalogo.py` (sessioni di cattura con scarto di 180 s, finestre da `FINESTRE`) e lancia `tools/leggi-schermate.py` sulle schermate nuove del S25 Ultra. Il comando senza argomenti rigenera in ordine `genera-grafici.py` (frammenti da `caso/data/finestra4-*`), `genera-aggiornamento.py`, `genera-reperti.py` (reperti letti dal catalogo, ruolo `reperto`), `genera-appendici.py`, `md-to-html.py` per ogni `.md` di `caso/consegna/` e `caso/fascicolo/`, `genera-pdf.py`, e chiude con otto controlli.

Ruolo dei file principali:

```
tools/catalogo.py          lettura e scrittura di caso/media/CATALOGO.csv, hash, istanti, dispositivo, sessioni, marcatura prova
tools/leggi-schermate.py   OCR locale delle schermate 1440x3120: bozza in caso/lavorazione/bozze/ e foglio dei ritagli dubbi
tools/unifica-media.py     unificazione una tantum dell'ottobre 2026 e svuotamento di J:, con il rapporto di provenienza
tools/aggiorna.py          orchestratore: ingest, rigenerazione, controlli
tools/genera-grafici.py    frammenti grafici e tabellari della finestra 4 (legge i file finestra4 per nome)
caso/data/finestraN-*      rilevazioni trascritte, una finestra per periodo di osservazione
```

Il lettore delle schermate riconosce sei tipi di schermata (Home, Batteria con autonomia, Batteria con dettaglio A/B, Battery Management, Information Center, Past Routes). La scheda A o B attiva si riconosce dal fondo più chiaro; i valori persi dal rilevatore si rileggono con `text_recognizer` sul riquadro fisso a destra dell'etichetta.

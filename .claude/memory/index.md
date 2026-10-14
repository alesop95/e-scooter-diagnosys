# Snapshot di sincronizzazione

> Da leggere per primo a inizio sessione. Fotografa lo stato del progetto al commit di riferimento e mappa ogni scheda al suo stato di verifica. È la fonte di verità su cosa è fatto, non le spunte del diario.

## Stato

```
Branch attivo:        main
Commit di riferimento: nessuno, il repository è stato inizializzato il 2026-10-14 e il primo commit lo fa l'utente
Data snapshot:        2026-10-14
Albero autorevole:    unico
Ambienti:             nessuno, progetto locale
```

## Stato di verifica delle schede

| Scheda | last-verified | Stato |
|---|---|---|
| STACK.md | nessun commit | scritta il 2026-10-14 leggendo il codice, da ancorare al primo commit |
| design-and-security.md | nessun commit | scritta il 2026-10-14, da ancorare al primo commit |
| deployment.md | nessun commit | scritta il 2026-10-14, da ancorare al primo commit |
| dev-testing.md | nessun commit | scritta il 2026-10-14, da ancorare al primo commit |
| current-work.md | nessun commit | scritta il 2026-10-14, da ancorare al primo commit |
| roadmap.md | nessun commit | scritta il 2026-10-14, da ancorare al primo commit |

## Punto di ripresa

Struttura: pubblico in radice, materiale del caso in `caso/` (ADR-008).


Dopo il primo commit dell'utente: `sync-context` per ancorare le schede a quel commit, poi lettura delle immagini nuove che il proprietario manda, da `caso/media/_arrivo/` con `python tools/aggiorna.py ingest`. Dopo: script di esportazione anonimizzata dei documenti e dei dati in una cartella pubblica (per esempio `docs/`), README di portfolio che mostri il lavoro fatto, e pagina con grafico interattivo su GitHub Pages servita da quella cartella (punti 22-24 di `_notes/RESUME_PROMPT.md`, ADR-007).

---
generated-from-commit: nessuno
generated-from-branch: main
generated-date: 2026-10-14
covers-paths:
  - caso/consegna/**
  - caso/fascicolo/**
  - .gitignore
last-verified-commit: nessuno
---

# Riservatezza e integrità

Il progetto non ha superfici di attacco applicative: è locale e non espone servizi. I rischi sono di riservatezza e di integrità della prova.

Riservatezza. `caso/fascicolo/` contiene strategia e termini e non si consegna mai. Il repository è pubblico (ADR-007): tutto il materiale del caso è escluso da git, gli script leggono i dati identificativi da `_notes/dati-privati.json` con `tools/privato.py`, e `tools/Test-Anonymization.py` blocca il commit se un valore reale compare nel perimetro pubblico. Nei documenti a terzi che adottano la codifica dei luoghi, oggi `caso/consegna/AGGIORNAMENTO-2026-08.md`, gli indirizzi sono sostituiti da codici L01-L0n e il controllo 5 di `aggiorna.py` rifiuta i termini di `VIETATI`. Il lettore delle schermate non estrae mai il testo degli indirizzi dalla Home né da Past Routes.

Integrità della prova. I file di `caso/media/` sono gli originali del telefono, identici byte per byte e con i metadati, tutti marcati `prova`, e non si modificano. Il catalogo ne registra l'hash e il controllo 8 lo verifica su un campione a ogni rigenerazione. `caso/media/` è esclusa da git ed è l'unica copia: va salvata a parte.

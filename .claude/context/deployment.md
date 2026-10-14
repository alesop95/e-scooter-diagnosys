---
generated-from-commit: nessuno
generated-from-branch: main
generated-date: 2026-10-14
covers-paths:
  - caso/consegna/**
  - tools/genera-pdf.py
last-verified-commit: nessuno
---

# Rilascio

Non esiste un ambiente di esercizio. Il "rilascio" è la produzione dei PDF in `caso/consegna/` con `python tools/aggiorna.py` e il loro invio per posta al centro assistenza, annotato nel file di ripresa con la data.

## Modello di separazione

Un solo ambiente, locale, sulla macchina del proprietario: nessuna separazione fra test e produzione è necessaria perché nulla gira in esercizio. La separazione che conta è fra ciò che si consegna (`caso/consegna/`) e ciò che resta riservato (`caso/fascicolo/`, `_notes/`), descritta in `design-and-security.md`. Da rivalutare con la skill `separazione-ambienti` solo se il progetto acquistasse un servizio in esercizio.

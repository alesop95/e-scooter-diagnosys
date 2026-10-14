---
generated-from-commit: nessuno
generated-from-branch: main
generated-date: 2026-10-14
covers-paths:
  - tools/aggiorna.py
  - tools/leggi-schermate.py
last-verified-commit: nessuno
---

# Verifiche

Non ci sono test unitari. Le verifiche sono gli otto controlli di `python tools/aggiorna.py verifica`: segnaposto non risolti, percorsi citati esistenti, un PDF per pagina, PDF non più vecchi del loro HTML, PDF integri, luoghi codificati, stile, coerenza del catalogo dei media (file e righe corrispondenti, nessun doppione, hash di un campione).

Il lettore delle schermate si collauda confrontando la sua bozza con una finestra già trascritta: `python tools/leggi-schermate.py --da 2026-08-13 --a 2026-08-25 --nome collaudo-f4` e confronto campo per campo con `caso/data/finestra4-letture.jsonl`. Esito del 2026-10-14: 834 valori su 885 uguali (94 per cento), 20 diversi quasi tutti segnalati come dubbi, 31 non letti. Le due differenze non segnalate (S061, S069) sono tragitti che la trascrizione manuale ha preso da Past Routes invece che dalla Home.

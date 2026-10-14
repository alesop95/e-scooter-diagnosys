# Work-log

> Append-only, in ordine cronologico inverso. Ogni passo significativo lascia una voce con data, file toccati, motivo e commit di riferimento. Le voci anteriori al 2026-10-14 sono ricostruite dal file di ripresa: il progetto non aveva git.

## 2026-10-14 - Riordino sotto caso/, README pubblico

Commit: nessuno. File toccati: tutto il materiale del caso spostato sotto `caso/` (ADR-008), `tools/percorsi.py` nuovo, percorsi aggiornati in tutti gli script, `README.md` riscritto per il pubblico, vecchia mappa in `caso/LEGGIMI.md`. Esito: 1.327 file spostati con hash verificato prima e dopo, catalogo di 968 file coerente, documenti rigenerati identici, otto controlli verdi, prova di ingest su un file fittizio collocato nella cartella della sua data e poi rimosso. Incidente: un aggiornamento automatico di `_notes/RESUME_PROMPT.md` ha cancellato per errore le sezioni dallo stato del caso alle azioni 1-21, perché l'ancora di ricerca "| 22 |" corrispondeva anche alla riga della campagna Marzo-Aprile 2026; il file, privato e non versionato, è stato ricostruito dal testo originale e dalle modifiche successive, tutte presenti nella conversazione, e verificato sezione per sezione.

## 2026-10-14 - Repository pubblico e anonimizzazione

Commit: nessuno. File toccati: `.gitignore` (materiale del caso escluso), `tools/privato.py` nuovo, `tools/Test-Anonymization.py` e `.claude/rules/anonymization.md` dal template, `tools/genera-grafici.py`, `genera-reperti.py`, `genera-modulo.py`, `genera-appendici.py`, `build-serie-2025.py`, `build-serie-2026-agosto.py`, `aggiorna.py`, `unifica-media.py` (valori reali spostati nel layer privato), `CLAUDE.md`, `README.md`. Motivo: il repository è pubblico (ADR-007). Esito: `Test-Anonymization.py` pulito sul perimetro pubblico, documenti rigenerati identici, otto controlli verdi, email dei commit anonima.

## 2026-10-14 - Allineamento al template e git

Commit: nessuno, primo commit dell'utente. File toccati: `.claude/` (PROJECT-SYSTEM, regole, norme, skill, templates, memoria, schede), `CLAUDE.md`, `.gitignore`, `tools/verifica-ripresa.py`, `tools/chiudi-sessione.ps1`, `tools/misura-istruzioni.py`; il file di ripresa è passato da `RESUME_PROMPT.md` a `_notes/RESUME_PROMPT.md`. Motivo: ripresa con `/riprendi`. Git inizializzato su `main` con identità locale alesop95 e remoto privato da creare su GitHub.

## 2026-10-14 - Unificazione dei media, J: svuotato, lettore delle schermate

Commit: nessuno. File toccati: `caso/media/` (968 file, catalogo), `tools/catalogo.py`, `tools/unifica-media.py`, `tools/leggi-schermate.py`, `tools/aggiorna.py` (ingest nuovo, controllo 8), `tools/genera-reperti.py`, `tools/genera-grafici.py`, `README.md`, `caso/consegna/AGGIORNAMENTO-2026-08.md` (tre rimandi alla vecchia cartella dei reperti sostituiti con il PDF dei reperti). Tolti `ingest-manifest.py`, `ingest-immagini.py`, `stato-ingestione.py`. Motivo: richiesta del proprietario di una cartella unica, dell'assorbimento di J: senza ridondanza e di una lettura economica delle schermate. Esito: 1.099 file di J: verificati e cancellati, rapporto in `caso/lavorazione/unificazione-rapporto.csv`, `aggiorna.py` con otto controlli verdi.

## 2026-08-28 - Lacuna esaminata, campagne esaurite

Commit: nessuno. Video del 21/11/2025, richiamo statunitense e note sui codici recuperati; 349 immagini 2025 filtrate senza esito.

## 2026-08-27 - Integrazione sulla lacuna

Commit: nessuno. Prodotta `caso/consegna/INTEGRAZIONE-2026-08-27.md`: Hall sensor fault del 13/11/2025, codici 12 e 123, perdita di lettura del 13/03/2026.

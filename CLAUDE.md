# e-scooter-diagnosys

> Istruzioni di team, versionate. Questo file è l'indice del progetto: indicizza i soli file satellite tracciati e descrive la procedura di ripresa. Le preferenze personali vivono in `CLAUDE.local.md`, ignorato da git, non qui.

## Cos'è questo progetto

Fascicolo tecnico e documentale sul difetto di gestione delle batterie estraibili di uno scooter elettrico NIU MQi GT, aperto nel luglio 2025: rilevazioni dall'app del costruttore, documenti consegnabili al centro assistenza, fascicolo legale riservato e gli script che li rigenerano. Il codice e il sistema di progetto stanno in radice e sono pubblici; tutto il materiale del caso sta in `caso/`, escluso da git, e la sua mappa è `caso/LEGGIMI.md`. I percorsi si prendono da `tools/percorsi.py`.

## Procedura di ripresa in una sessione nuova

Lo stato del progetto è interamente recuperabile su disco. Si comincia con una verifica e non con una lettura: la skill `riprendi` esegue `tools/verifica-ripresa.py`, che confronta l'impronta registrata alla chiusura precedente con lo stato reale di git e dice che cosa una sessione caduta a metà non ha scritto. Solo dopo si legge `.claude/memory/index.md`, che dà branch, commit di riferimento, stato di verifica di ogni scheda e punto di ripresa, poi `.claude/context/current-work.md` per il lavoro attivo. Si invoca `sync-context` per il drift fra schede e codice e si leggono solo le schede pertinenti. Il work-log `.claude/memory/progress.md` e il registro `.claude/memory/decisions.md` danno storia e decisioni quando servono. Lo stato di dettaglio del fascicolo, cioè che cosa è accertato, che cosa è stato inviato e le azioni aperte, è in `_notes/RESUME_PROMPT.md`, privato e ignorato, che va aggiornato alla fine di ogni sessione. Nello stesso momento l'agente scrive in `_notes/COMMIT-MSG.txt` il messaggio di commit proposto, una riga di al massimo 72 caratteri, e la chiusura la esegue l'utente con `tools/chiudi-sessione.ps1` dopo aver chiuso la sessione.

## Indice dei file satellite tracciati

Memoria e meta-stato, sotto `.claude/memory/`, letti sempre a inizio sessione.

```
.claude/memory/index.md       snapshot e tabella di sincronizzazione, da leggere per primo
.claude/memory/progress.md    work-log append-only di passi e riconciliazioni
.claude/memory/decisions.md   registro ADR-lite delle decisioni
```

Schede tecniche, sotto `.claude/context/`, con frontmatter di riconciliazione.

```
.claude/context/STACK.md                script, flussi di dati, ruolo dei file
.claude/context/design-and-security.md  riservatezza: luoghi codificati, consegna contro fascicolo, media fuori da git
.claude/context/deployment.md           nessun ambiente di esercizio: progetto locale, uscite in consegna/
.claude/context/dev-testing.md          controlli di aggiorna.py e collaudo del lettore delle schermate
.claude/context/current-work.md         lavoro attivo, definition of done, domande aperte
.claude/context/roadmap.md              direzione e priorità
```

Regole sempre attive sotto `.claude/rules/`, skill richiamabili sotto `.claude/skills/`. Una norma che vale solo in certe situazioni vive come `RIFERIMENTO.md` dentro la propria skill, e l'indice qui sotto dice quando invocarla. Lo strumento `tools/misura-istruzioni.py` misura il carico degli instruction file. Lo standard di sistema completo è in `.claude/PROJECT-SYSTEM.md`.

Norme caricate su richiesta, una riga per situazione.

- Si scrive o si valuta una prova automatica, si chiude un difetto, si sta per dichiarare completo un intervento il cui scopo era un effetto misurabile: skill `prove-che-misurano`.
- Un recupero web fallisce con 403 o con una pagina anti-bot, la fonte sta su Reddit o su Discord, si sta per annotare una fonte non letta: skill `fonti-non-recuperabili`.
- `git worktree list` mostra più di un albero, se ne crea o se ne rimuove uno: skill `alberi-di-lavoro`.
- Cambia il modo in cui si prova e si rilascia, e va deciso come separare test e produzione: skill `separazione-ambienti`.
- Si imposta o si verifica user.name e user.email, si collega o si cambia il remoto o l'alias SSH, un push fallisce per permessi: skill `identita-git`.

## Apprendimenti recenti

```
- [2026-10-14] Le schermate del S25 Ultra (1440x3120) si leggono in locale con tools/leggi-schermate.py; il rilevatore dell'OCR perde le cifre isolate, il riconoscitore su riquadro fisso no.
- [2026-10-14] media/ contiene gli unici originali (J: svuotato) ed è esclusa da git: serve una copia a parte.
```

## Vincoli di team

Le operazioni di `git add`, commit e push restano sempre manuali dell'utente: l'agente prepara i file, non committa. L'identità git è impostata a livello locale del repo secondo la skill `identita-git`: alesop95 con l'email anonima di GitHub, remoto `git@github-personal:alesop95/e-scooter-diagnosys.git`. Il repository è PUBBLICO, perché è un progetto di portfolio: i materiali nominativi del caso (`caso/media/`, `caso/consegna/`, `caso/fascicolo/`, `caso/fonti/`, `caso/data/`, `caso/lavorazione/`) sono esclusi da git, i dati identificativi che servono agli script stanno in `_notes/dati-privati.json` e si leggono con `tools/privato.py`, e prima di ogni commit `python tools/Test-Anonymization.py` deve uscire pulito; lo esegue da solo `tools/chiudi-sessione.ps1`. Nessun valore reale (nomi, telaio, targa, numeri di serie, venditore, centro assistenza, luoghi) entra mai in un file tracciato, secondo `.claude/rules/anonymization.md`. Lo stile di documentazione e di interazione è quello di `.claude/rules/interaction-style.md`. I media in `caso/media/` sono originali del telefono, tutti marcati come prova, e non si comprimono né si modificano. Le citazioni normative si verificano sul corpus locale del progetto `legal-consultant`, mai a memoria. Claude aggiorna i file di memoria e di contesto in automatico a ogni giro di lavoro sostanziale, secondo `.claude/rules/chat-non-e-memoria.md`.

# Registro delle decisioni

> Convenzione ADR-lite, append-only. Ogni decisione non ovvia entra come voce numerata con data, stato, contesto, decisione, motivazione e conseguenze. Una decisione non si cancella: quando viene superata si aggiunge una voce nuova che cita la precedente. Le voci da ADR-002 a ADR-004 sono ricostruite da `README.md` e dal file di ripresa, perché il progetto non aveva storia git.

## ADR-001 - Adozione del sistema di progetto portabile

Data: 2026-10-14 Stato: accettata Contesto: il progetto non aveva memoria versionata né git, e la ripresa dipendeva da un solo file di ripresa. Decisione: allineare il progetto a `E:\template-claude-developing` con `.claude/PROJECT-SYSTEM.md`, regole, skill del motore e `riprendi`, memoria e schede. Motivazione: stato recuperabile da disco e ripresa verificata con `/riprendi`. Conseguenze: commit e push manuali dell'utente; il gate dei pacchetti opzionali e l'MCP sono rimandati (MCP rifiutato, pacchetti da valutare in una sessione dedicata).

## ADR-002 - Separazione fra consegna e fascicolo

Data: 2026-08 (ricostruita) Stato: accettata Contesto: il progetto produce sia documenti per il centro assistenza sia la strategia verso venditore e importatore. Decisione: `caso/consegna/` contiene solo ciò che si può mandare a terzi, `caso/fascicolo/` la strategia, i termini e le bozze di contestazione, e non si consegna mai. Motivazione: non esporre la strategia alla controparte. Conseguenze: quando si allega materiale si attinge da `caso/consegna/` e da nient'altro.

## ADR-003 - Documenti rigenerati da sorgente unica

Data: 2026-08 (ricostruita) Stato: accettata Contesto: rischio di numeri copiati a mano e di versioni divergenti dello stesso documento. Decisione: il Markdown è la sorgente, HTML e PDF si rigenerano con `python tools/aggiorna.py`, le tabelle dati si generano dagli script, e un documento già consegnato si integra con un addendum invece di riscriverlo. Motivazione: i numeri pubblicati coincidono con i dati estratti e resta stabilito che cosa era noto alla data di consegna. Conseguenze: otto controlli automatici in coda a ogni rigenerazione.

## ADR-004 - Luoghi codificati nei documenti a terzi

Data: 2026-08 (ricostruita) Stato: accettata Contesto: le schermate dell'app mostrano indirizzi. Decisione: nell'aggiornamento della finestra 4 i luoghi sono codici L01-L0n, e `aggiorna.py` rifiuta i termini della lista `VIETATI`. Conseguenze: il lettore delle schermate non estrae mai il testo degli indirizzi.

## ADR-005 - Un'unica cartella di media originali, fuori da git

Data: 2026-10-14 Stato: accettata Contesto: le immagini stavano in otto cartelle del progetto e sul disco esterno J:, con 293 copie doppie. Decisione: tutti i media in `caso/media/`, piatta, una copia per contenuto, con catalogo `caso/media/CATALOGO.csv`; originali byte per byte con i metadati del telefono, nessuna compressione, tutti marcati come prova; J: svuotato dopo verifica per hash; `caso/media/` esclusa da git, versionato il solo catalogo. Motivazione: gli originali e i loro metadati (istante di scatto) sono materiale di prova; 1,7 GB non stanno in un repository. Conseguenze: `caso/media/` è l'unica copia e va salvata a parte. Una compressione AVIF era stata implementata e collaudata (12,5 MB ridotti a 1,0 MB su una giornata) ed è stata ritirata nella stessa sessione su decisione del proprietario.

## ADR-006 - Lettura locale delle schermate del S25 Ultra

Data: 2026-10-14 Stato: accettata Contesto: leggere a vista le schermate costa circa 1.500 token l'una (stima) e la trascrizione è il passo più lento. Decisione: `tools/leggi-schermate.py` legge in locale con `rapidocr_onnxruntime` le schermate 1440x3120: classifica il tipo dal titolo, cerca l'etichetta e il valore sulla stessa riga, rilegge con il solo riconoscitore il riquadro fisso quando il rilevatore perde il valore, e produce una bozza più un foglio dei soli ritagli dubbi. Motivazione: collaudo sulla finestra 4, 94 per cento di 885 valori uguali alla trascrizione manuale, differenze quasi tutte segnalate. Conseguenze: la trascrizione in `caso/data/` resta il passo di giudizio; la bozza la prepara.

## ADR-007 - Repository pubblico di portfolio, materiale del caso fuori da git

Data: 2026-10-14 Stato: accettata Contesto: il proprietario vuole il repository pubblico, perché il lavoro di impostazione e conduzione del progetto deve essere visibile nel portfolio, e vuole che sia anonimizzato completamente prima del primo push. Decisione: restano fuori da git `caso/media/`, `caso/consegna/`, `caso/fascicolo/`, `caso/fonti/`, `caso/data/` e `caso/lavorazione/`; gli script non contengono più valori reali, che stanno in `_notes/dati-privati.json` e si leggono con `tools/privato.py` (in assenza del file diventano segnaposti); è installato il pacchetto `anonymization` del template, con `tools/Test-Anonymization.py`, la regola `.claude/rules/anonymization.md` e i valori da cercare in `_notes/.anonymization-patterns.json`; l'email dei commit è quella anonima di GitHub. Motivazione: nessun dato del caso nel perimetro pubblico, e il fascicolo legale non va mai esposto alla controparte. Conseguenze: i documenti e i dati del progetto si mostrano solo come versioni anonimizzate generate da uno script, da costruire, che saranno anche la base della pagina con il grafico interattivo su GitHub Pages; `aggiorna.py` e gli script producono gli stessi documenti di prima, verificato byte per byte.

Precisazione del proprietario, stesso giorno: gli unici dati reali che possono essere pubblici sono quelli del veicolo, cioè le rilevazioni (percentuali dei pacchi, temperature, cicli, chilometri, consumi, tragitti senza luoghi) e le analisi statistiche che ne derivano, destinate alla pagina su GitHub Pages. Restano privati tutti gli identificativi: persone, telaio e targa (riconducono all'intestatario), venditore, centro assistenza, luoghi; i numeri di serie dei pacchi si pubblicano abbreviati come nei documenti (...439, ...168, ...135). Da confermare con il proprietario se telaio e targa rientrino o no fra i "dati del motorino": in assenza di conferma restano privati.

## ADR-008 - Riordino: pubblico in radice, caso in caso/, media per data

Data: 2026-10-14 Stato: accettata Contesto: il proprietario voleva una struttura più pulita e le foto ordinate come sul disco d'origine, con l'integrità verificata a ogni spostamento. Decisione: in radice solo ciò che è pubblico (`README.md`, `CLAUDE.md`, `.claude/`, `tools/`, in seguito `docs/` per il sito); tutto il materiale del caso sotto `caso/` (`media/`, `data/`, `consegna/`, `fascicolo/`, `fonti/`, `lavorazione/`), escluso da git con una riga; foto in `caso/media/AAAA/AAAA-MM-GG/`, reperti in `caso/media/reperti/`, documenti e rese in `caso/media/documenti/`; percorsi centralizzati in `tools/percorsi.py`. Il nome `data/` resta invece di `dati/` perché cinque documenti già consegnati citano percorsi `data/...`. Motivazione: un confine pubblico/privato leggibile a colpo d'occhio, e le foto nuove si collocano da sole per data. Conseguenze: 1.327 file spostati con hash verificato prima e dopo, registro in `caso/lavorazione/riordino-2026-10-14.csv`; documenti rigenerati identici; il README pubblico presenta il progetto e la vecchia mappa interna è `caso/LEGGIMI.md`.

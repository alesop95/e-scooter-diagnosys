# e-scooter-diagnosys

Diagnosi di un difetto in garanzia sulle due batterie estraibili di uno scooter elettrico NIU MQi GT, condotta da utente finale con i soli strumenti a disposizione di un utente: l'app del costruttore, il cruscotto, un telefono. Il progetto raccoglie tredici mesi di osservazioni, le trasforma in serie di dati confrontabili e ne ricava la documentazione tecnica consegnata al centro assistenza.

## Il problema

Da giugno 2025 lo scooter mostra tre sintomi che si sovrappongono: i due pacchi batteria si scaricano in modo disuguale, l'app perde a intermittenza la lettura di uno dei due, e a mezzo fermo la carica cala più di quanto dovrebbe. La prima ipotesi era un singolo pacco difettoso. La domanda era se il difetto stesse in un pacco o nel veicolo.

## Il metodo

Le osservazioni sono organizzate in quattro finestre, cioè periodi continuativi di rilevazione fra luglio 2025 e agosto 2026: 81 tragitti per 467 km nella prima, poi 51, 22 e 57 rilevazioni dell'app, più 24 tragitti. Ogni rilevazione registra percentuale, temperatura e cicli di ciascun pacco, chilometri, autonomia e consumo, e ogni ragionamento si conduce sul numero di serie del pacco e non sull'etichetta A o B dell'app, perché la corrispondenza fra alloggiamento e pacco è cambiata due volte nel periodo.

La quarta finestra è un esperimento naturale: il pacco sospetto è stato tolto e sostituito con un pacco del centro assistenza, che non ha storia su questo veicolo. Se il difetto fosse stato nel pacco, i sintomi sarebbero spariti con lui.

Ogni ipotesi resta marcata come tale finché un dato non la conferma, e una è stata ritirata: un valore anomalo del cruscotto, letto in un primo momento come guasto di comunicazione, si è rivelato il normale transitorio di accensione quando è stata esaminata la sequenza completa del filmato.

## Che cosa dicono i dati

| Aspetto | Risultato |
|---|---|
| Consumo in marcia | stabile su quattro finestre e tredici mesi, fra 0,99 e 1,13 punti percentuali al km: nessun degrado di capacità |
| Autonomia a carica piena | 91-92 km, invariata |
| Squilibrio fra i pacchi | era proprio del pacco sospetto ed è sparito con lui |
| Perdite di lettura | sette episodi in dodici giorni dopo la sostituzione, che colpiscono anche il pacco del centro assistenza |
| Campi che si azzerano insieme | percentuale, temperatura e cicli cadono a zero contemporaneamente: firma di un problema di comunicazione, non delle celle |
| Calo a mezzo fermo | le soste con perdita di almeno tre punti hanno tutte un'anomalia di lettura entro quattro ore, quelle lunghe e stabili nessuna |
| Codice 165 | esposto dal cruscotto con due pacchi rilevati e carichi al 99 per cento, e assente dall'elenco dei codici del manuale |

La conclusione che ne discende, e che la documentazione chiede al centro assistenza di verificare con lo strumento diagnostico ufficiale, è che il difetto principale non sta nei pacchi ma nel veicolo.

## Gli strumenti

La parte ripetitiva del lavoro è automatizzata da script Python locali, in `tools/`. `leggi-schermate.py` legge le schermate dell'app con un OCR locale: sfrutta il fatto che il telefono cattura sempre a 1440x3120 e che l'app mette ogni dato nella stessa fascia di pixel, così che a una persona resta da guardare un foglio con i soli valori incerti invece di ogni schermata. Collaudato sulla quarta finestra, riproduce la trascrizione manuale nel 94 per cento degli 885 valori, e segnala come incerti quasi tutti quelli che sbaglia. `catalogo.py` tiene l'inventario delle foto e dei filmati con l'hash di ciascun file, il telefono e l'istante di scatto. `aggiorna.py` rigenera grafici, tabelle e documenti a partire dai dati e chiude con otto controlli di coerenza, così che nessun numero pubblicato sia copiato a mano.

## Riservatezza

Il repository pubblica il metodo e il codice. Foto originali, documenti consegnati, corrispondenza e dati personali restano fuori: gli script li leggono da una cartella locale esclusa da git, e un controllo automatico blocca ogni commit che contenga un dato identificativo.

## Stato

Il caso è aperto. Il prossimo passo pubblico è una pagina su GitHub Pages con i grafici interattivi delle rilevazioni e le analisi statistiche, generata dagli stessi dati senza le informazioni identificative.

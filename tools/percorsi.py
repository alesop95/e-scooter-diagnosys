#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Percorsi del progetto, in un posto solo.

Il repository e' pubblico. In radice stanno soltanto il codice, il sistema di progetto e il sito;
tutto il materiale del caso sta sotto `caso/`, che git ignora per intero. Gli script prendono i
percorsi da qui, cosi' che la divisione fra pubblico e privato sia scritta una volta sola.
"""

import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
CASO = BASE / "caso"

MEDIA = CASO / "media"              # originali del telefono, per data di scatto, con CATALOGO.csv
DATI = CASO / "data"                # rilevazioni trascritte, una finestra per periodo
CONSEGNA = CASO / "consegna"        # documenti per il centro assistenza
FASCICOLO = CASO / "fascicolo"      # strategia legale, mai consegnata
FONTI = CASO / "fonti"              # manuali, chat, note, documenti originali
LAVORAZIONE = CASO / "lavorazione"  # intermedi, bozze di lettura, rapporti

NOTE = BASE / "_notes"              # layer privato del sistema di progetto

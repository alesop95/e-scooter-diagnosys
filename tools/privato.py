#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dati identificativi del caso, tenuti fuori dal repository pubblico.

Telaio, targa, intestatario, venditore, centro assistenza e luoghi servono ai documenti nominativi
di `consegna/` e `fascicolo/`, che sono privati, ma non possono stare negli script, che sono
pubblici. Vivono in `_notes/dati-privati.json`, ignorato da git; gli script li chiedono qui. Se il
file manca, per esempio in un clone del repository pubblico, ogni dato diventa un segnaposto
leggibile e gli script continuano a funzionare.
"""

import json
import pathlib

FILE = pathlib.Path(__file__).resolve().parent.parent / "_notes" / "dati-privati.json"


def _dati():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def dato(chiave):
    """Il valore privato, o il segnaposto `[chiave]`."""
    return _dati().get(chiave) or "[%s]" % chiave


def elenco(chiave):
    v = _dati().get(chiave)
    return v if isinstance(v, list) else []


def presente():
    return FILE.exists()

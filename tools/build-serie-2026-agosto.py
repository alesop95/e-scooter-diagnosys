#!/usr/bin/env python3
"""Costruisce i dati della finestra 4 (13-25/08/2026) a partire dalla trascrizione degli screenshot.

La trascrizione riga per riga vive in `data/serie-2026-agosto.jsonl`, che e' la fonte di questa
finestra allo stesso titolo in cui `_traccia_batterie.xlsx` lo era per la finestra 1. Da qui si
generano le due tabelle in formato CSV usate dal report e dalle appendici, con la stessa
convenzione di intestazione delle finestre precedenti: le colonne dei pacchi portano nel nome il
numero di serie effettivamente montato in quello slot, cosi' che una futura rotazione non possa
piu' rendere ambigua la serie.

La mappatura fra slot e numero di serie in questa finestra e' dimostrata dal conteggio cicli, con
lo stesso criterio del paragrafo 2.1 del report: la scheda B prosegue da 101 cicli del 03/08/2026
a 102 il 14/08 e 104 il 25/08, e identifica quindi la ...168; la scheda A parte da 132
cicli, valore incompatibile con qualunque pacco gia' presente sul veicolo, e identifica la
...135 registrata dall'app come primo utilizzo il 14/08/2026 alle 10:08.
"""

import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import privato  # noqa: E402
import percorsi as P  # noqa: E402  numeri di serie dei pacchi, dal layer privato

BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = P.DATI / "serie-2026-agosto.jsonl"
SLOT_A = "" + privato.dato("pacco_135") + ""
SLOT_B = "" + privato.dato("pacco_168") + ""


def num(v):
    """Formatta un numero per la cella CSV, con la virgola decimale delle altre serie."""
    if v is None:
        return ""
    if isinstance(v, float) and v != int(v):
        return f"{v:.1f}".replace(".", ",")
    return str(int(v))


def carica():
    righe = [json.loads(l) for l in SRC.open(encoding="utf-8") if l.strip()]
    righe.sort(key=lambda r: r["ts"])
    return righe


def scrivi_serie(righe):
    out = P.DATI / "serie-screenshot-2026-agosto.csv"
    testa = ["data", "ora", f"A_pct_{SLOT_A}", f"B_pct_{SLOT_B}", "diff_A_meno_B",
             "temp_A_C", "temp_B_C", "cicli_A", "cicli_B", "odo_km", "spare_pct",
             "usato_pct", "range_km", "ride_km", "ride_time", "sessione", "note"]
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(testa)
        for r in righe:
            a, b = r["a_pct"], r["b_pct"]
            diff = a - b if (a is not None and b is not None) else None
            w.writerow([r["ts"][:10], r["ts"][11:], num(a), num(b), num(diff),
                        num(r["temp_a_c"]), num(r["temp_b_c"]), num(r["cicli_a"]), num(r["cicli_b"]),
                        num(r["km_totali"]), num(r["spare_pct"]), num(r["uso_30gg_pct"]),
                        num(r["autonomia_km"]), num(r["ultimo_tragitto_km"]),
                        r["ultimo_tragitto_durata"] or "", r["sessione"], r["note"]])
    return out, len(righe)


def scrivi_tragitti(righe):
    out = P.DATI / "tragitti-2026-agosto.csv"
    testa = ["data", "ora_inizio", "ora_fine", "da", "a", "km", "durata",
             "consumo_pct", "pct_per_km", "vel_media_kmh", "sessione"]
    n = 0
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(testa)
        for r in righe:
            t = r.get("tragitto")
            if not t:
                continue
            n += 1
            ppk = t["cons_pct"] / t["km"] if (t.get("cons_pct") and t.get("km")) else None
            w.writerow([r["ts"][:10], t["ora_inizio"], t["ora_fine"], t["da"], t["a"],
                        num(t["km"]), t["durata"], num(t["cons_pct"]),
                        f"{ppk:.2f}".replace(".", ",") if ppk else "",
                        num(t.get("vel_media_kmh")), r["sessione"]])
    return out, n


if __name__ == "__main__":
    righe = carica()
    for percorso, quante in (scrivi_serie(righe), scrivi_tragitti(righe)):
        print(f"{percorso.relative_to(BASE)}: {quante} righe")

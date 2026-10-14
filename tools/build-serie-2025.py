#!/usr/bin/env python3
"""Normalizza le trascrizioni degli screenshot in una serie temporale.

Ingresso: `_lavorazione/trascrizioni-screenshot.txt`, una riga per screenshot nel
formato pipe prodotto dai lettori. Uscita: `data/serie-screenshot-2025.csv`,
una riga per rilevazione, con le due batterie affiancate.

Gli screenshot sono catturati in terzine ravvicinate: prima la schermata
Veicolo, poi la scheda della batteria A, poi quella della batteria B. La
scheda selezionata non e' sempre riconoscibile con certezza dall'immagine,
quindi l'assegnazione A/B si ricava dall'ordine di cattura dentro il gruppo,
che e' stabile in tutte le terzine osservate. I valori di temperatura e cicli
appartengono alla scheda selezionata; la coppia di percentuali e' invece
leggibile su entrambe le schede e serve da controllo incrociato.
"""

import csv
import pathlib
import sys
import re
from datetime import datetime

import argparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import privato  # noqa: E402
import percorsi as P  # noqa: E402  numeri di serie dei pacchi, dal layer privato

DEFAULT_SRC = str(P.LAVORAZIONE / "trascrizioni-screenshot.txt")
DEFAULT_OUT = str(P.DATI / "serie-screenshot-2025.csv")
GROUP_GAP_S = 180  # secondi entro cui due scatti appartengono alla stessa rilevazione

FIELDS = [
    "filename", "screen", "tab", "a_pct", "b_pct", "temp_c",
    "cycles", "odo_km", "spare_pct", "usato_pct", "range_km",
    "ride_km", "ride_time",
]


def num(v):
    v = (v or "").strip()
    if v in ("", "-", "?"):
        return None
    v = v.replace(",", ".")
    m = re.match(r"^-?\d+(\.\d+)?$", v)
    return float(v) if m else None


def stamp(name):
    m = re.search(r"(\d{8})_(\d{6})", name)
    return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S") if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--label-a", default="A_pct_" + privato.dato("pacco_168") + "")
    ap.add_argument("--label-b", default="B_pct_" + privato.dato("pacco_439") + "")
    args = ap.parse_args()
    SRC = pathlib.Path(args.src)
    OUT = pathlib.Path(args.out)

    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        parts += [""] * (len(FIELDS) - len(parts))
        r = dict(zip(FIELDS, parts[: len(FIELDS)]))
        r["extra"] = " ".join(parts[len(FIELDS):]).strip()
        r["ts"] = stamp(r["filename"])
        if r["ts"]:
            rows.append(r)
    rows.sort(key=lambda r: r["ts"])

    groups, cur = [], []
    for r in rows:
        if cur and (r["ts"] - cur[-1]["ts"]).total_seconds() > GROUP_GAP_S:
            groups.append(cur)
            cur = []
        cur.append(r)
    if cur:
        groups.append(cur)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow([
            "data", "ora", args.label_a, args.label_b,
            "diff_A_meno_B", "temp_A_C", "temp_B_C", "cicli_A", "cicli_B",
            "odo_km", "spare_pct", "usato_pct", "range_km", "ride_km",
            "ride_time", "n_scatti", "note",
        ])
        for g in groups:
            bat = [r for r in g[:] if r["screen"] == "batteria"]
            veh = next((r for r in g if r["screen"] == "veicolo"), None)
            altro = [r["extra"] for r in g if r["screen"] == "altro" and r["extra"]]

            a = bat[0] if len(bat) >= 1 else None
            b = bat[1] if len(bat) >= 2 else None

            a_pct = num(a["a_pct"]) if a else (num(b["a_pct"]) if b else None)
            b_pct = num(a["b_pct"]) if a else (num(b["b_pct"]) if b else None)
            diff = (a_pct - b_pct) if (a_pct is not None and b_pct is not None) else None

            note = []
            if altro:
                note.extend(altro)
            if a and b:
                if num(a["a_pct"]) != num(b["a_pct"]) or num(a["b_pct"]) != num(b["b_pct"]):
                    note.append("percentuali discordanti fra le due schede")
            if len(bat) < 2:
                note.append(f"solo {len(bat)} scheda batteria nel gruppo")
            if b_pct == 0 and a_pct not in (None, 0):
                note.append("BATTERIA B A ZERO - possibile disconnessione")
            if a_pct == 0 and b_pct not in (None, 0):
                note.append("BATTERIA A A ZERO - possibile disconnessione")

            ts = g[0]["ts"]
            w.writerow([
                ts.strftime("%Y-%m-%d"), ts.strftime("%H:%M:%S"),
                a_pct, b_pct, diff,
                num(a["temp_c"]) if a else None,
                num(b["temp_c"]) if b else None,
                num(a["cycles"]) if a else None,
                num(b["cycles"]) if b else None,
                num(a["odo_km"]) if a else (num(veh["odo_km"]) if veh else None),
                num(a["spare_pct"]) if a else None,
                num(a["usato_pct"]) if a else None,
                num(veh["range_km"]) if veh else None,
                num(veh["ride_km"]) if veh else None,
                veh["ride_time"] if veh and veh["ride_time"] not in ("-", "") else None,
                len(g),
                "; ".join(note),
            ])

    print(f"righe sorgente: {len(rows)}")
    print(f"rilevazioni:    {len(groups)}")
    print(f"output:         {OUT}")


if __name__ == "__main__":
    main()

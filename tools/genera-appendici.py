#!/usr/bin/env python3
"""Genera le appendici dati del report a partire dai CSV.

Le tabelle del report non si scrivono a mano: si rigenerano da qui, cosi' che
i numeri pubblicati coincidano sempre con i dati estratti e una correzione a
monte si propaghi senza reintrodurre errori di trascrizione.
"""

import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import privato  # noqa: E402
import percorsi as P  # noqa: E402  numeri di serie dei pacchi, dal layer privato

OUT = P.LAVORAZIONE / "appendici.md"


def f(v, dec=0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    return f"{x:.{dec}f}".replace(".", ",") if dec else f"{x:.0f}"


def cell(v, limit=None):
    """Normalizza un valore per una cella di tabella Markdown.

    Le note del foglio elettronico contengono a capo e barre verticali, che
    spezzerebbero la riga della tabella: qui vengono neutralizzati.
    """
    s = " ".join((v or "").split())
    s = s.replace("|", "/")
    return s[:limit] if limit else s


def pct(v):
    try:
        return f"{float(v) * 100:.0f}"
    except (TypeError, ValueError):
        return ""


def serie(path, col_a, col_b, eti_a, eti_b):
    rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter=";"))
    out = [
        f"| # | Data | Ora | {eti_a} | {eti_b} | Scarto | T {eti_a} | T {eti_b} "
        f"| Cicli {eti_a} | Cicli {eti_b} | km | Contesto | Riserva ECU | Usato "
        f"| Autonomia | Tragitto | Tempo | Scatti | Note |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    prev_km = None
    for i, r in enumerate(rows, 1):
        km = r["odo_km"]
        ctx = ""
        if prev_km and km:
            try:
                d = float(km) - float(prev_km)
                ctx = f"+{d:.0f} km" if d > 0 else "fermo"
            except ValueError:
                ctx = ""
        if km:
            prev_km = km
        note = cell(r["note"])
        out.append(
            f"| {i} | {r['data']} | {r['ora'][:5]} | {f(r[col_a])} | {f(r[col_b])} "
            f"| {f(r['diff_A_meno_B'])} | {f(r['temp_A_C'])} | {f(r['temp_B_C'])} "
            f"| {f(r['cicli_A'])} | {f(r['cicli_B'])} | {f(km)} | {ctx} "
            f"| {f(r['spare_pct'])} | {f(r['usato_pct'])} | {f(r['range_km'])} "
            f"| {f(r['ride_km'], 1)} | {cell(r['ride_time'])} | {f(r['n_scatti'])} "
            f"| {note} |"
        )
    return "\n".join(out)


def traccia(path):
    rows = list(csv.reader(open(path, encoding="utf-8"), delimiter=";"))[1:]
    out = [
        "| # | Data | Ora | Riserva ECU | ...168 (Slot 2, A) | T | Cicli "
        "| ...439 (Slot 1, B) | T | Cicli | Scarto | km | Tempo | Media | Note |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    n = 0
    for r in rows:
        r = r + [""] * (22 - len(r))
        data = (r[1] or "")[:10]
        if not data:
            continue
        n += 1
        out.append(
            f"| {n} | {data} | {(r[2] or '')[:5]} | {pct(r[3])} | {pct(r[4])} "
            f"| {f(r[5])} | {f(r[6])} | {pct(r[7])} | {f(r[8])} | {f(r[9])} "
            f"| {pct(r[10])} | {f(r[18], 1)} | {r[19] or ''} | {f(r[20], 1)} "
            f"| {cell(r[21], 90)} |"
        )
    return "\n".join(out)


def cicli(path_25, path_26):
    out = [
        "| Finestra | Data | Cicli scheda A | Cicli scheda B | Segno |",
        "|---|---|---|---|---|",
    ]
    for label, path in (("2", path_25), ("3", path_26)):
        rows = [
            r for r in csv.DictReader(open(path, encoding="utf-8"), delimiter=";")
            if r["cicli_A"] and r["cicli_B"] and float(r["cicli_B"]) > 0
        ]
        for r in (rows[0], rows[-1]):
            a, b = float(r["cicli_A"]), float(r["cicli_B"])
            seg = "A maggiore" if a > b else ("A minore" if a < b else "pari")
            out.append(f"| {label} | {r['data']} | {a:.0f} | {b:.0f} | {seg} |")
    return "\n".join(out)


def main():
    parts = [
        "## Appendice A - Serie completa della finestra 2 (16/08 - 11/09/2025)\n",
        "Ricostruita dalle 158 immagini dell'app. La colonna Scarto e' la "
        "differenza fra le due percentuali; valori negativi indicano la "
        "" + privato.dato("pacco_168") + " piu' bassa.\n",
        serie(
            str(P.DATI / "finestra2-letture.csv"),
            "A_pct_" + privato.dato("pacco_168") + "", "B_pct_" + privato.dato("pacco_439") + "",
            "...168", "...439",
        ),
        "\n## Appendice B - Serie completa della finestra 3 (30/07 - 03/08/2026)\n",
        "Ricostruita dai 100 screenshot del 2026. Valori negativi dello scarto "
        "indicano la " + privato.dato("pacco_439") + " piu' bassa.\n",
        serie(
            str(P.DATI / "finestra3-letture.csv"),
            "A_pct_" + privato.dato("pacco_439") + "", "B_pct_" + privato.dato("pacco_168") + "",
            "...439", "...168",
        ),
        "\n## Appendice C - Registro della finestra 1 (24/07 - 16/08/2025)\n",
        "Esportato dal foglio `Dati` di `_traccia_batterie.xlsx`, con le "
        "percentuali convertite da frazione a punti percentuali.\n",
        traccia(str(P.DATI / "finestra1-traccia.csv")),
        "\n## Appendice D - Prova dello scambio di posizione\n",
        cicli(str(P.DATI / "finestra2-letture.csv"), str(P.DATI / "finestra3-letture.csv")),
    ]
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"scritto {OUT}, {len(OUT.read_text(encoding='utf-8').splitlines())} righe")


if __name__ == "__main__":
    main()

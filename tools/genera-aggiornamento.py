#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compone l'unico documento della finestra 4: prosa, grafici, reperti e tabelle in una pagina.

Il documento della finestra esiste in una sola forma. Il testo sta in
`consegna/AGGIORNAMENTO-2026-08.md` e contiene segnaposto della forma `[[nome]]`; i grafici, i
reperti e le tabelle stanno in `_lavorazione/frammenti-finestra4.json`, prodotto da
`tools/genera-grafici.py` a partire dai dati in `data/`. Questo script converte il Markdown con
`tools/md-to-html.py`, innesta i frammenti al posto dei segnaposto e aggiunge il foglio di stile
necessario a grafici e figure.

Rigenerazione completa della finestra:

    python tools/genera-grafici.py
    python tools/genera-aggiornamento.py

Il PDF si ottiene stampando l'HTML dal browser, come per gli altri documenti del progetto.
"""

import io
import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import percorsi as P  # noqa: E402
MD = P.CONSEGNA / "AGGIORNAMENTO-2026-08.md"
HTML = P.CONSEGNA / "AGGIORNAMENTO-2026-08.html"
FRAMMENTI = P.LAVORAZIONE / "frammenti-finestra4.json"

# Il foglio di stile di md-to-html.py e' pensato per un documento di testo stampabile e non
# conosce grafici. Queste regole si limitano a cio' che serve, riusando i colori del documento.
CSS_AGGIUNTIVO = """
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
.viz { break-inside: avoid; }
/* --- grafici e figure della finestra 4 --- */
.viz { margin: 1.4em 0; overflow-x: auto; page-break-inside: avoid; }
.viz svg.chart { display: block; width: 100%; min-width: 660px; height: auto; }
.viz figure { margin: 0; }
.viz figure img { display: block; width: 100%; height: auto; border: 1px solid var(--rule); }
.viz figcaption { color: var(--mute); font-size: .82em; margin-top: .5em; line-height: 1.45;
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
.viz table { border-collapse: collapse; width: 100%; font-size: .8em; min-width: 600px;
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
.viz th, .viz td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--rule);
  white-space: nowrap; vertical-align: top; }
.viz th { color: var(--mute); font-weight: 600; font-size: .82em; text-transform: uppercase;
  letter-spacing: .04em; }
.viz td.w { white-space: normal; max-width: 380px; }
.viz tr.warn td { background: #f6e9e9; }
.grid { stroke: #e0e0e0; stroke-width: 1; }
.grid.zero { stroke: var(--mute); }
.ax { fill: var(--mute); font-size: 11px; font-family: -apple-system, "Segoe UI", sans-serif; }
.ax.r { fill: var(--ink); }
.val { fill: var(--mute); font-size: 11px; font-family: -apple-system, "Segoe UI", sans-serif; }
.lbl { font-size: 12px; font-weight: 600; font-family: -apple-system, "Segoe UI", sans-serif; }
.lbl.s1, .lbl.pos { fill: #2a78d6; }
.lbl.s2 { fill: #eb6834; }
.lbl.neg, .lbl.bad { fill: #c0392b; }
.lbl.mut { fill: var(--mute); }
.ln { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.ln.s1 { stroke: #2a78d6; } .ln.s2 { stroke: #eb6834; }
.pt { stroke: #fff; stroke-width: 2; }
.pt.s1 { fill: #2a78d6; } .pt.s2 { fill: #eb6834; }
circle.bad { fill: none; stroke: #c0392b; stroke-width: 2.5; }
.bar.pos, .bar.seq { fill: #2a78d6; }
.bar.neg, .bar.crit { fill: #c0392b; }
.lane { fill: #eeeeee; }
.ev.grave { fill: #c0392b; }
.ev.lieve { fill: var(--mute); opacity: .55; }
"""


def main():
    if not FRAMMENTI.exists():
        sys.exit("manca %s: eseguire prima tools/genera-grafici.py" % FRAMMENTI.name)
    frammenti = json.loads(FRAMMENTI.read_text(encoding="utf-8"))

    subprocess.run([sys.executable, str(BASE / "tools" / "md-to-html.py"),
                    str(MD), "--out", str(HTML)], check=True)

    h = HTML.read_text(encoding="utf-8")

    # md-to-html avvolge in un paragrafo ogni riga che non riconosce: i segnaposto arrivano
    # quindi come <p>[[nome]]</p> ed e' quella forma che va sostituita, non la sola parentesi.
    usati, mancanti = [], []

    def innesta(m):
        nome = m.group(1)
        if nome not in frammenti:
            mancanti.append(nome)
            return m.group(0)
        usati.append(nome)
        return '<div class="viz">%s</div>' % frammenti[nome]

    h = re.sub(r"<p>\s*\[\[([a-z0-9_]+)\]\]\s*</p>", innesta, h)
    h = re.sub(r"\[\[([a-z0-9_]+)\]\]", innesta, h)   # eventuali segnaposto in altre posizioni

    h = h.replace("</style>", CSS_AGGIUNTIVO + "\n</style>", 1)
    HTML.write_text(h, encoding="utf-8")

    print("segnaposto innestati: %d (%s)" % (len(usati), ", ".join(usati)))
    if mancanti:
        print("ATTENZIONE, segnaposto senza frammento: %s" % ", ".join(sorted(set(mancanti))))
    inutilizzati = sorted(set(frammenti) - set(usati))
    if inutilizzati:
        print("frammenti non usati: %s" % ", ".join(inutilizzati))
    print("scritto %s (%.0f KB)" % (HTML.name, HTML.stat().st_size / 1024))


if __name__ == "__main__":
    main()

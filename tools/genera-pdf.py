#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converte in PDF i documenti del progetto, senza passare dalla stampa manuale del browser.

Usa Edge o Chrome in modalita' headless. La resa dei fondini e dei grafici richiede che il foglio
di stile dichiari `print-color-adjust: exact`, altrimenti il motore di stampa scarta i colori di
sfondo e le tabelle perdono le righe: la dichiarazione e' nei fogli di stile del progetto.

Uso:
    python tools/genera-pdf.py              tutti i documenti di consegna e fascicolo
    python tools/genera-pdf.py consegna     solo una cartella
    python tools/genera-pdf.py consegna/AGGIORNAMENTO-2026-08.html   un singolo file
"""

import os
import pathlib
import subprocess
import sys
import time
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import percorsi as P  # noqa: E402

BROWSER = None
for _c in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
           r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
           r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
    if os.path.exists(_c):
        BROWSER = _c
        break


def in_pdf(html: pathlib.Path) -> pathlib.Path:
    """Stampa un HTML in PDF con lo stesso nome, restituendo il percorso prodotto."""
    pdf = html.with_suffix(".pdf")
    prima = pdf.stat().st_mtime if pdf.exists() else 0
    profilo = P.LAVORAZIONE / ".profilo-stampa"
    profilo.mkdir(parents=True, exist_ok=True)
    subprocess.run([BROWSER,
                    "--headless=new", "--disable-gpu", "--no-first-run", "--no-sandbox",
                    "--user-data-dir=%s" % profilo,
                    "--no-pdf-header-footer",
                    "--print-to-pdf=%s" % pdf,
                    html.resolve().as_uri()],
                   capture_output=True, timeout=180)
    # il motore scrive il file in modo asincrono rispetto all'uscita del processo
    for _ in range(40):
        if pdf.exists() and pdf.stat().st_mtime > prima and pdf.stat().st_size > 2048:
            return pdf
        time.sleep(0.25)
    return pdf


def bersagli(argv):
    if len(argv) > 1:
        q = BASE / argv[1] if (BASE / argv[1]).exists() else P.CASO / argv[1]
        return [q] if q.is_file() else sorted(q.glob("*.html"))
    out = []
    for d in (P.CONSEGNA, P.FASCICOLO):
        out += sorted(d.glob("*.html"))
    return out


def main():
    if not BROWSER:
        sys.exit("nessun browser trovato: serve Edge o Chrome")
    print("motore di stampa: %s\n" % os.path.basename(BROWSER))
    for h in bersagli(sys.argv):
        p = in_pdf(h)
        stato = "%6.0f KB" % (p.stat().st_size / 1024) if p.exists() else "FALLITO"
        print("  %-44s %s" % (h.name, stato))


if __name__ == "__main__":
    main()

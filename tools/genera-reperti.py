#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compone i reperti fotografici in un unico documento stampabile.

Serve a poter allegare un solo file invece di una cartella di immagini. Ogni reperto e' riportato
a piena larghezza con la propria didascalia, il filmato di origine e l'istante di estrazione, cosi'
che il destinatario possa riestrarlo e verificarlo. Immagini, descrizioni, filmato e istante sono letti
dal catalogo dei media (`media/CATALOGO.csv`, righe con ruolo `reperto`), che resta la sola fonte:
non si duplicano qui. Qui stanno solo le due avvertenze, che sono testo del documento.

Uso: python tools/genera-reperti.py
"""

import base64
import html
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalogo  # noqa: E402
import privato  # noqa: E402
import percorsi as P  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent
OUT = P.CONSEGNA / "REPERTI-2026-08.html"

AVVERTENZE = [
    "Sui reperti 06, 07 e 09 va tenuta un'avvertenza. Ritraggono il cruscotto nei secondi immediatamente "
    "successivi a una riaccensione, quando il contachilometri e l'orologio non hanno ancora ricevuto i valori "
    "reali. Una prima lettura li aveva scambiati per prove di un guasto di comunicazione sul display: l'esame "
    "della sequenza completa dei filmati ha mostrato che si tratta del normale avvio, e l'ipotesi e' stata "
    "ritirata. A display stabile cruscotto e app concordano esattamente, come mostra il reperto 10.",
    "Sulle etichette adesive va tenuta una seconda cautela. Nei filmati compaiono etichette scritte a mano con "
    "il nome del proprietario seguito da 1 o da 2, su giornate diverse e su pacchi diversi, e nel vano "
    "del 16 agosto solo uno dei due pacchi ne porta una. Non sono numeri di serie e la loro "
    "corrispondenza con le serie non e' documentata: va chiesta al centro assistenza.",
]

CSS = """
:root { --ink:#1a1a1a; --mute:#5c5c5c; --rule:#d4d4d4; --bg:#fff; }
* { box-sizing:border-box; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
body { margin:0 auto; padding:32px 28px 64px; max-width:960px; background:var(--bg); color:var(--ink);
  font:15px/1.62 Georgia,"Times New Roman",serif; font-variant-numeric:tabular-nums; }
h1 { font-size:1.8em; line-height:1.25; margin:0 0 .2em; font-weight:600; }
h1 + p { color:var(--mute); font-size:.95em; margin:0 0 1.6em; }
p { margin:0 0 .85em; text-align:justify; hyphens:auto; }
figure { margin:0 0 2.2em; break-inside:avoid; page-break-inside:avoid; }
figure img { display:block; width:100%; height:auto; border:1px solid var(--rule); }
figcaption { color:var(--mute); font-size:.86em; margin-top:.6em; line-height:1.5;
  font-family:-apple-system,"Segoe UI",Roboto,sans-serif; }
figcaption b { color:var(--ink); font-weight:600; }
figcaption .src { display:block; margin-top:.3em; font-size:.92em; }
.avv { border-left:3px solid #c0392b; padding:.2em 0 .2em 14px; margin:1.6em 0; color:var(--mute);
  font-size:.94em; }
hr { border:0; border-top:1px solid var(--rule); margin:2em 0; }
@page { size:A4; margin:16mm 14mm; }
"""


def leggi_reperti():
    """Righe del catalogo con ruolo reperto, in ordine di nome."""
    return sorted((r for r in catalogo.carica() if r["ruolo"] == "reperto"), key=lambda r: r["nome_originale"])


def main():
    reperti = leggi_reperti()
    parti = [
        "<!doctype html><html lang='it'><head><meta charset='utf-8'>",
        "<title>Reperti fotografici, 14 e 16 agosto 2026</title>",
        "<style>%s</style></head><body>" % CSS,
        "<h1>Reperti fotografici estratti dai filmati</h1>",
        "<p>" + html.escape(privato.dato("veicolo")) + " &middot; filmati del 14 e 16 agosto 2026 "
        "&middot; allegato all'aggiornamento del 26 agosto 2026</p>",
        "<p>Ogni fotogramma e' stato estratto con <code>ffmpeg</code> dal filmato indicato in didascalia, "
        "all'istante indicato. Il comando che li riproduce e' "
        "<code>ffmpeg -ss &lt;istante&gt; -i &lt;video&gt;.mp4 -frames:v 1 -q:v 2 out.jpg</code>. "
        "Le descrizioni riportano cio' che si legge sul fotogramma, non cio' che ci si aspettava di trovare.</p>",
    ]
    for a in AVVERTENZE:
        parti.append("<div class='avv'>%s</div>" % html.escape(a))
    parti.append("<hr>")

    n = 0
    for r in reperti:
        img = catalogo.MEDIA / r["file"]
        video, istante, descr = r["fonte_video"], r["istante"], r["didascalia"]
        b64 = base64.b64encode(img.read_bytes()).decode("ascii")
        parti.append(
            "<figure><img src='data:image/jpeg;base64,%s' alt='%s'>"
            "<figcaption><b>%s</b><br>%s"
            "<span class='src'>Origine: %s, istante %s</span></figcaption></figure>"
            % (b64, html.escape(pathlib.Path(r["nome_originale"]).stem), html.escape(pathlib.Path(r["nome_originale"]).stem.replace("_", " ")),
               html.escape(descr), html.escape(video), html.escape(istante)))
        n += 1

    parti.append("</body></html>")
    OUT.write_text("".join(parti), encoding="utf-8")
    print("composti %d reperti in %s (%.0f KB)" % (n, OUT.name, OUT.stat().st_size / 1024))


if __name__ == "__main__":
    main()

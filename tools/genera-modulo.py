#!/usr/bin/env python3
"""Genera il modulo di una pagina per l'officina, come PDF compilabile.

Il modulo e' un AcroForm con campi di testo veri: si compila a schermo con
qualunque lettore PDF, browser inclusi, e si salva; stampato, le stesse caselle
restano righe da riempire a mano. Sta deliberatamente in una pagina sola,
perche' un modulo che non si vede tutto in una volta non viene compilato.
"""

import pathlib
import sys

import fitz

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import privato  # noqa: E402
import percorsi as P  # noqa: E402

OUT = P.CONSEGNA / "MODULO-OFFICINA.pdf"

INK = (0.10, 0.10, 0.10)
MUTE = (0.42, 0.42, 0.42)
RULE = (0.72, 0.72, 0.72)
HEAD = (0.93, 0.93, 0.90)
FIELD = (1.0, 1.0, 0.96)

MISURE = [
    ("Corrente totale a riposo", "A", "oltre 0,5 A: sostituire", "p. 109, cod. 12"),
    ("Differenza tensione fra celle", "mV", "oltre 50 mV: sostituire", "p. 109, cod. 11"),
    ("Capacita' residua", "Ah", "nominale 31 Ah", "targa pacco"),
    ("Capacita' residua", "Wh", "nominale 1488 Wh", "targa pacco"),
]

VERIFICHE = [
    ("Codici in memoria errori", "anche a 3 cifre: 121, 122, 134, 154, 191"),
    ("Connettori FOC e BMS", "serraggio, ossidazione"),
    ("BCS e cablaggio vano batterie", "continuita' su entrambi i rami"),
    ("Ricarica da frenata su entrambi i rami", "simmetria fra i rami"),
    ("Versione firmware BMS / BCS / controllore", "e aggiornamento se disponibile"),
]


def text(p, x, y, s, size=8.5, color=INK, font="helv"):
    p.insert_text((x, y), s, fontname=font, fontsize=size, color=color)


def field(p, name, rect, multiline=False, size=9):
    w = fitz.Widget()
    w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w.field_name = name
    w.rect = rect
    w.field_value = ""
    w.text_fontsize = size
    w.text_color = (0, 0, 0.55)
    w.fill_color = FIELD
    w.border_color = RULE
    w.border_width = 0.6
    if multiline:
        w.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE
    p.add_widget(w)


def main():
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    L, R = 38, 557

    text(p, L, 52, "MODULO DI DIAGNOSI IN GARANZIA", 13, INK, "hebo")
    text(p, L, 66, "NIU MQi GT  -  targa %s  -  telaio %s  -  circa 6832 km  -  circa 100 cicli" % (privato.dato("targa"), privato.dato("telaio")), 8, MUTE)
    text(p, L, 78, "Intestatario %s  -  venditore %s  -  richiesta in garanzia legale di conformita'" % (privato.dato("intestatario"), privato.dato("venditore")), 8, MUTE)
    p.draw_line((L, 86), (R, 86), color=RULE, width=0.8)

    # ---- configurazione slot ----
    y = 104
    text(p, L, y, "1.  CONFIGURAZIONE ALLA CONSEGNA   (da annotare aprendo la sella)", 9.5, INK, "hebo")
    y += 12
    p.draw_rect(fitz.Rect(L, y, R, y + 15), color=RULE, fill=HEAD, width=0.5)
    text(p, L + 4, y + 10.5, "Alloggiamento", 8, INK, "hebo")
    text(p, L + 170, y + 10.5, "Etichetta app", 8, INK, "hebo")
    text(p, L + 260, y + 10.5, "Numero di serie del pacco presente", 8, INK, "hebo")
    y += 15
    for lab, et in (("Slot 1, vicino al manubrio", "B"), ("Slot 2, lontano dal manubrio", "A")):
        p.draw_rect(fitz.Rect(L, y, R, y + 20), color=RULE, width=0.5)
        text(p, L + 4, y + 13, lab, 8.5)
        text(p, L + 170, y + 13, et, 8.5)
        field(p, f"serie_{et}", fitz.Rect(L + 258, y + 3, R - 4, y + 17))
        y += 20

    # ---- misure numeriche ----
    y += 14
    text(p, L, y, "2.  MISURE CON VALORE NUMERICO   (priorita': le prime due autorizzano la sostituzione)", 9.5, INK, "hebo")
    y += 12
    p.draw_rect(fitz.Rect(L, y, R, y + 24), color=RULE, fill=HEAD, width=0.5)
    text(p, L + 4, y + 9, "Misura", 8, INK, "hebo")
    text(p, L + 4, y + 19, "riferimento manuale d'officina", 7, MUTE)
    text(p, L + 232, y + 9, "Pacco ...200168", 8, INK, "hebo")
    text(p, L + 232, y + 19, "slot da annotare sopra", 7, MUTE)
    text(p, L + 340, y + 9, "Pacco ...300439", 8, INK, "hebo")
    text(p, L + 340, y + 19, "slot da annotare sopra", 7, MUTE)
    text(p, L + 448, y + 9, "Soglia costruttore", 8, INK, "hebo")
    y += 24
    for i, (lab, unit, soglia, rif) in enumerate(MISURE):
        h = 26
        p.draw_rect(fitz.Rect(L, y, R, y + h), color=RULE, width=0.5)
        text(p, L + 4, y + 11, f"{lab}  [{unit}]", 8.5)
        text(p, L + 4, y + 21, rif, 7, MUTE)
        field(p, f"m{i}_168", fitz.Rect(L + 230, y + 5, L + 332, y + h - 5))
        field(p, f"m{i}_439", fitz.Rect(L + 338, y + 5, L + 440, y + h - 5))
        text(p, L + 448, y + 16, soglia, 7.5, MUTE)
        y += h

    # ---- verifiche con esito ----
    y += 14
    text(p, L, y, "3.  VERIFICHE CON ESITO", 9.5, INK, "hebo")
    y += 12
    for i, (lab, sub) in enumerate(VERIFICHE):
        h = 24
        p.draw_rect(fitz.Rect(L, y, R, y + h), color=RULE, width=0.5)
        text(p, L + 4, y + 10, lab, 8.5)
        text(p, L + 4, y + 19, sub, 7, MUTE)
        field(p, f"v{i}", fitz.Rect(L + 268, y + 4, R - 4, y + h - 4))
        y += h

    # ---- dati amministrativi ----
    y += 14
    text(p, L, y, "4.  DATI DA ACQUISIRE", 9.5, INK, "hebo")
    y += 8
    for name, lab in (("pratica", "Numero pratica di garanzia aperta presso il costruttore"),
                      ("importatore", "Importatore NIU per l'Italia: denominazione e PEC")):
        text(p, L, y + 12, lab, 8.5)
        field(p, name, fitz.Rect(L + 300, y + 2, R, y + 16))
        y += 22

    y += 6
    text(p, L, y, "Note dell'officina", 8.5)
    field(p, "note", fitz.Rect(L, y + 6, R, y + 62), multiline=True, size=8.5)
    y += 72

    text(p, L, y + 12, "Data", 8.5)
    field(p, "data", fitz.Rect(L + 34, y + 2, L + 150, y + 16))
    text(p, L + 170, y + 12, "Firma e timbro", 8.5)
    field(p, "firma", fitz.Rect(L + 246, y + 2, R, y + 16))
    y += 30

    p.draw_line((L, y), (R, y), color=RULE, width=0.5)
    text(p, L, y + 11,
         "Si richiede che le misure siano eseguite su entrambi i pacchi con il medesimo strumento e nella medesima sessione, e che", 7.5, MUTE)
    text(p, L, y + 20,
         "l'esito sia espresso con il valore rilevato. Relazione tecnica completa a corredo: REPORT-DIAGNOSI.pdf, 37 pagine.", 7.5, MUTE)

    doc.save(OUT, garbage=3, deflate=True)
    n = len([w for w in p.widgets()])
    print(f"scritto {OUT} - 1 pagina, {n} campi compilabili")


if __name__ == "__main__":
    main()

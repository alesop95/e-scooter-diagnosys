#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legge in locale le schermate dell'app NIU catturate con il Samsung S25 Ultra e ne fa una bozza di letture.

Guardare una schermata intera costa al modello un migliaio e mezzo di token, e una rilevazione ne
conta quattro o cinque. Le schermate del S25 Ultra hanno pero' tutte la stessa risoluzione, 1440x3120,
e l'app colloca ogni dato sempre nella stessa fascia di pixel: si puo' quindi leggere tutto in locale
con un OCR (`rapidocr_onnxruntime`), senza rete e senza token, e mandare al modello solo i pochi
ritagli su cui la lettura automatica non e' sicura.

Il riconoscimento procede in due stadi. Il primo classifica la schermata dal testo della fascia del
titolo (Home, Batteria con autonomia, Batteria con il dettaglio dei pacchi, Battery Management,
Information Center, Past Routes). Il secondo cerca, dentro le fasce di pixel attese per quel tipo,
l'etichetta del dato ("Battery temperature", "Total Mileage"...) e prende il valore sulla stessa riga:
la fascia fissa limita l'area, l'etichetta assorbe lo scorrimento della pagina. La scheda A o B
selezionata nella pagina della batteria si riconosce dal colore di fondo, piu' chiaro su quella attiva.

I valori passano controlli di plausibilita'. Escono:

    _lavorazione/bozze/<nome>-letture.jsonl   una riga per sessione, nello schema di data/finestra4-letture.jsonl,
                                              con i campi `_fonti` (file per campo) e `_dubbi`
    _lavorazione/bozze/<nome>-verifica-N.jpg  i soli ritagli dei campi dubbi, in scala di grigi, impilati

Nella schermata Past Routes si leggono solo data, orari, distanza, durata e velocita' media: la fascia
con gli indirizzi non si ritaglia e il suo testo non si scrive da nessuna parte. Lo stesso vale per il
nome del veicolo e per l'indirizzo nella Home.

    python tools/leggi-schermate.py [--da AAAA-MM-GG] [--a AAAA-MM-GG] [--nome N] [--tutti]
    python tools/leggi-schermate.py --file Screenshot_...jpg [...]       solo quei file, stampa i valori

`--tutti` mette nel foglio di verifica anche i campi non dubbi. I risultati dell'OCR si conservano in
`_lavorazione/ocr-cache.json`, indicizzati per hash, cosi' che una seconda lettura non costi nulla.
"""

import argparse
import datetime
import io
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalogo as C  # noqa: E402

BASE = C.BASE
BOZZE = C.P.LAVORAZIONE / "bozze"
CACHE = C.P.LAVORAZIONE / "ocr-cache.json"
RISOLUZIONE = (1440, 3120)

# fasce verticali, in pixel nativi del S25 Ultra: sopra la barra di stato, sotto la barra di navigazione
Y_TITOLO = (140, 300)
Y_UTILE = (300, 2960)
SOGLIA_CONF = 0.45

NUM = r"-?\d+(?:[.,]\d+)?"


# --------------------------------------------------------------------------- OCR
_motore = None


def motore():
    global _motore
    if _motore is None:
        import logging
        logging.disable(logging.WARNING)
        from rapidocr_onnxruntime import RapidOCR
        _motore = RapidOCR()
    return _motore


def carica_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salva_cache(c):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, CACHE)


def ocr(percorso, cache=None, chiave=None):
    """Lista di token (x0, y0, x1, y1, testo, conf) in pixel nativi."""
    if cache is not None and chiave in cache:
        return [tuple(t) for t in cache[chiave]]
    import numpy as np
    from PIL import Image
    with Image.open(percorso) as im:
        a = np.array(im.convert("RGB"))
    res, _ = motore()(a)
    out = []
    for box, txt, conf in res or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append((int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)), txt.strip(), round(float(conf), 3)))
    if cache is not None and chiave:
        cache[chiave] = out
    return out


def riconosci(percorso, riquadro, cache=None, chiave=None):
    """Lettura di un riquadro di pixel fisso con il solo riconoscitore, senza il rilevatore di testo.

    Il rilevatore dell'OCR, sulla pagina intera, perde le cifre isolate e grandi (lo "0%" dell'uso a 30
    giorni, una temperatura): ma sul S25 Ultra il valore sta sempre nello stesso riquadro rispetto alla
    sua etichetta, quindi basta dare quel riquadro al riconoscitore. Torna un token in pixel nativi."""
    x0, y0, x1, y1 = (int(v) for v in riquadro)
    k = "%s@%d,%d,%d,%d" % (chiave, x0, y0, x1, y1) if chiave else None
    if cache is not None and k in cache:
        t = cache[k]
        return tuple(t) if t else None
    import numpy as np
    from PIL import Image
    with Image.open(percorso) as im:
        c = np.array(im.convert("RGB").crop((x0, y0, x1, y1)))
    res = motore().text_recognizer([c])[0]
    t = None
    if res and res[0][0].strip():
        t = (x0, y0, x1, y1, res[0][0].strip(), round(float(res[0][1]), 3))
    if cache is not None and k:
        cache[k] = t
    return t


# --------------------------------------------------------------------------- tipo di schermata
def classifica(tok):
    titolo = " ".join(t[4] for t in tok if Y_TITOLO[0] <= t[1] <= Y_TITOLO[1])
    tutto = " ".join(t[4] for t in tok)
    if "Management" in titolo or "Currently in use" in tutto:
        return "gestione"
    if "Information" in titolo:
        return "centro_info"
    if re.search(r"a?st Routes", titolo):
        return "tragitti"
    if "Riding Data" in titolo:
        return "dati_guida"
    if "Battery temperature" in tutto or "Battery Cycles" in tutto:
        return "batteria_dettaglio"
    if "Battery Level" in tutto and "Range" in tutto:
        return "batteria_autonomia"
    if "Total Mileage" in tutto and not titolo.startswith("<"):
        return "home"
    return "sconosciuta"


# --------------------------------------------------------------------------- utilita' di posizione
def cy(t):
    return (t[1] + t[3]) / 2


def etichetta(tok, pat):
    for t in tok:
        if re.search(pat, t[4]):
            return t
    return None


def sulla_riga(tok, rif, x_min=0, x_max=1440, pat=None, tolleranza=70):
    c = [t for t in tok if abs(cy(t) - cy(rif)) <= tolleranza and t is not rif
         and x_min <= t[0] <= x_max and (pat is None or re.search(pat, t[4]))]
    return sorted(c, key=lambda t: t[0])


def sopra(tok, rif, distanza=(20, 260), pat=None):
    """Token sopra l'etichetta, con sovrapposizione orizzontale."""
    c = [t for t in tok if distanza[0] <= rif[1] - t[3] <= distanza[1]
         and t[0] < rif[2] + 40 and t[2] > rif[0] - 40 and (pat is None or re.search(pat, t[4]))]
    return sorted(c, key=lambda t: rif[1] - t[3])


def numero(s):
    m = re.search(NUM, s.replace(" ", ""))
    if not m:
        return None
    v = m.group(0).replace(",", ".")
    return float(v) if "." in v else int(v)


class Lettura:
    """Valori estratti da una schermata, con il riquadro da cui vengono e la confidenza."""

    def __init__(self, file, tipo, percorso=None, cache=None, chiave=None):
        self.file, self.tipo = file, tipo
        self.percorso, self.cache, self.chiave = percorso, cache, chiave
        self.valori, self.riquadri, self.conf, self.dubbi = {}, {}, {}, []

    def a_destra(self, tok, rif, x_min, pat, tolleranza=70):
        """Valore sulla riga dell'etichetta; se l'OCR della pagina non l'ha visto, rilegge la zona."""
        v = sulla_riga(tok, rif, x_min, 1440, pat, tolleranza)
        if v or not self.percorso:
            return v
        return self.zona((max(x_min, 980), cy(rif) - 48, 1345, cy(rif) + 48), pat)

    def zona(self, riquadro, pat):
        t = riconosci(self.percorso, riquadro, self.cache, self.chiave)
        return [t] if t and re.search(pat, t[4]) else []

    def dubbio(self, campo, motivo, riquadro):
        self.dubbi.append({"campo": campo, "file": self.file, "motivo": motivo, "riquadro": riquadro})

    def metti(self, campo, valore, *tokens):
        if valore is None:
            return
        self.valori[campo] = valore
        tk = [t for t in tokens if t]
        if tk:
            self.riquadri[campo] = (min(t[0] for t in tk), min(t[1] for t in tk),
                                    max(t[2] for t in tk), max(t[3] for t in tk))
            self.conf[campo] = min(t[5] for t in tk)


# --------------------------------------------------------------------------- lettori per tipo
def leggi_home(tok, L):
    st = [t for t in tok if 450 <= t[1] <= 750 and t[4] in ("On", "Off")]
    if st:
        L.metti("stato", st[0][4], st[0])
    km = [t for t in tok if 750 <= t[1] <= 1050 and t[0] < 500 and t[4] == "km"]
    if km:
        v = sulla_riga(tok, km[0], 0, km[0][0], r"^\d+$", 90)
        if v:
            L.metti("autonomia_km", numero(v[-1][4]), v[-1], km[0])
    soc = [t for t in tok if 1000 <= t[1] <= 1250 and t[0] < 800 and re.fullmatch(r"\d{1,3}%?", t[4])]
    if soc:
        L.metti("soc_medio_pct", numero(soc[0][4]), soc[0])
    tm = etichetta(tok, r"Total Mileage")
    if tm:
        v = sopra(tok, tm, (5, 200), r"^\d{3,6}\s*k?m?$")
        if v:
            L.metti("km_totali", numero(v[0][4]), v[0], tm)
        riga = [t for t in tok if 20 <= tm[1] - t[3] <= 200 and t[2] < tm[0] - 10]
        y0, y1 = tm[1] - 175, tm[1] - 25          # riga dei valori, sopra le etichette
        d = [t for t in riga if re.fullmatch(NUM + r"\s*km", t[4])] or \
            L.zona((480, y0, 815, y1), NUM + r"\s*km$")
        if d:
            L.metti("ultimo_tragitto_km", numero(d[0][4]), d[0])
        dur = [t for t in riga if re.search(r"\d+'\d+", t[4])]
        rilettura = L.zona((790, y0, 1050, y1), r"\d+'\d+")
        if dur and rilettura and durata(dur[0][4]) != durata(rilettura[0][4]):
            L.dubbio("ultimo_tragitto_durata", "due letture: %s e %s" % (durata(dur[0][4]), durata(rilettura[0][4])),
                     dur[0][:4])
            # l'errore tipico e' una cifra persa ("11'04" letto "1'04""): si tiene la lettura piu' lunga
            if len(re.sub(r"\D", "", rilettura[0][4])) > len(re.sub(r"\D", "", dur[0][4])):
                dur = rilettura
        dur = dur or rilettura
        if dur:
            L.metti("ultimo_tragitto_durata", durata(dur[0][4]), dur[0])
    pk = etichetta(tok, r"%/km")
    if pk:
        v = sulla_riga(tok, pk, 0, pk[0], r"^" + NUM + r"$", 60) or \
            L.zona((pk[0] - 260, cy(pk) - 60, pk[0] + 5, cy(pk) + 45), r"^" + NUM + r"$")
        if v:
            L.metti("consumo_pct_km", numero(v[-1][4]), v[-1], pk)
            if re.search(r"\.\d\d", v[-1][4]):         # l'app mostra un decimale: il secondo e' un'altra cifra letta male
                L.dubbio("consumo_pct_km", "due decimali: %s" % v[-1][4], v[-1][:4])


def durata(s):
    m = re.search(r"(\d+)'\s*(\d+)", s)
    return "%d'%02d\"" % (int(m.group(1)), int(m.group(2))) if m else None


def ricarica(s):
    m = re.search(r"just\s*now\s*charged\s*to\s*(\d+)\s*%", s, re.I)
    if m:
        p = int(m.group(1))
        return "appena ora %s%d%%" % ("all'" if (p in (1, 8, 11) or str(p).startswith("8")) else "al ", p)
    m = re.search(r"(\d+)\s*(min|h|d|day)\w*\s+ago\s+charged\s+to\s+(\d+)\s*%", s, re.I)
    if not m:
        return None
    n, u, p = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    u = {"min": "min", "h": "h", "d": "g", "day": "g"}[u]
    art = "all'" if (p in (1, 8, 11) or str(p).startswith("8")) else "al "
    return "%d %s fa %s%d%%" % (n, u, art, p)


def leggi_batteria_autonomia(tok, L):
    bl = etichetta(tok, r"^Battery Level$")
    if bl:
        v = sopra(tok, bl, (10, 260), r"^\d{1,3}$")
        if v:
            L.metti("soc_medio_pct", numero(v[0][4]), v[0], bl)
    rg = etichetta(tok, r"^Range$")
    if rg:
        v = sopra(tok, rg, (10, 260), r"^\d{1,3}$")
        if v:
            L.metti("autonomia_batteria_km", numero(v[0][4]), v[0], rg)
    rc = [t for t in tok if re.search(r"(ago|now)\s*charged", t[4], re.I)]
    if rc:
        L.metti("ultima_ricarica", ricarica(rc[0][4]), rc[0])


def scheda_attiva(percorso, riga_y):
    """'a' o 'b': la scheda selezionata ha il fondo piu' chiaro (circa 48 contro 19 di luminosita')."""
    import numpy as np
    from PIL import Image
    with Image.open(percorso) as im:
        a = np.asarray(im.convert("L"), dtype=float)
    y0, y1 = int(riga_y - 45), int(riga_y + 45)
    sx = float(np.median(a[y0:y1, 120:700]))
    dx = float(np.median(a[y0:y1, 780:1320]))
    if abs(sx - dx) < 10:
        return None
    return "a" if sx > dx else "b"


def leggi_batteria_dettaglio(tok, L, percorso):
    us = etichetta(tok, r"^Used$")
    if us:
        v = L.a_destra(tok, us, 900, r"^\d{1,3}\s*[%:]?$", 90)
        if v:
            L.metti("uso_30gg_pct", numero(v[0][4]), v[0], us)
    bt = etichetta(tok, r"Battery temperature")
    if not bt:
        return
    pct = [t for t in tok if 120 <= bt[1] - t[3] <= 420 and re.fullmatch(r"(?:[AB]\s*)?(\d{1,3}|--)\s*%?", t[4])]
    sx = [t for t in pct if t[0] < 720]
    dx = [t for t in pct if t[0] >= 720]
    if sx:
        L.metti("a_pct", numero(sx[0][4]), sx[0])
    if dx:
        L.metti("b_pct", numero(dx[0][4]), dx[0])
    L.metti("b_presente", bool(dx and numero(dx[0][4]) is not None), *(dx[:1] or sx[:1]))
    riga = cy(sx[0]) if sx else (cy(dx[0]) if dx else bt[1] - 210)
    lato = scheda_attiva(percorso, riga)
    if lato:
        L.valori["_scheda"] = lato
    v = L.a_destra(tok, bt, 900, r"^-?\d+\s*[°℃Cc]*$")
    if v and lato:
        L.metti("temp_%s_c" % lato, numero(v[0][4]), v[0], bt)
    cyc = etichetta(tok, r"Battery Cycles")
    if cyc:
        v = L.a_destra(tok, cyc, 900, r"^\d+$")
        if v and lato:
            L.metti("cicli_%s" % lato, numero(v[0][4]), v[0], cyc)
    tm = etichetta(tok, r"^Total Mileage$")
    if tm:
        v = L.a_destra(tok, tm, 900, r"^\d+\s*k?m?$")
        if v:
            L.metti("km_totali", numero(v[0][4]), v[0], tm)
    sp = etichetta(tok, r"Spare Battery Level")
    if sp:
        v = L.a_destra(tok, sp, 900, r"^\d{1,3}\s*%?$")
        if v:
            L.metti("spare_pct", numero(v[0][4]), v[0], sp)


def leggi_gestione(tok, L):
    storico = etichetta(tok, r"Historical usage")
    y_st = storico[1] if storico else 99999
    parti = []
    for t in tok:
        m = re.search(r"[A-Z0-9]{14,18}", t[4].replace(" ", ""))
        if not m or not m.group(0).startswith("BMT"):
            continue
        data = [d for d in tok if 120 <= d[1] - t[3] <= 260 and d[0] > 300 and re.search(r"\d{4}", d[4])]
        cap = [c for c in tok if 0 <= t[1] - c[3] <= 230 and re.fullmatch(r"\d+\s*(Ah)?", c[4]) and c[0] > 1000]
        cosa = "storico" if t[1] > y_st else "in uso"
        quando = data[0][4] if data else "?"
        parti.append("%s %s%s, %s %s" % (cosa, m.group(0), " %sAh" % numero(cap[0][4]) if cap else "",
                                          "ultimo uso" if cosa == "storico" else "primo utilizzo", quando))
        L.riquadri.setdefault("_serie", []).append((t[0], t[1], t[2], t[3]))
    if parti:
        L.valori["_pacchi"] = "; ".join(parti)


def leggi_centro_info(tok, L):
    ore = sorted((t for t in tok if t[0] > 1080 and re.fullmatch(r"\d{2}:\d{2}", t[4])), key=lambda t: t[1])
    giorni = sorted((t for t in tok if t[0] < 120 and re.fullmatch(r"Today|Yesterday|[A-Z][a-z]{2} \d+.*|\d.*", t[4])),
                    key=lambda t: t[1])
    eventi = []
    for o in ore:
        testo = " ".join(t[4] for t in sorted(tok, key=lambda t: t[1])
                         if 260 <= t[0] <= 1080 and o[1] - 70 <= t[1] <= o[1] + 110)
        testo = re.sub(r"Battery\s*has\s*been", "Battery has been", testo)
        g = [d[4] for d in giorni if d[1] < o[1]]
        eventi.append("%s %s %s" % (g[-1] if g else "", o[4], testo))
    if eventi:
        L.valori["_eventi"] = eventi


def leggi_tragitti(tok, L):
    """Solo la scheda inferiore del tragitto selezionato; nessun testo d'indirizzo."""
    basso = [t for t in tok if t[1] >= 2300]
    g = [t for t in basso if re.fullmatch(r"Today|Yesterday|[A-Z][a-z]{2} \d+", t[4])]
    o = [t for t in basso if re.search(r"[AP]M\s*\d{2}:\d{2}\s*-\s*[AP]M\s*\d{2}:\d{2}", t[4])]
    if g:
        L.metti("_giorno", g[0][4], g[0])
    if o:
        hh = re.findall(r"([AP])M\s*(\d{2}):(\d{2})", o[0][4])
        conv = ["%02d:%s" % ((int(h) % 12) + (12 if ap == "P" else 0), m) for ap, h, m in hh]
        L.metti("_orario", " - ".join(conv), o[0])
    km = [t for t in basso if t[4] == "km" and t[0] < 400]
    if km:
        v = [t for t in basso if abs(cy(t) - cy(km[0])) < 60 and t[0] < km[0][0] and re.fullmatch(NUM, t[4])]
        if v:
            L.metti("_km", numero(v[-1][4]), v[-1], km[0])
    dur = sorted((t for t in basso if 380 <= t[0] <= 840 and 2600 <= t[1] <= 2720 and re.search(r"\d", t[4])),
                 key=lambda t: t[0])
    if dur:
        L.metti("_durata", durata("'".join(re.sub(r"[^\d]", "", t[4]) for t in dur[:2])) if len(dur) > 1
                else None, *dur[:2])
    vel = [t for t in basso if t[0] > 1100 and 2620 <= t[1] <= 2720 and re.fullmatch(NUM, t[4])]
    if vel:
        L.metti("_vel_media", numero(vel[0][4]), vel[0])


def leggi_file(r, cache):
    p = C.MEDIA / r["file"]
    tok = ocr(p, cache, r["sha256"])
    tipo = classifica(tok)
    L = Lettura(r["nome_originale"], tipo, p, cache, r["sha256"])
    if tipo == "home":
        leggi_home(tok, L)
    elif tipo == "batteria_autonomia":
        leggi_batteria_autonomia(tok, L)
    elif tipo == "batteria_dettaglio":
        leggi_batteria_dettaglio(tok, L, p)
    elif tipo == "gestione":
        leggi_gestione(tok, L)
    elif tipo == "centro_info":
        leggi_centro_info(tok, L)
    elif tipo == "tragitti":
        leggi_tragitti(tok, L)
    return L


# --------------------------------------------------------------------------- composizione per sessione
CAMPI_LETTURA = ["sessione", "ts", "stato", "soc_medio_pct", "autonomia_km", "a_pct", "b_pct", "b_presente",
                 "temp_a_c", "temp_b_c", "cicli_a", "cicli_b", "km_totali", "spare_pct", "uso_30gg_pct",
                 "consumo_pct_km", "ultima_ricarica", "posizione", "ultimo_tragitto_km",
                 "ultimo_tragitto_durata", "tragitto", "note"]

LIMITI = {"soc_medio_pct": (0, 100), "a_pct": (0, 100), "b_pct": (0, 100), "spare_pct": (0, 100),
          "uso_30gg_pct": (0, 100), "temp_a_c": (-15, 70), "temp_b_c": (-15, 70), "cicli_a": (0, 3000),
          "cicli_b": (0, 3000), "km_totali": (0, 200000), "autonomia_km": (0, 200),
          "autonomia_batteria_km": (0, 200), "consumo_pct_km": (0, 10), "ultimo_tragitto_km": (0, 300)}


def componi(sessione, letture, precedente):
    rec = {k: None for k in CAMPI_LETTURA}
    rec["sessione"] = sessione["id"]
    rec["ts"] = sessione["ts"]
    fonti, dubbi, note, tragitti = {}, [], [], []
    for L in letture:
        for k, v in L.valori.items():
            if k.startswith("_"):
                continue
            if rec.get(k) is not None and rec[k] != v and k != "b_presente":
                # vale la schermata piu' recente della sessione, ma la discordanza va guardata
                dubbi.append({"campo": k, "file": L.file, "motivo": "discorde: %s prima, %s poi" % (rec[k], v),
                              "riquadro": L.riquadri.get(k)})
            rec[k] = v
            fonti[k] = L.file
            if L.conf.get(k, 1) < SOGLIA_CONF:
                dubbi.append({"campo": k, "file": L.file, "motivo": "confidenza OCR %.2f" % L.conf[k],
                              "riquadro": L.riquadri.get(k)})
        dubbi += L.dubbi
        if "_pacchi" in L.valori:
            note.append("Battery Management: " + L.valori["_pacchi"])
        if "_eventi" in L.valori:
            note.append("Information Center: " + "; ".join(L.valori["_eventi"]))
        if L.tipo == "tragitti" and "_km" in L.valori:
            tragitti.append({k[1:]: v for k, v in L.valori.items() if k.startswith("_")})
        if L.tipo == "batteria_dettaglio" and "_scheda" not in L.valori:
            dubbi.append({"campo": "scheda A/B", "file": L.file, "motivo": "scheda selezionata non riconosciuta",
                          "riquadro": L.riquadri.get("a_pct")})
    if rec.get("autonomia_batteria_km") is not None:
        rec["_autonomia_batteria_km"] = rec.pop("autonomia_batteria_km")
    else:
        rec.pop("autonomia_batteria_km", None)
    for k, (lo, hi) in LIMITI.items():
        v = rec.get(k) if k in rec else rec.get("_" + k)
        if isinstance(v, (int, float)) and not lo <= v <= hi:
            dubbi.append({"campo": k, "file": fonti.get(k), "motivo": "fuori intervallo %s-%s" % (lo, hi),
                          "riquadro": None})
    for k, salto in (("km_totali", 400), ("cicli_a", 20), ("cicli_b", 20)):
        v, p = rec.get(k), (precedente or {}).get(k)
        if isinstance(v, (int, float)) and isinstance(p, (int, float)):
            if v < p:
                dubbi.append({"campo": k, "file": fonti.get(k), "motivo": "decresce: %s dopo %s" % (v, p),
                              "riquadro": None})
            elif v - p > salto:
                dubbi.append({"campo": k, "file": fonti.get(k), "motivo": "salto: %s dopo %s" % (v, p),
                              "riquadro": None})
    if tragitti:
        rec["_tragitti"] = tragitti
    for d in dubbi:
        if d.get("riquadro") is None and d.get("file"):
            L = next((x for x in letture if x.file == d["file"]), None)
            d["riquadro"] = L.riquadri.get(d["campo"]) if L else None
    rec["note"] = " | ".join(note) or None
    rec["_fonti"] = fonti
    rec["_dubbi"] = [{k: v for k, v in d.items() if k != "riquadro"} for d in dubbi]
    return rec, dubbi


# --------------------------------------------------------------------------- foglio di verifica
def fogli_verifica(voci, nome, larghezza=480, altezza_max=1600):
    """Impila i ritagli: ogni ritaglio e' la riga del dato, larga quanto lo schermo, ridotta."""
    from PIL import Image, ImageDraw
    ritagli = []
    for v in voci:
        q = v["riquadro"]
        r = C.indice().get(v["file"]) if v.get("file") else None
        if not r:
            continue
        with Image.open(C.MEDIA / r["file"]) as im:
            if q:
                y0, y1 = max(0, q[1] - 30), min(im.height, q[3] + 30)
            else:
                continue
            c = im.crop((0, y0, im.width, y1)).convert("L")
        c = c.resize((larghezza, max(1, round(c.height * larghezza / c.width))), Image.LANCZOS)
        cart = Image.new("L", (larghezza, c.height + 16), 255)
        ImageDraw.Draw(cart).text((2, 2), "%s  %s  %s" % (v["file"][11:26], v["campo"], v["motivo"])[:80], fill=0)
        cart.paste(c, (0, 16))
        ritagli.append(cart)
    usciti, pagina, h = [], [], 0
    for c in ritagli + [None]:
        if c is None or h + c.height > altezza_max:
            if pagina:
                f = Image.new("L", (larghezza, h), 255)
                y = 0
                for x in pagina:
                    f.paste(x, (0, y))
                    y += x.height
                out = BOZZE / ("%s-verifica-%d.jpg" % (nome, len(usciti) + 1))
                f.save(out, "JPEG", quality=80)
                usciti.append(out)
            pagina, h = [], 0
        if c is not None:
            pagina.append(c)
            h += c.height
    return usciti


# --------------------------------------------------------------------------- principale
def candidati(righe, da=None, a=None, nomi=None):
    out = []
    for r in righe:
        if nomi and r["nome_originale"] not in nomi:
            continue
        if r["dispositivo"] != "S25U" or r["tipo"] != "schermata" or r["app"]:
            continue
        if (int(r["larghezza"] or 0), int(r["altezza"] or 0)) != RISOLUZIONE:
            continue
        g = r["ts"][:10]
        if (da and g < da) or (a and g > a):
            continue
        out.append(r)
    return sorted(out, key=lambda r: (r["ts"], r["nome_originale"]))


def leggi(righe, cache):
    """Letture per file, in ordine di cattura."""
    return [(r, leggi_file(r, cache)) for r in righe]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--da")
    ap.add_argument("--a")
    ap.add_argument("--nome")
    ap.add_argument("--file", nargs="*")
    ap.add_argument("--tutti", action="store_true")
    args = ap.parse_args()

    righe = candidati(C.carica(), args.da, args.a, set(args.file) if args.file else None)
    if not righe:
        print("nessuna schermata S25 Ultra dell'app NIU nell'intervallo")
        return 0
    cache = carica_cache()
    letture = leggi(righe, cache)
    salva_cache(cache)

    if args.file:
        for r, L in letture:
            print("%s  %-19s %s" % (r["nome_originale"], L.tipo,
                                    json.dumps(L.valori, ensure_ascii=False)))
        return 0

    sessioni = {}
    for r, L in letture:
        sessioni.setdefault(r["sessione"], []).append((r, L))
    BOZZE.mkdir(parents=True, exist_ok=True)
    nome = args.nome or "%s_%s" % (righe[0]["ts"][:10], righe[-1]["ts"][:10])
    out = BOZZE / ("%s-letture.jsonl" % nome)
    tutti_dubbi, prec, n = [], None, 0
    with io.open(out, "w", encoding="utf-8") as fh:
        for sid, voci in sessioni.items():
            s = {"id": sid, "ts": voci[0][0]["ts"]}
            rec, dubbi = componi(s, [L for _, L in voci], prec)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            tutti_dubbi += dubbi
            if args.tutti:
                for _, L in voci:
                    tutti_dubbi += [{"campo": k, "file": L.file, "motivo": str(L.valori[k]), "riquadro": q}
                                    for k, q in L.riquadri.items() if not k.startswith("_")]
            sospetti = {d["campo"] for d in dubbi}
            prec = {**(prec or {}), **{k: v for k, v in rec.items() if v is not None and k not in sospetti}}
            n += 1
    fogli = fogli_verifica(tutti_dubbi, nome)
    tipi = {}
    for _, L in letture:
        tipi[L.tipo] = tipi.get(L.tipo, 0) + 1
    print("schermate lette %d, sessioni %d, campi dubbi %d" % (len(letture), n, len(tutti_dubbi)))
    print("tipi: " + ", ".join("%s %d" % kv for kv in sorted(tipi.items())))
    print("bozza: %s" % out.relative_to(BASE))
    for f in fogli:
        print("foglio di verifica: %s" % f.relative_to(BASE))
    return 0


if __name__ == "__main__":
    sys.exit(main())

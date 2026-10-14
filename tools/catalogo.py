#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalogo unico dei media del progetto, e funzioni comuni a chi lo legge o lo scrive.

Tutti i file multimediali del progetto stanno in `media/`, originali e in una cartella piatta, e
ognuno ha una riga in `media/CATALOGO.csv`. Il catalogo e' la sola fonte su provenienza, istante,
dispositivo, ruolo e sessione di cattura di ogni file: non si scrive a mano, lo scrivono gli script
che importano e leggono. Un file si cerca per nome attraverso `trova()`.

Uso da riga di comando:

    python tools/catalogo.py stato                 riepilogo per campagna, tipo, ruolo e telefono
    python tools/catalogo.py prova <nome> [...]    marca uno o piu' file come prova
    python tools/catalogo.py non-prova <nome> [...] toglie la marcatura
    python tools/catalogo.py sessioni              ricalcola le sessioni di cattura
"""

import csv
import datetime
import hashlib
import io
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import percorsi as P  # noqa: E402

BASE = P.BASE
MEDIA = P.MEDIA
CATALOGO = MEDIA / "CATALOGO.csv"

CAMPI = ["file", "nome_originale", "sha256", "byte",
         "tipo", "ruolo", "dispositivo", "ts", "larghezza", "altezza", "app",
         "campagna", "finestra", "sessione", "schermata", "prova",
         "origine", "nota_origine", "didascalia", "fonte_video", "istante"]

EST_IMMAGINE = (".jpg", ".jpeg", ".png", ".avif", ".webp", ".heic")
EST_VIDEO = (".mp4", ".mov", ".mkv")
EST_AUDIO = (".opus", ".m4a", ".mp3", ".ogg")
EST_MEDIA = EST_IMMAGINE + EST_VIDEO + EST_AUDIO

GAP_SESSIONE = 180      # secondi fra due catture perche' appartengano alla stessa sessione

# Finestre di osservazione, come in README.md. Il 16/08/2025 e' giorno di confine fra la prima e
# la seconda: senza l'ora di passaggio documentata, quel giorno resta assegnato a entrambe.
FINESTRE = [("1", "2025-07-24", "2025-08-16"), ("2", "2025-08-16", "2025-09-11"),
            ("3", "2026-07-30", "2026-08-03"), ("4", "2026-08-13", "2026-08-25")]

# Risoluzioni di cattura schermo dei due telefoni, e modelli EXIF delle loro fotocamere.
SCHERMO = {(1440, 3120): "S25U", (3120, 1440): "S25U", (1080, 2400): "S20FE", (2400, 1080): "S20FE"}
MODELLI = {"Galaxy S25 Ultra": "S25U", "SM-S938": "S25U", "SM-G781": "S20FE"}

_PAT_TS = [
    (re.compile(r"(?:Screenshot_|seq_)?(\d{8})_(\d{6})"), "%Y%m%d%H%M%S"),
    (re.compile(r"(?:photo|video)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})"), "%Y-%m-%d%H-%M-%S"),
]
_PAT_WA = re.compile(r"(IMG|VID|PTT)-(\d{8})-WA\d+")
_PAT_APP = re.compile(r"^Screenshot_\d{8}_\d{6}_(.+)$")


# --------------------------------------------------------------------------- file e hash
def sha256(percorso, blocco=1 << 20):
    h = hashlib.sha256()
    with open(percorso, "rb") as fh:
        while True:
            b = fh.read(blocco)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def carica():
    if not CATALOGO.exists():
        return []
    with io.open(CATALOGO, encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def salva(righe):
    MEDIA.mkdir(parents=True, exist_ok=True)
    righe = sorted(righe, key=lambda r: (r.get("ts") or "9999", r["nome_originale"]))
    tmp = CATALOGO.with_suffix(".csv.tmp")
    with io.open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPI, extrasaction="ignore")
        w.writeheader()
        for r in righe:
            w.writerow({k: r.get(k, "") for k in CAMPI})
    os.replace(tmp, CATALOGO)


def indice(righe=None):
    """Mappa nome originale -> riga."""
    return {r["nome_originale"]: r for r in (righe if righe is not None else carica())}


def trova(nome, righe=None):
    """Percorso attuale su disco del file entrato nel progetto con quel nome, o None."""
    r = indice(righe).get(os.path.basename(nome))
    return (MEDIA / r["file"]) if r else None


def hash_noti(righe):
    """Ogni hash gia' presente nel catalogo -> nome del file."""
    return {r["sha256"]: r["nome_originale"] for r in righe if r.get("sha256")}


# --------------------------------------------------------------------------- metadati
def ts_da_nome(nome):
    stem = os.path.splitext(os.path.basename(nome))[0]
    for pat, fmt in _PAT_TS:
        m = pat.search(stem)
        if m:
            try:
                return datetime.datetime.strptime(m.group(1) + m.group(2), fmt)
            except ValueError:
                pass
    m = _PAT_WA.search(stem)
    if m:      # WhatsApp registra solo il giorno
        try:
            return datetime.datetime.strptime(m.group(2), "%Y%m%d")
        except ValueError:
            pass
    return None


def info_immagine(percorso):
    """(larghezza, altezza, modello EXIF, istante EXIF) di un'immagine; campi vuoti se illeggibili."""
    try:
        from PIL import Image
        with Image.open(percorso) as im:
            w, h = im.size
            ex = im.getexif()
            modello = str(ex.get(0x0110, "") or "").strip("\x00 ")
            quando = ex.get(0x0132)
            try:
                sub = ex.get_ifd(0x8769)
                quando = sub.get(0x9003) or quando
            except Exception:
                pass
            t = None
            if quando:
                try:
                    t = datetime.datetime.strptime(str(quando).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    t = None
            return w, h, modello, t
    except Exception:
        return None, None, "", None


def tipo_di(nome, w=None, h=None):
    e = os.path.splitext(nome)[1].lower()
    if e in EST_VIDEO:
        return "video"
    if e in EST_AUDIO:
        return "audio"
    if os.path.basename(nome).startswith("Screenshot_") or (w, h) in SCHERMO:
        return "schermata"
    if re.match(r"^\d{8}_\d{6}", os.path.basename(nome)):
        return "foto"
    return "immagine"


def app_di(nome):
    """Suffisso d'app degli screenshot Samsung (Screenshot_..._WhatsApp); vuoto per l'app NIU."""
    m = _PAT_APP.match(os.path.splitext(os.path.basename(nome))[0])
    return m.group(1) if m else ""


def dispositivo_di(nome, w, h, modello):
    for k, v in MODELLI.items():
        if modello and modello.startswith(k):
            return v
    if (w, h) in SCHERMO:
        return SCHERMO[(w, h)]
    if _PAT_WA.search(nome):
        return "whatsapp"
    return "ignoto"


def finestra_di(ts):
    if not ts:
        return ""
    g = ts[:10]
    return "|".join(n for n, a, b in FINESTRE if a <= g <= b)


def descrivi(percorso, nome):
    """Campi del catalogo che si ricavano dal file stesso."""
    w, h, modello, t_exif = (None, None, "", None)
    if os.path.splitext(nome)[1].lower() in EST_IMMAGINE:
        w, h, modello, t_exif = info_immagine(percorso)
    t = ts_da_nome(nome) or t_exif
    ts = t.strftime("%Y-%m-%d %H:%M:%S") if t else ""
    return {
        "tipo": tipo_di(nome, w, h),
        "dispositivo": dispositivo_di(nome, w, h, modello),
        "ts": ts,
        "larghezza": w or "",
        "altezza": h or "",
        "app": app_di(nome),
        "finestra": finestra_di(ts),
    }


def cartella_di(r):
    """Cartella, relativa a media/, in cui sta un file: anno e giorno di scatto. I reperti e i
    documenti hanno una cartella propria, perche' sono materiale prodotto e non catture."""
    if r.get("ruolo") == "reperto":
        return "reperti"
    if r.get("ruolo") in ("documento", "render"):
        return "documenti"
    ts = r.get("ts") or ""
    return "%s/%s" % (ts[:4], ts[:10]) if len(ts) >= 10 else "senza-data"


def nome_libero(nome, occupati):
    """Il nome stesso, o con suffisso numerico se gia' occupato da un altro contenuto."""
    if nome not in occupati:
        return nome
    stem, ext = os.path.splitext(nome)
    k = 2
    while "%s_%d%s" % (stem, k, ext) in occupati:
        k += 1
    return "%s_%d%s" % (stem, k, ext)


# --------------------------------------------------------------------------- sessioni
def calcola_sessioni(righe):
    """Raggruppa per prossimita' temporale. La sessione si chiama con l'istante della prima cattura,
    cosi' resta stabile quando arrivano file di altri giorni."""
    datate = sorted((r for r in righe if len(r.get("ts", "")) == 19 and r["tipo"] != "audio"
                     and r["ruolo"] == "originale"), key=lambda r: r["ts"])
    prec, cur = None, ""
    for r in datate:
        t = datetime.datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
        if prec is None or (t - prec).total_seconds() > GAP_SESSIONE:
            cur = t.strftime("%Y%m%d-%H%M%S")
        r["sessione"] = cur
        prec = t
    return righe


# --------------------------------------------------------------------------- comandi
def _stato(righe):
    from collections import Counter
    print("%d file a catalogo, %.1f MB su disco\n" % (len(righe), sum(int(r["byte"] or 0) for r in righe) / 1e6))
    for campo in ("campagna", "tipo", "ruolo", "dispositivo", "prova"):
        c = Counter(r.get(campo) or "-" for r in righe)
        print("%s:" % campo)
        for k, v in c.most_common():
            print("  %6d  %s" % (v, k))
        print()


def _marca(righe, nomi, valore):
    ix = indice(righe)
    for n in nomi:
        r = ix.get(os.path.basename(n))
        if not r:
            print("non a catalogo: %s" % n)
            continue
        r["prova"] = valore
        print("%-60s prova=%s" % (r["nome_originale"], valore or "no"))
    salva(righe)


def main():
    a = sys.argv[1:]
    righe = carica()
    if not a or a[0] == "stato":
        _stato(righe)
    elif a[0] == "prova":
        _marca(righe, a[1:], "si")
    elif a[0] == "non-prova":
        _marca(righe, a[1:], "")
    elif a[0] == "sessioni":
        salva(calcola_sessioni(righe))
        print("sessioni: %d" % len({r["sessione"] for r in righe if r.get("sessione")}))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

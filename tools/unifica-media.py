#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Porta in `media/` tutti i media del progetto e del disco esterno, una volta sola e senza doppioni.

Script storico: ha fatto l'unificazione del 14 ottobre 2026, prima del riordino del progetto sotto
`caso/`; le cartelle d'origine elencate in INTERNE descrivono la disposizione di allora e oggi non
esistono piu'. Si conserva perche' documenta l'operazione e il formato del rapporto.

Fino all'ottobre 2026 le immagini del progetto stavano in otto cartelle diverse e il materiale grezzo
su un disco esterno, con copie identiche sparse fra i due. Questo script le riunisce in una cartella
piatta, una copia per contenuto, e scrive il catalogo. Lavora in due fasi separate, perche' la
seconda e' irreversibile e va decisa guardando l'esito della prima.

    python tools/unifica-media.py importa [radice J]
    python tools/unifica-media.py cancella-origine [radice J] [--conferma]

La fase `importa` calcola lo SHA-256 di ogni file, copia in `media/` un esemplare per contenuto,
rilegge l'hash della copia, porta in `fonti/` i documenti non multimediali, e scrive il catalogo e il
rapporto `_lavorazione/unificazione-rapporto.csv`, che per ogni file d'origine dice dove e' finito.
Solo a copie verificate svuota le cartelle d'origine interne al progetto. Sul disco esterno non
tocca nulla. Si puo' rilanciare: cio' che e' gia' a catalogo non si ricopia.

La fase `cancella-origine` rilegge il rapporto, ricontrolla che ogni file del disco esterno abbia un
esemplare verificato nel progetto, stampa l'elenco e i totali, e cancella solo con `--conferma`.
"""

import csv
import io
import os
import pathlib
import re
import shutil
import struct
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalogo as C  # noqa: E402
import privato  # noqa: E402

BASE = C.BASE
LAV = C.P.LAVORAZIONE
FONTI = C.P.FONTI
RAPPORTO = LAV / "unificazione-rapporto.csv"
J_DEFAULT = pathlib.Path(r"J:\_DOCUMENTATION\NIU MOTORINO\Foto e screen (diagnosi)")

CAMPAGNA_REPERTI = privato.dato("campagna_reperti")
INDICE_REPERTI = BASE / "consegna" / "reperti-2026-08" / "INDICE.md"

# Cartelle interne al progetto: (percorso, campagna, ruolo, regola di nome, nota)
INTERNE = [
    ("consegna/reperti-2026-08", CAMPAGNA_REPERTI, "reperto", None, "fotogrammi estratti dai filmati"),
    ("_lavorazione/foto-vano-2026", "Luglio - Agosto 2026", "originale", None, ""),
    ("_lavorazione/lacuna-2025-2026/novembre-2025", "Novembre 2025", "originale", "lacuna", ""),
    ("_lavorazione/lacuna-2025-2026/marzo-aprile-2026", "Marzo - Aprile 2026", "originale", None,
     "QuickShare_2604271227.zip"),
    ("_lavorazione/lacuna-2025-2026/_video", "Marzo - Aprile 2026", "fotogramma", None,
     "fotogrammi estratti dai filmati"),
    ("_lavorazione/doc-acquisto", "acquisto", "documento", None, "documenti di acquisto e consegna"),
    ("_lavorazione/manual-pages", "manuale", "render", "manuale", "pagine del manuale d'uso"),
    ("_lavorazione/storico/modulo-preview.png", "modulo", "render", None, "anteprima del modulo officina"),
]
# Copie ridotte rigenerabili: non si importano, si eliminano.
DERIVATE = ["_lavorazione/.tmp-crops", "_lavorazione/.tmp-crops-2026",
            "_lavorazione/lacuna-2025-2026/_small"]

PROVA_NOTA = re.compile(r"errore|codice|spia|guasto", re.I)


# --------------------------------------------------------------------------- inventario
def voce(percorso, etichetta, **kw):
    v = {"path": pathlib.Path(percorso), "sorgente": etichetta, "byte": os.path.getsize(percorso)}
    v.update(kw)
    return v


def inventario_j(radice):
    voci = []
    for dp, _, fs in os.walk(radice):
        for f in fs:
            p = pathlib.Path(dp) / f
            rel = p.relative_to(radice)
            parti = rel.parts
            campagna = parti[0] if len(parti) > 1 else ""
            nota = " / ".join(parti[1:-1])
            voci.append(voce(p, "J:/" + rel.as_posix(), lato="J", campagna=campagna, nota=nota,
                             ruolo="originale", regola=None, nome=f))
    return voci


def inventario_progetto():
    voci = []
    for rel, campagna, ruolo, regola, nota in INTERNE:
        q = BASE / rel
        fs = [q] if q.is_file() else sorted(p for p in q.glob("*") if p.is_file() and p != INDICE_REPERTI)             if q.is_dir() else []
        for p in fs:
            voci.append(voce(p, "progetto:/" + p.relative_to(BASE).as_posix(), lato="P",
                             campagna=campagna, nota=nota, ruolo=ruolo, regola=regola, nome=p.name))
    return voci


def inventario_derivate():
    out = []
    for rel in DERIVATE:
        q = BASE / rel
        if q.is_dir():
            out += [p for p in q.rglob("*") if p.is_file()]
    return out


# --------------------------------------------------------------------------- nomi e metadati
def nome_di_arrivo(v):
    nome = v["nome"]
    if v["regola"] == "lacuna":                      # "10112025-_screenshot_00.png" -> nome originale
        nome = re.sub(r"^\d{8}-_", "", nome)
    if v["regola"] == "manuale":
        return "manuale-" + nome
    if C.ts_da_nome(nome) is None and os.path.splitext(nome)[1].lower() in C.EST_MEDIA:
        m = re.search(r"(\d{2})(\d{2})(\d{4})", v["nota"] or v["nome"])
        if m:
            return "%s%s%s_%s" % (m.group(3), m.group(2), m.group(1), nome)
    return nome


def leggi_indice_reperti():
    if not INDICE_REPERTI.exists():
        return {}
    voci = {}
    for r in re.findall(r"^\|\s*`([^`]+\.jpg)`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|",
                        INDICE_REPERTI.read_text(encoding="utf-8"), re.M):
        nome, video, istante, descr = (x.strip().strip("`") for x in r)
        voci[nome] = {"fonte_video": video, "istante": istante, "didascalia": descr}
    return voci


def ts_reperto(video, istante):
    t = C.ts_da_nome(video)
    if not t:
        return ""
    import datetime
    s = float(istante.replace(",", ".").split()[0])
    return (t + datetime.timedelta(seconds=round(s))).strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- zip malformato
def voci_zip(percorso):
    """SHA-256 delle voci di uno zip scorrendo le intestazioni locali.

    L'archivio di marzo-aprile 2026 ha dimensioni a 0xFFFFFFFF nella directory centrale senza campo
    ZIP64, e i lettori standard lo rifiutano; le intestazioni locali e i dati compressi sono invece
    integri, quindi si leggono direttamente."""
    import hashlib
    b = open(percorso, "rb").read()
    out, i = [], 0
    while True:
        i = b.find(b"PK\x03\x04", i)
        if i < 0:
            break
        (_, flag, metodo, _, _, _, csize, usize, nlen, xlen) = struct.unpack("<HHHHHIIIHH", b[i + 4:i + 30])
        nome = b[i + 30:i + 30 + nlen].decode("utf-8", "replace")
        d0 = i + 30 + nlen + xlen
        if metodo == 8:
            z = zlib.decompressobj(-15)
            dati = z.decompress(b[d0:])
            fine = len(b) - len(z.unused_data)
        elif metodo == 0 and not (flag & 8):
            dati = b[d0:d0 + csize]
            fine = d0 + csize
        else:
            raise ValueError("voce non leggibile: %s" % nome)
        out.append((nome, hashlib.sha256(dati).hexdigest(), len(dati)))
        i = fine
    return out


# --------------------------------------------------------------------------- importa
def copia_verificata(src, dst, atteso):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copy2(src, tmp)
    if C.sha256(tmp) != atteso:
        tmp.unlink()
        raise IOError("copia non conforme: %s" % src)
    os.replace(tmp, dst)


def importa(radice_j):
    if not radice_j.is_dir():
        sys.exit("radice non raggiungibile: %s" % radice_j)
    print("Inventario")
    vj = inventario_j(radice_j)
    vp = inventario_progetto()
    der = inventario_derivate()
    print("  disco esterno %d file, progetto %d file, copie ridotte da eliminare %d" % (len(vj), len(vp), len(der)))

    print("Calcolo degli hash")
    for k, v in enumerate(vj + vp, 1):
        v["sha"] = C.sha256(v["path"])
        if k % 100 == 0:
            print("  %d/%d" % (k, len(vj) + len(vp)), flush=True)

    righe = C.carica()
    noti = C.hash_noti(righe)
    per_nome = C.indice(righe)
    occupati = {r["nome_originale"] for r in righe} | {r["file"] for r in righe}
    fonti_hash = {C.sha256(p): p for p in FONTI.iterdir() if p.is_file()}
    reperti = leggi_indice_reperti()
    rapporto = []

    gruppi = {}
    for v in vj + vp:
        gruppi.setdefault(v["sha"], []).append(v)

    nuovi = copiati = 0
    zip_voci = []
    for sha, vs in gruppi.items():
        media = [v for v in vs if os.path.splitext(v["nome"])[1].lower() in C.EST_MEDIA]
        if not media:
            # documenti: archivi, testi, fogli di calcolo, PDF
            if any(v["nome"].lower().endswith(".zip") for v in vs):
                for v in vs:
                    zip_voci.append(v)
                continue
            if sha in fonti_hash:
                dest = fonti_hash[sha]
                esito = "gia' in fonti"
            else:
                pref = sorted(vs, key=lambda v: v["lato"] != "J")[0]
                nome = re.sub(r"^\d{8}-_|^RichiamoU_", "", pref["nome"])
                dest = FONTI / nome
                if dest.exists():
                    dest = FONTI / C.nome_libero(nome, {p.name for p in FONTI.iterdir()})
                src = sorted(vs, key=lambda v: v["lato"] != "P")[0]["path"]
                copia_verificata(src, dest, sha)
                fonti_hash[sha] = dest
                esito = "portato in fonti"
            for v in vs:
                rapporto.append([v["sorgente"], sha, v["byte"], esito, dest.relative_to(BASE).as_posix(), ""])
            continue

        primo = sorted(vs, key=lambda v: (v["lato"] != "J", v["sorgente"]))[0]
        gia = sha in noti
        if gia:
            r = per_nome[noti[sha]]
        else:
            nome = C.nome_libero(nome_di_arrivo(primo), occupati)
            occupati.add(nome)
            src = sorted(vs, key=lambda v: v["lato"] != "P")[0]["path"]   # dal progetto se c'e', e' piu' veloce
            copia_verificata(src, C.MEDIA / nome, sha)
            copiati += 1
            ruolo = next((v["ruolo"] for v in vs if v["ruolo"] != "originale"), "originale")
            r = {"file": nome, "nome_originale": nome, "sha256": sha, "byte": primo["byte"], "ruolo": ruolo,
                 "campagna": primo["campagna"], "prova": ""}
            r.update(C.descrivi(C.MEDIA / nome, nome))
            if ruolo == "reperto":
                r.update(reperti.get(nome, {}))
                r["dispositivo"] = "S25U"
                r["ts"] = ts_reperto(r.get("fonte_video", ""), r.get("istante", "0")) or r["ts"]
                r["finestra"] = C.finestra_di(r["ts"])
            if ruolo == "fotogramma":
                r["fonte_video"] = re.sub(r"^seq_", "", os.path.splitext(nome)[0]) + ".mp4"
            righe.append(r)
            per_nome[nome] = r
            noti[sha] = nome
            nuovi += 1
        orig = [x for x in (r.get("origine") or "").split(" | ") if x]
        note = [x for x in (r.get("nota_origine") or "").split(" | ") if x]
        for v in vs:
            if v["sorgente"] not in orig:
                orig.append(v["sorgente"])
            if v["nota"] and v["nota"] not in note:
                note.append(v["nota"])
            esito = "gia' a catalogo" if gia else ("importato" if v is primo else "doppione")
            rapporto.append([v["sorgente"], sha, v["byte"], esito, "media/" + r["nome_originale"], ""])
        r["origine"] = " | ".join(orig)
        r["nota_origine"] = " | ".join(note)

    # archivi: ogni voce deve gia' essere a catalogo
    for v in zip_voci:
        voci = voci_zip(v["path"])
        mancanti = [n for n, s, _ in voci if s not in noti]
        esito = "archivio, %d voci tutte a catalogo" % len(voci) if not mancanti else \
                "ARCHIVIO CON VOCI MANCANTI: %s" % ", ".join(mancanti[:5])
        rapporto.append([v["sorgente"], v["sha"], v["byte"], esito, "media/", ""])
        for r in righe:
            if any(s == r["sha256"] for _, s, _ in voci) and v["nome"] not in r["nota_origine"]:
                r["nota_origine"] = " | ".join(x for x in [r["nota_origine"], "voce di " + v["nome"]] if x)

    # prova: reperti, filmati da cui sono tratti, materiale di giornate con errori segnalati
    video_reperti = {r.get("fonte_video") for r in righe if r["ruolo"] in ("reperto", "fotogramma")}
    for r in righe:
        if r["ruolo"] == "reperto" or r["nome_originale"] in video_reperti or PROVA_NOTA.search(r["nota_origine"]):
            r["prova"] = "si"

    C.salva(C.calcola_sessioni(righe))

    LAV.mkdir(exist_ok=True)
    with io.open(RAPPORTO, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sorgente", "sha256", "byte", "esito", "destinazione", "nota"])
        for p in der:
            rapporto.append(["progetto:/" + p.relative_to(BASE).as_posix(), "", p.stat().st_size,
                             "copia ridotta rigenerabile, eliminata", "", ""])
        w.writerows(sorted(rapporto))

    print("\nContenuti nuovi in media/: %d (copiati %d)" % (nuovi, copiati))
    print("Catalogo: %d righe | rapporto: %s" % (len(righe), RAPPORTO.relative_to(BASE)))

    # verifica finale prima di svuotare le cartelle interne
    errori = [x for x in rapporto if x[3].startswith("ARCHIVIO CON")]
    for r in righe:
        p = C.MEDIA / r["file"]
        if not p.exists():
            errori.append(["manca", r["file"]])
    mancanti_j = [x for x in rapporto if x[0].startswith("J:/") and not x[4]]
    if errori or mancanti_j:
        print("ERRORI, le cartelle interne non vengono svuotate:")
        for e in (errori + mancanti_j)[:20]:
            print("  ", e)
        return 1

    tolti = 0
    for v in vp:
        if v["path"].exists():
            v["path"].unlink()
            tolti += 1
    for p in der:
        p.unlink()
        tolti += 1
    if INDICE_REPERTI.exists() and all(n in per_nome for n in reperti):
        INDICE_REPERTI.unlink()
        tolti += 1
    for rel in [x[0] for x in INTERNE] + DERIVATE + ["_lavorazione/lacuna-2025-2026"]:
        q = BASE / rel
        if q.is_dir():
            for d in sorted((x for x in q.rglob("*") if x.is_dir()), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
            if not any(q.iterdir()):
                q.rmdir()
    print("Cartelle interne svuotate: %d file tolti dalle posizioni precedenti" % tolti)
    return 0


# --------------------------------------------------------------------------- cancella-origine
def cancella_origine(radice_j, conferma):
    if not RAPPORTO.exists():
        sys.exit("manca il rapporto: eseguire prima la fase importa")
    righe = C.carica()
    noti = C.hash_noti(righe)
    per_nome = C.indice(righe)
    fonti_hash = {C.sha256(p) for p in FONTI.iterdir() if p.is_file()}
    rap = list(csv.DictReader(io.open(RAPPORTO, encoding="utf-8", newline="")))
    da_j = [x for x in rap if x["sorgente"].startswith("J:/")]

    ok, ko = [], []
    for x in da_j:
        p = radice_j / x["sorgente"][3:]
        if not p.exists():
            continue
        s = C.sha256(p)
        if s != x["sha256"]:
            ko.append((x["sorgente"], "cambiato dopo l'importazione"))
        elif x["esito"].startswith("archivio,"):
            voci = voci_zip(p)
            if all(h in noti for _, h, _ in voci):
                ok.append((p, x))
            else:
                ko.append((x["sorgente"], "voci dell'archivio non a catalogo"))
        elif s in noti:
            r = per_nome[noti[s]]
            if (C.MEDIA / r["file"]).exists():
                ok.append((p, x))
            else:
                ko.append((x["sorgente"], "esemplare non trovato in media"))
        elif s in fonti_hash:
            ok.append((p, x))
        else:
            ko.append((x["sorgente"], "nessun esemplare nel progetto"))

    presenti = {p for p, _ in ok} | {radice_j / s[3:] for s, _ in ko}
    estranei = [p for p in (pathlib.Path(dp) / f for dp, _, fs in os.walk(radice_j) for f in fs)
                if p not in presenti]

    from collections import Counter
    c = Counter(x["sorgente"][3:].split("/")[0] if "/" in x["sorgente"][3:] else "(radice)" for _, x in ok)
    print("Cancellabili da %s\n" % radice_j)
    for k, n in sorted(c.items()):
        print("  %5d  %s" % (n, k))
    print("  -----\n  %5d  file, %.2f GiB" % (len(ok), sum(int(x["byte"]) for _, x in ok) / 2**30))
    for s, m in ko:
        print("  NON CANCELLABILE  %s  (%s)" % (s, m))
    for p in estranei:
        print("  ESTRANEO AL RAPPORTO, NON SI TOCCA  %s" % p)
    if ko or not conferma:
        if not conferma:
            print("\nNessuna cancellazione: rilanciare con --conferma.")
        return 1 if ko else 0

    for p, _ in ok:
        p.unlink()
    for dp, ds, fs in sorted(os.walk(radice_j), key=lambda t: -len(t[0])):
        if pathlib.Path(dp) != radice_j and not os.listdir(dp):
            os.rmdir(dp)
    print("\nCancellati %d file." % len(ok))
    return 0


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] not in ("importa", "cancella-origine"):
        print(__doc__)
        return 1
    radice = pathlib.Path(a[1]) if len(a) > 1 else J_DEFAULT
    if a[0] == "importa":
        return importa(radice)
    return cancella_origine(radice, "--conferma" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())

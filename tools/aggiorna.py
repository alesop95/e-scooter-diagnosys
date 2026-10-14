#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ciclo completo di aggiornamento del progetto, dall'assorbimento di nuovi screenshot ai PDF.

Esistono due comandi, perche' fra l'uno e l'altro c'e' l'unico passo che non si automatizza.

    python tools/aggiorna.py ingest [cartella] [--sposta]
    python tools/aggiorna.py

Il primo sposta il materiale nuovo in `media/`, originale e intatto. Senza cartella legge
`media/_arrivo/`, dove si lasciano le foto appena scaricate dal telefono; i file di quella
cartella vengono spostati, quelli di qualunque altra cartella copiati, salvo `--sposta`. Ogni file
entra una volta sola: cio' che il catalogo conosce gia' per hash viene riconosciuto e saltato. Poi
la catena prosegue da sola: sessioni di cattura e lettura locale delle schermate del S25 Ultra in
una bozza con il foglio dei ritagli dubbi. Si ferma alla bozza, perche' la trascrizione in `data/`
resta un lavoro di giudizio: la bozza la prepara, non la sostituisce.

Il secondo, che e' anche il comportamento predefinito, rigenera tutto in ordine di dipendenza:
frammenti grafici, documento della finestra, galleria dei reperti, pagine HTML degli altri
documenti, PDF di tutto, e infine i controlli. Si lancia dopo ogni modifica ai dati o ai testi,
e non serve ricordare quali passi servano ne' in quale ordine.

    python tools/aggiorna.py verifica     esegue i soli controlli, senza rigenerare
"""

import datetime
import glob
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalogo as C  # noqa: E402
import percorsi as P  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable

# Il controllo sui dati personali riguarda i soli documenti che adottano la codifica dei luoghi,
# cioe' l'aggiornamento della finestra 4, dove i tragitti sono espressi con codici Lnn proprio per
# non esporre indirizzi. Non riguarda il report ne' la richiesta di diagnosi, che sono documenti
# nominativi per costruzione e citano intestatario, targa e sede del centro assistenza.
A_LUOGHI_CODIFICATI = ["AGGIORNAMENTO-2026-08.md"]
# I termini vietati sono dati reali e stanno nel layer privato, letti da tools/privato.py.
import privato  # noqa: E402
VIETATI = privato.elenco("luoghi_vietati")

# La regola di stile del progetto e' entrata in vigore con i documenti di agosto 2026. Le due
# lettere e il piano d'azione sono anteriori e usano il grassetto per evidenziare i riferimenti
# normativi: non e' un difetto da correggere, e sono esclusi dal controllo.
STILE_ESCLUSI = ["PEC-contestazione-venditore.md", "PIANO-AZIONE.md"]


def eseguibile(nome):
    return (BASE / "tools" / nome).exists()


def passo(titolo, argv, obbligatorio=True):
    print("  %-46s" % titolo, end="", flush=True)
    r = subprocess.run([PY] + argv, capture_output=True, text=True, cwd=BASE)
    if r.returncode == 0:
        coda = [l for l in r.stdout.strip().splitlines() if l.strip()]
        print("ok" + ("   %s" % coda[-1][:64] if coda else ""))
        return True
    print("FALLITO")
    for l in (r.stderr or r.stdout).strip().splitlines()[-6:]:
        print("      %s" % l)
    if obbligatorio:
        sys.exit("interrotto: %s" % titolo)
    return False


# --------------------------------------------------------------------------- ingest
def finestra_corrente():
    """Numero della finestra piu' recente presente in data/."""
    n = [int(m.group(1)) for f in glob.glob(str(P.DATI / "finestra*-letture.jsonl"))
         for m in [re.search(r"finestra(\d+)-", os.path.basename(f))] if m]
    return max(n) if n else 4


ARRIVO = C.MEDIA / "_arrivo"
PROVA_NOTA = re.compile(r"errore|codice|spia|guasto", re.I)


def ingest(cartella=None, sposta=False):
    q = pathlib.Path(cartella) if cartella else ARRIVO
    if not q.is_dir():
        sys.exit("cartella non trovata: %s" % q)
    da_arrivo = q.resolve() == ARRIVO.resolve()
    sposta = sposta or da_arrivo
    print("Assorbimento di %s (%s)\n" % (q, "spostamento" if sposta else "copia"))

    righe = C.carica()
    noti = C.hash_noti(righe)
    occupati = {r["nome_originale"] for r in righe} | {r["file"] for r in righe}
    nuovi, gia, altri, da_togliere = [], 0, [], []
    for p in sorted(x for x in q.rglob("*") if x.is_file()):
        if os.path.splitext(p.name)[1].lower() not in C.EST_MEDIA:
            altri.append(p)
            continue
        h = C.sha256(p)
        if h in noti:                              # gia' assorbito
            gia += 1
            da_togliere.append(p)
            continue
        nome = C.nome_libero(p.name, occupati)
        occupati.add(nome)
        info = C.descrivi(p, nome)
        dst = C.MEDIA / C.cartella_di({"ts": info["ts"], "ruolo": "originale"}) / nome
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(nome + ".tmp")
        shutil.copy2(p, tmp)
        if C.sha256(tmp) != h:
            tmp.unlink()
            sys.exit("copia non conforme: %s" % p)
        os.replace(tmp, dst)
        rel = p.relative_to(q)
        r = {"file": dst.relative_to(C.MEDIA).as_posix(), "nome_originale": nome, "sha256": h,
             "byte": p.stat().st_size, "ruolo": "originale",
             "campagna": "" if da_arrivo else (rel.parts[0] if len(rel.parts) > 1 else q.name),
             "nota_origine": " / ".join(rel.parts[1:-1] if not da_arrivo else rel.parts[:-1]),
             "origine": str(p), "prova": "si"}
        r.update(info)
        if PROVA_NOTA.search(r["nota_origine"] + " " + r["campagna"]):
            r["prova"] = "si"
        righe.append(r)
        noti[h] = nome
        nuovi.append(r)
        da_togliere.append(p)
    C.salva(C.calcola_sessioni(righe))
    if sposta:
        for p in da_togliere:
            p.unlink()
    print("  nuovi in media/            : %d" % len(nuovi))
    print("  gia' assorbiti, saltati    : %d" % gia)
    if altri:
        print("  non multimediali, lasciati : %d  (%s)" % (len(altri), ", ".join(x.name for x in altri[:4])))
    fuori = sum(1 for r in nuovi if r["ts"] and not r["finestra"])
    if fuori:
        print("  fuori dalle finestre note  : %d  (la finestra nuova va aggiunta a FINESTRE in tools/catalogo.py)"
              % fuori)
    if not nuovi:
        print("\n  nulla di nuovo")
        return 0

    schermate = [r["nome_originale"] for r in nuovi
                 if r["dispositivo"] == "S25U" and r["tipo"] == "schermata" and not r["app"]]
    print()
    if schermate:
        passo("lettura locale delle schermate S25 Ultra",
              [str(BASE / "tools" / "leggi-schermate.py"), "--nome",
               "ingest-" + datetime.datetime.now().strftime("%Y%m%d-%H%M"), "--file"] + schermate)

    # sessioni nuove che non hanno ancora una lettura trascritta in data/
    trascritte = set()
    for f in glob.glob(str(P.DATI / "finestra*-letture.jsonl")):
        trascritte |= {json.loads(l)["ts"][:16] for l in io.open(f, encoding="utf-8") if l.strip()}
    sess = sorted({r["sessione"] for r in C.carica() if r["nome_originale"] in schermate and r["sessione"]})
    da_fare = [s for s in sess if "%s-%s-%s %s:%s" % (s[:4], s[4:6], s[6:8], s[9:11], s[11:13]) not in trascritte]
    print("\n  sessioni nuove da trascrivere: %d" % len(da_fare))
    for s in da_fare[:12]:
        print("    %s" % s)
    if len(da_fare) > 12:
        print("    ... e altre %d" % (len(da_fare) - 12))
    print("\n  Bozza e foglio dei ritagli dubbi sono in caso/lavorazione/bozze/. Trascritte le letture in")
    print("  data/finestra%d-letture.jsonl, si rigenera tutto con: python tools/aggiorna.py" % finestra_corrente())
    return 0


# --------------------------------------------------------------------------- build
def build():
    n = finestra_corrente()
    print("Rigenerazione completa, finestra %d\n" % n)
    if n != 4:
        print("  ATTENZIONE: tools/genera-grafici.py legge i file finestra4-*.")
        print("  Per la finestra %d va parametrizzato prima di procedere.\n" % n)

    passo("frammenti grafici e tabellari", [str(BASE / "tools" / "genera-grafici.py")])
    passo("documento della finestra", [str(BASE / "tools" / "genera-aggiornamento.py")])
    if eseguibile("genera-reperti.py"):
        passo("galleria dei reperti", [str(BASE / "tools" / "genera-reperti.py")])
    if eseguibile("genera-appendici.py"):
        passo("appendici del report", [str(BASE / "tools" / "genera-appendici.py")], obbligatorio=False)

    md2html = str(BASE / "tools" / "md-to-html.py")
    for d in (P.CONSEGNA, P.FASCICOLO):
        for m in sorted(d.glob("*.md")):
            if m.stem == "AGGIORNAMENTO-2026-08":
                continue        # gia' composto, con i frammenti innestati
            passo("pagina %s" % m.name, [md2html, str(m), "--out", str(m.with_suffix(".html"))])

    passo("stampa in PDF di tutti i documenti", [str(BASE / "tools" / "genera-pdf.py")])
    print()
    return verifica()


# --------------------------------------------------------------------------- verifica
def verifica():
    print("Controlli\n")
    errori = []

    def chk(nome, ok, dettaglio=""):
        print("  %-46s %s%s" % (nome, "ok" if ok else "FALLITO", "   " + dettaglio if dettaglio else ""))
        if not ok:
            errori.append(nome)

    # 1. segnaposto non risolti
    resti = []
    for h in glob.glob(str(P.CONSEGNA / "*.html")) + glob.glob(str(P.FASCICOLO / "*.html")):
        if "[[" in io.open(h, encoding="utf-8").read():
            resti.append(os.path.basename(h))
    chk("nessun segnaposto non risolto", not resti, ", ".join(resti))

    # 2. percorsi citati nei documenti
    pat = re.compile(r'`((?:caso|consegna|fascicolo|data|tools|fonti|media|lavorazione)/[A-Za-z0-9_.\-*/]+)`')
    rotti = []
    for f in (glob.glob(str(BASE / "*.md")) + glob.glob(str(P.CONSEGNA / "*.md"))
              + glob.glob(str(P.FASCICOLO / "*.md"))):
        for m in set(pat.findall(io.open(f, encoding="utf-8").read())):
            if not any((r / m).exists() or glob.glob(str(r / m)) or (r / os.path.dirname(m)).is_dir()
                       for r in (BASE, P.CASO)):
                rotti.append("%s in %s" % (m, os.path.basename(f)))
    chk("percorsi citati tutti esistenti", not rotti, "; ".join(rotti[:3]))

    # 3. PDF presenti e non piu' vecchi del proprio HTML
    vecchi, mancanti = [], []
    for h in glob.glob(str(P.CONSEGNA / "*.html")) + glob.glob(str(P.FASCICOLO / "*.html")):
        p = h[:-5] + ".pdf"
        if not os.path.exists(p):
            mancanti.append(os.path.basename(p))
        elif os.path.getmtime(p) < os.path.getmtime(h) - 2:
            vecchi.append(os.path.basename(p))
    chk("un PDF per ogni pagina", not mancanti, ", ".join(mancanti))
    chk("nessun PDF piu' vecchio del suo HTML", not vecchi, ", ".join(vecchi))

    # 4. i PDF sono file leggibili e non troncati
    corrotti = []
    for p in glob.glob(str(P.CONSEGNA / "*.pdf")) + glob.glob(str(P.FASCICOLO / "*.pdf")):
        b = io.open(p, "rb").read(5)
        if b != b"%PDF-" or os.path.getsize(p) < 4096:
            corrotti.append(os.path.basename(p))
    chk("PDF integri", not corrotti, ", ".join(corrotti))

    # 5. dati personali nei documenti che vanno a terzi
    trovati = []
    for f in glob.glob(str(P.CONSEGNA / "*.md")):
        if os.path.basename(f) not in A_LUOGHI_CODIFICATI:
            continue
        t = io.open(f, encoding="utf-8").read()
        for v in VIETATI:
            if re.search(v, t, re.I):
                trovati.append("%s in %s" % (v, os.path.basename(f)))
    chk("luoghi codificati dove previsto", not trovati, "; ".join(trovati[:3]))

    # 6. stile della documentazione
    fuori = []
    for f in glob.glob(str(P.CONSEGNA / "*.md")) + glob.glob(str(P.FASCICOLO / "*.md")):
        if os.path.basename(f) in STILE_ESCLUSI:
            continue
        t = io.open(f, encoding="utf-8").read()
        corpo = re.sub(r"^\|.*$", "", t, flags=re.M)          # le tabelle sono esenti
        if "—" in t:
            fuori.append("trattino lungo in " + os.path.basename(f))
        if re.findall(r"\*\*[^*]+\*\*", corpo):
            fuori.append("grassetto nella prosa di " + os.path.basename(f))
        if re.findall(r"^[-*] ", corpo, re.M):
            fuori.append("elenco puntato in " + os.path.basename(f))
    chk("stile conforme alla regola del progetto", not fuori, "; ".join(fuori[:3]))

    # 8. catalogo dei media: ogni file a catalogo e viceversa, nessun doppione, hash corrispondenti
    import random
    righe = C.carica()
    su_disco = {x.relative_to(C.MEDIA).as_posix() for x in C.MEDIA.rglob("*")
                if x.is_file() and x != C.CATALOGO and ARRIVO not in x.parents} if C.MEDIA.is_dir() else set()
    a_catalogo = {r["file"] for r in righe}
    difetti = []
    if su_disco - a_catalogo:
        difetti.append("%d file fuori catalogo" % len(su_disco - a_catalogo))
    if a_catalogo - su_disco:
        difetti.append("%d righe senza file" % len(a_catalogo - su_disco))
    hash_ = [r["sha256"] for r in righe]
    if len(set(hash_)) != len(hash_):
        difetti.append("%d contenuti doppi" % (len(hash_) - len(set(hash_))))
    for r in random.sample(righe, min(20, len(righe))):
        p = C.MEDIA / r["file"]
        if p.exists() and C.sha256(p) != r["sha256"]:
            difetti.append("hash diverso: " + r["file"])
    chk("catalogo dei media coerente", not difetti, "; ".join(difetti[:3]))

    print()
    if errori:
        print("ESITO: %d controlli falliti" % len(errori))
        return 1
    print("ESITO: progetto allineato e coerente")
    return 0


def main():
    a = sys.argv[1:]
    if a and a[0] == "ingest":
        resto = [x for x in a[1:] if not x.startswith("--")]
        return ingest(resto[0] if resto else None, "--sposta" in a) or 0
    if a and a[0] == "verifica":
        return verifica()
    return build()


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Produce i frammenti grafici e tabellari della finestra 4 a partire dai dati in data/.

Non compone una pagina: esporta grafici SVG inline, reperti fotografici incorporati come data URI
e tabelle in `_lavorazione/frammenti-finestra4.json`, che `genera-aggiornamento.py` innesta
nell'HTML dell'aggiornamento. E' la ragione per cui esiste un solo documento per finestra invece
di due che dicono le stesse cose.

Rigenerazione: python tools/genera-grafici.py
"""
import os, io, json, csv, datetime, html, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import privato  # noqa: E402
import percorsi  # noqa: E402

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATI = str(percorsi.DATI)

rec = [json.loads(l) for l in io.open(os.path.join(DATI, "finestra4-letture.jsonl"), encoding="utf-8") if l.strip()]
rec.sort(key=lambda r: r["ts"])
luoghi = json.load(io.open(os.path.join(DATI, "finestra4-luoghi.json"), encoding="utf-8"))
pacchi = json.load(io.open(os.path.join(DATI, "finestra4-pacchi.json"), encoding="utf-8"))
for r in rec:
    r["dt"] = datetime.datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")

SER_A = pacchi["slot_A"]["serie"]
SER_B = pacchi["slot_B"]["serie"]
SER_X = pacchi["rimosso"]["serie"]

# ---------------------------------------------------------------- CSV
COLS = ["sessione", "ts", "stato", "soc_medio_pct", "autonomia_km", "a_pct", "b_pct",
        "temp_a_c", "temp_b_c", "cicli_a", "cicli_b", "km_totali", "spare_pct",
        "uso_30gg_pct", "consumo_pct_km", "ultima_ricarica", "posizione",
        "ultimo_tragitto_km", "ultimo_tragitto_durata", "note"]
with io.open(os.path.join(DATI, "finestra4-letture.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(COLS + ["delta_a_meno_b"])
    for r in rec:
        d = (r["a_pct"] - r["b_pct"]) if (r["a_pct"] is not None and r["b_pct"] is not None) else None
        w.writerow([r.get(c) if r.get(c) is not None else "" for c in COLS] + ["" if d is None else d])

trag = []
for r in rec:
    t = r.get("tragitto")
    if not t:
        continue
    t = dict(t)
    t["sessione"] = r["sessione"]
    t["giorno"] = r["ts"][:10]
    t["pct_per_km"] = round(t["cons_pct"] / t["km"], 2) if (t.get("cons_pct") and t.get("km")) else None
    trag.append(t)
trag.sort(key=lambda t: (t["giorno"], t["ora_inizio"]))
TC = ["giorno", "ora_inizio", "ora_fine", "da", "a", "km", "durata", "cons_pct", "pct_per_km", "vel_media_kmh", "sessione"]
with io.open(os.path.join(DATI, "finestra4-tragitti.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(TC)
    for t in trag:
        w.writerow([t.get(c) if t.get(c) is not None else "" for c in TC])

# ---------------------------------------------------------------- anomalie e soste
def anomalie(r):
    out = []
    if r["a_pct"] == 0 and (r["b_pct"] or 0) > 0:
        out.append(("A", "percentuale slot A a zero"))
    if r["b_pct"] == 0 and (r["a_pct"] or 0) > 0:
        out.append(("B", "percentuale slot B a zero"))
    if r["temp_a_c"] == 0:
        out.append(("A", "temperatura A a 0 gradi"))
    if r["temp_b_c"] == 0:
        out.append(("B", "temperatura B a 0 gradi"))
    if r["cicli_a"] == 0:
        out.append(("A", "conteggio cicli A a zero"))
    if r["cicli_b"] == 0:
        out.append(("B", "conteggio cicli B a zero"))
    return out

eventi = []
for r in rec:
    for slot, testo in anomalie(r):
        eventi.append({"dt": r["dt"], "ts": r["ts"], "slot": slot, "testo": testo})
anomali_dt = [r["dt"] for r in rec if anomalie(r)]

val = [r for r in rec if r["a_pct"] not in (None, 0) and r["b_pct"] not in (None, 0)]
soste = []
for p, q in zip(val, val[1:]):
    if q["km_totali"] != p["km_totali"]:
        continue
    ore = (q["dt"] - p["dt"]).total_seconds() / 3600
    if ore < 0.5:
        continue
    da, db = q["a_pct"] - p["a_pct"], q["b_pct"] - p["b_pct"]
    if da > 5 or db > 5:
        continue
    vicina = any(abs((a - q["dt"]).total_seconds()) < 4 * 3600 or
                 abs((a - p["dt"]).total_seconds()) < 4 * 3600 for a in anomali_dt)
    soste.append({"da": p, "a": q, "ore": ore, "d_a": da, "d_b": db,
                  "perdita": -min(da, db), "anomalia": vicina})

# ---------------------------------------------------------------- SVG
T0, T1 = rec[0]["dt"], rec[-1]["dt"]
SPAN = (T1 - T0).total_seconds()

def esc(s):
    return html.escape(str(s), quote=True)

def x_of(dt, x0, w):
    return x0 + w * ((dt - T0).total_seconds() / SPAN)

def giorni_ticks():
    d = T0.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
    out = []
    while d <= T1:
        out.append(d)
        d += datetime.timedelta(days=1)
    return out

def chart_soc(w=1120, h=380):
    x0, y0, pw, ph = 54, 30, w - 54 - 18, h - 30 - 46
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Andamento della carica dei due pacchi nel tempo" class="chart">' % (w, h)]
    for v in range(0, 101, 25):
        y = y0 + ph * (1 - v / 100.0)
        p.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (x0, y, x0 + pw, y))
        p.append('<text class="ax" x="%d" y="%.1f" text-anchor="end">%d%%</text>' % (x0 - 8, y + 4, v))
    for d in giorni_ticks():
        x = x_of(d, x0, pw)
        p.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%.1f"/>' % (x, y0, x, y0 + ph))
        p.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x, y0 + ph + 20, d.strftime("%d/%m")))
    def serie(key, cls, nome):
        pts = [(x_of(r["dt"], x0, pw), y0 + ph * (1 - r[key] / 100.0), r) for r in rec if r[key] is not None]
        seg, cur, prev = [], [], None
        for xx, yy, r in pts:
            if prev is not None and (r["dt"] - prev).total_seconds() > 20 * 3600:
                seg.append(cur); cur = []
            cur.append((xx, yy)); prev = r["dt"]
        seg.append(cur)
        for s in seg:
            if len(s) > 1:
                p.append('<polyline class="ln %s" points="%s"/>' % (cls, " ".join("%.1f,%.1f" % q for q in s)))
        for xx, yy, r in pts:
            p.append('<circle class="pt %s" cx="%.1f" cy="%.1f" r="4"><title>%s, %s %d per cento</title></circle>'
                     % (cls, xx, yy, esc(r["ts"][5:16]), nome, r[key]))
    serie("b_pct", "s2", "slot B")
    serie("a_pct", "s1", "slot A")
    for r in rec:
        for slot, testo in anomalie(r):
            if "percentuale" not in testo:
                continue
            p.append('<circle class="bad" cx="%.1f" cy="%.1f" r="8"><title>%s, %s</title></circle>'
                     % (x_of(r["dt"], x0, pw), y0 + ph, esc(r["ts"][5:16]), esc(testo)))
    p.append('<text class="lbl s1" x="%.1f" y="16">slot A, %s</text>' % (x0, SER_A))
    p.append('<text class="lbl s2" x="%.1f" y="16">slot B, %s</text>' % (x0 + 260, SER_B))
    p.append('<text class="lbl bad" x="%.1f" y="16">cerchio rosso: percentuale letta a zero</text>' % (x0 + 520))
    p.append("</svg>")
    return "".join(p)

def chart_delta(w=1120, h=260):
    dati = [(r, r["a_pct"] - r["b_pct"]) for r in val]
    x0, y0, pw, ph = 54, 18, w - 54 - 18, h - 18 - 46
    mx = max(abs(d) for _, d in dati) or 1
    mid = y0 + ph / 2
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Scarto di carica fra i due slot" class="chart">' % (w, h)]
    for v in (mx, mx / 2, 0, -mx / 2, -mx):
        y = mid - (ph / 2) * (v / mx)
        p.append('<line class="grid%s" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (" zero" if v == 0 else "", x0, y, x0 + pw, y))
        p.append('<text class="ax" x="%d" y="%.1f" text-anchor="end">%+d</text>' % (x0 - 8, y + 4, round(v)))
    bw = max(4, pw / (len(dati) * 1.6))
    for r, d in dati:
        x = x_of(r["dt"], x0, pw) - bw / 2
        hh = abs(d) / mx * (ph / 2)
        p.append('<rect class="bar %s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2"><title>%s, slot A %d per cento e slot B %d per cento, scarto %+d</title></rect>'
                 % ("pos" if d >= 0 else "neg", x, mid - hh if d >= 0 else mid, bw, max(hh, 1.5),
                    esc(r["ts"][5:16]), r["a_pct"], r["b_pct"], d))
    for dd in giorni_ticks():
        p.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x_of(dd, x0, pw), y0 + ph + 20, dd.strftime("%d/%m")))
    p.append('<text class="lbl pos" x="%d" y="%.1f" text-anchor="end">slot A piu carico</text>' % (x0 + pw, y0 + 12))
    p.append('<text class="lbl neg" x="%d" y="%.1f" text-anchor="end">slot B piu carico</text>' % (x0 + pw, y0 + ph - 2))
    p.append("</svg>")
    return "".join(p)

def chart_guasti(w=1120):
    lanes = [("A", "slot A, " + SER_A), ("B", "slot B, " + SER_B)]
    h = 24 + len(lanes) * 46 + 30
    x0, pw = 210, w - 210 - 18
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Cronologia delle anomalie di lettura per slot" class="chart">' % (w, h)]
    for i, (ln, etichetta) in enumerate(lanes):
        y = 24 + i * 46
        p.append('<rect class="lane" x="%d" y="%.1f" width="%.1f" height="30" rx="4"/>' % (x0, y, pw))
        p.append('<text class="ax r" x="%d" y="%.1f" text-anchor="end">%s</text>' % (x0 - 10, y + 20, esc(etichetta)))
        for e in eventi:
            if e["slot"] != ln:
                continue
            grave = "percentuale" in e["testo"]
            p.append('<rect class="ev %s" x="%.1f" y="%.1f" width="5" height="30" rx="2"><title>%s, %s</title></rect>'
                     % ("grave" if grave else "lieve", x_of(e["dt"], x0, pw) - 2.5, y, esc(e["ts"][5:16]), esc(e["testo"])))
    for dd in giorni_ticks():
        p.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x_of(dd, x0, pw), h - 8, dd.strftime("%d/%m")))
    p.append('<text class="lbl bad" x="%d" y="14">barra piena: percentuale a zero</text>' % x0)
    p.append('<text class="lbl mut" x="%d" y="14">barra chiara: temperatura o cicli a zero</text>' % (x0 + 290))
    p.append("</svg>")
    return "".join(p)

def chart_consumi(w=1120):
    d = sorted([t for t in trag if t["pct_per_km"]], key=lambda t: t["pct_per_km"], reverse=True)
    rowh, x0 = 26, 250
    h = 30 + rowh * len(d)
    pw = w - x0 - 245
    mx = max(t["pct_per_km"] for t in d)
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Consumo per chilometro di ogni tragitto" class="chart">' % (w, h)]
    for i, t in enumerate(d):
        y = 22 + i * rowh
        bw = pw * t["pct_per_km"] / mx
        p.append('<text class="ax r" x="%d" y="%.1f" text-anchor="end">%s %s  %s&#8594;%s</text>'
                 % (x0 - 10, y + 12, esc(t["giorno"][8:10] + "/" + t["giorno"][5:7]), esc(t["ora_inizio"]), esc(t["da"]), esc(t["a"])))
        p.append('<rect class="bar seq" x="%d" y="%.1f" width="%.1f" height="16" rx="4"><title>%s km in %s, %s per cento consumati, media %s km/h</title></rect>'
                 % (x0, y, bw, esc(t["km"]), esc(t["durata"]), esc(t["cons_pct"]), esc(t["vel_media_kmh"])))
        p.append('<text class="val" x="%.1f" y="%.1f">%.2f %%/km  &#183;  %s km  &#183;  %s km/h</text>'
                 % (x0 + bw + 8, y + 12, t["pct_per_km"], t["km"], t["vel_media_kmh"]))
    p.append("</svg>")
    return "".join(p)

def chart_soste(w=1120):
    d = sorted(soste, key=lambda s: s["perdita"], reverse=True)
    rowh, x0 = 30, 250
    h = 46 + rowh * len(d)
    pw = w - x0 - 300
    mx = max(s["perdita"] for s in d) or 1
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Perdita di carica in sosta, per finestra" class="chart">' % (w, h)]
    p.append('<text class="lbl bad" x="%d" y="14">finestra con anomalia di lettura entro 4 ore</text>' % x0)
    p.append('<text class="lbl s1" x="%d" y="14">finestra senza anomalia</text>' % (x0 + 420))
    for i, s in enumerate(d):
        y = 34 + i * rowh
        bw = max(pw * s["perdita"] / mx, 2)
        p.append('<text class="ax r" x="%d" y="%.1f" text-anchor="end">%s &#8594; %s</text>'
                 % (x0 - 10, y + 12, esc(s["da"]["ts"][5:16]), esc(s["a"]["ts"][11:16])))
        p.append('<rect class="bar %s" x="%d" y="%.1f" width="%.1f" height="16" rx="4"><title>%.1f ore di sosta, slot A %+d e slot B %+d punti</title></rect>'
                 % ("crit" if s["anomalia"] else "seq", x0, y, bw, s["ore"], s["d_a"], s["d_b"]))
        p.append('<text class="val" x="%.1f" y="%.1f">%d punti in %.1f h  &#183;  A %+d  B %+d</text>'
                 % (x0 + bw + 8, y + 12, s["perdita"], s["ore"], s["d_a"], s["d_b"]))
    p.append("</svg>")
    return "".join(p)

# ---------------------------------------------------------------- statistiche
km_tot = [r["km_totali"] for r in rec if r["km_totali"]]
km_perc = max(km_tot) - min(km_tot)
tt = [t for t in trag if t["cons_pct"]]
km_t = sum(t["km"] for t in tt)
pct_t = sum(t["cons_pct"] for t in tt)
cons_medio = pct_t / km_t
vel = [t["vel_media_kmh"] for t in trag if t.get("vel_media_kmh")]
regime = [r for r in val if r["dt"] > datetime.datetime(2026, 8, 14, 18, 0)]
dd = [r["a_pct"] - r["b_pct"] for r in regime]
n_zero = sum(1 for d in dd if d == 0)
n_uno = sum(1 for d in dd if abs(d) <= 1)
n_pos = sum(1 for d in dd if d > 0)
n_neg = sum(1 for d in dd if d < 0)
ore_sosta = sum(s["ore"] for s in soste)
perdita_sosta = sum(s["perdita"] for s in soste)
gravi = [s for s in soste if s["perdita"] >= 3]
lunghe = [s for s in soste if s["ore"] >= 8 and s["perdita"] <= 1]
ep_a = sum(1 for e in eventi if e["slot"] == "A" and "percentuale" in e["testo"])
ep_b = sum(1 for e in eventi if e["slot"] == "B" and "percentuale" in e["testo"])

def tile(v, lab, sub=""):
    return '<div class="tile"><div class="v">%s</div><div class="l">%s</div>%s</div>' % (
        v, esc(lab), '<div class="s">%s</div>' % esc(sub) if sub else "")

def tab(th, righe):
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
        "".join("<th>%s</th>" % esc(x) for x in th), "".join(righe))

def tab_letture():
    righe = []
    for r in rec:
        d = (r["a_pct"] - r["b_pct"]) if (r["a_pct"] is not None and r["b_pct"] is not None) else None
        c = lambda v: "" if v is None else esc(v)
        righe.append("<tr class='%s'>%s</tr>" % (
            "warn" if anomalie(r) else "",
            "".join("<td>%s</td>" % x for x in [
                esc(r["ts"][:16]), c(r["stato"]), c(r["a_pct"]), c(r["b_pct"]),
                "" if d is None else "%+d" % d, c(r["soc_medio_pct"]), c(r["autonomia_km"]),
                c(r["temp_a_c"]), c(r["temp_b_c"]), c(r["cicli_a"]), c(r["cicli_b"]),
                c(r["km_totali"]), c(r["spare_pct"]), c(r["posizione"])])))
    return tab(["Data e ora", "Stato", "A %", "B %", "Scarto", "Media %", "Autonomia km",
                "T A", "T B", "Cicli A", "Cicli B", "km tot", "Riserva %", "Luogo"], righe)

def tab_tragitti():
    righe = ["<tr>%s</tr>" % "".join("<td>%s</td>" % x for x in [
        esc(t["giorno"]), "%s&ndash;%s" % (esc(t["ora_inizio"]), esc(t["ora_fine"])), esc(t["da"]), esc(t["a"]),
        esc(t["km"]), esc(t["durata"]), "" if t["cons_pct"] is None else esc(t["cons_pct"]),
        "" if t["pct_per_km"] is None else "%.2f" % t["pct_per_km"], esc(t.get("vel_media_kmh", ""))]) for t in trag]
    return tab(["Giorno", "Orario", "Da", "A", "km", "Durata", "Cons. %", "%/km", "km/h"], righe)

def tab_note():
    return tab(["Data e ora", "Sessione", "Osservazione"],
               ["<tr><td>%s</td><td>%s</td><td class='w'>%s</td></tr>" % (esc(r["ts"][:16]), esc(r["sessione"]), esc(r["note"]))
                for r in rec if r["note"]])

def tab_luoghi():
    return tab(["Codice", "Descrizione"],
               ["<tr><td>%s</td><td class='w'>%s</td></tr>" % (esc(k), esc(v))
                for k, v in sorted(luoghi.items()) if not k.startswith("_")])

def tab_soste():
    righe = []
    for s in sorted(soste, key=lambda s: s["da"]["ts"]):
        righe.append("<tr class='%s'>%s</tr>" % (
            "warn" if s["anomalia"] else "",
            "".join("<td>%s</td>" % x for x in [
                esc(s["da"]["ts"][:16]), esc(s["a"]["ts"][5:16]), "%.1f" % s["ore"],
                "%+d" % s["d_a"], "%+d" % s["d_b"], "si" if s["anomalia"] else "no"])))
    return tab(["Inizio sosta", "Fine sosta", "Ore", "Slot A", "Slot B", "Anomalia entro 4 h"], righe)

def tab_pacchi():
    righe = []
    for k in ("slot_A", "slot_B", "rimosso"):
        v = pacchi[k]
        righe.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='w'>%s</td></tr>" % (
            esc(v["serie"]), esc(v["posizione"]), esc(v["cicli"]), esc(v["proprieta"]), esc(v["nota"])))
    return tab(["Numero di serie", "Posizione nella finestra", "Cicli", "Proprieta", "Nota"], righe)

def img_b64(nome, alt):
    """Incorpora un reperto come data URI, per tenere il report autonomo."""
    import base64
    import sys
    sys.path.insert(0, os.path.join(BASE, "tools"))
    import catalogo
    q = str(catalogo.trova(nome_reperto(nome)))
    with io.open(q, "rb") as fh:
        b = base64.b64encode(fh.read()).decode("ascii")
    return '<figure><img src="data:image/jpeg;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>' % (b, esc(alt), esc(alt))

REPERTI = [
    ("01", "20260814_101552.mp4", "25,0 s",
     "Cruscotto alle 10:16: codice 165 con icona di avviso, MODE E-SAVE, due indicatori di batteria a quattro tacche piene, 99 per cento, 06923 km, 0 km/h"),
    ("02", "20260814_101552.mp4", "27,0 s",
     "Stesso codice 165, inquadratura piu ampia"),
    ("03", "20260814_101552.mp4", "4,5 s",
     "I due pacchi nel vano, con etichetta adesiva scritta a mano e cavo di collegamento"),
    ("04", "20260814_111821.mp4", "4,0 s",
     "Pacco del proprietario, etichetta a mano con il suo nome"),
    ("05", "20260814_100924.mp4", "20,0 s",
     "Cruscotto con 06923 km, conferma del chilometraggio di quella mattina"),
    ("06", "20260814_143545.mp4", "4,0 s",
     "Transitorio di accensione del display: contachilometri ancora a 00000 km. Non e un guasto"),
    ("07", "20260814_143545.mp4", "20,2 s",
     "Secondo transitorio di accensione nello stesso filmato"),
    ("08", "20260816_180352.mp4", "0,7 s",
     "Vano con i due pacchi alloggiati; solo quello di sinistra porta l etichetta adesiva scritta a mano"),
    ("09", "20260816_151453.mp4", "2,3 s",
     "99 per cento e 06961 km, orologio ancora a 00:00 perche il display si e appena acceso"),
    ("10", "20260814_141413.mp4", "6,0 s",
     "Display a regime: 74 per cento e 06947 km, gli stessi valori registrati dall app alle 14:11"),
]

def nome_reperto(numero):
    """Nome del file del reperto dal suo numero: i nomi stanno nel catalogo, non qui."""
    import sys
    sys.path.insert(0, os.path.join(BASE, "tools"))
    import catalogo
    for r in catalogo.carica():
        if r["ruolo"] == "reperto" and r["nome_originale"].startswith(numero + "_"):
            return r["nome_originale"]
    return numero

def tab_reperti():
    return tab(["File", "Video di origine", "Istante", "Cosa mostra"],
               ["<tr><td>%s</td><td>%s</td><td>%s</td><td class='w'>%s</td></tr>" % (esc(nome_reperto(a)), esc(b), esc(c), esc(d))
                for a, b, c, d in REPERTI])

EPISODI = [
    ("A e B insieme", "entrambi", "14/08 14:09", "14/08 14:11", "3 minuti"),
    ("B", SER_B, "16/08 15:45", "16/08 17:14", "89 minuti"),
    ("A", SER_A, "17/08 08:41", "17/08 10:05", "83 minuti"),
    ("A", SER_A, "20/08 23:30", "22/08 12:59", "37,5 ore, sbloccato estraendo i pacchi"),
    ("B", SER_B, "22/08 17:09", "22/08 18:21", "73 minuti"),
    ("B", SER_B, "23/08 17:09", "23/08 17:41", "32 minuti"),
    ("A", SER_A, "24/08 19:47", "24/08 20:05", "18 minuti"),
]

def tab_episodi():
    return tab(["Slot", "Pacco", "Prima lettura a zero", "Prima lettura di rientro", "Durata massima osservabile"],
               ["<tr>%s</tr>" % "".join("<td>%s</td>" % esc(x) for x in e) for e in EPISODI])

RICHIESTE = [
    ("Decodifica del codice 165 con lo strumento diagnostico ufficiale, con la definizione secondo il costruttore e l albero diagnostico previsto",
     "il codice e documentato dai reperti del 14 agosto ma non compare nella lista di 46 voci alle pagine 107 e 108 del manuale V1.0.0",
     "definizione ufficiale, albero diagnostico e versione firmware che lo genera"),
    ("Verbalizzazione della prova del 14 agosto 2026 con i pacchi sostitutivi: numeri di serie dei due pacchi provati, corrispondenza con le etichette dei filmati, codice mostrato e se il veicolo si sia avviato",
     "il mancato avviamento e finora soltanto riferito, e i reperti mostrano il codice ma non l esito",
     "dichiarazione firmata con i numeri di serie"),
    ("Prova prolungata a riposo con entrambi i pacchi del proprietario assenti dal veicolo, su almeno 48 ore continuative",
     "separa la responsabilita' del veicolo da quella dei pacchi", "risposta binaria: se il crollo si ripresenta, la causa e' nel veicolo"),
    ("Misura della corrente totale di batteria a riposo, non solo a regime ma durante e subito dopo un episodio di perdita di lettura",
     "in questa finestra le perdite a riposo si concentrano attorno agli episodi", "confronto con la soglia di 0,5 A dell'albero del codice 12, p. 109"),
    ("Misura della differenza di tensione fra le celle su entrambi i pacchi con strumento H1",
     "e' una delle due misure che autorizzano da sole la sostituzione", "soglia di 50 mV, albero del codice 11, p. 109"),
    ("Lettura della memoria errori con strumento ufficiale, inclusi i codici a tre cifre non visibili a display",
     "i codici 121, 122, 134, 154 e 191 sono direttamente pertinenti", "presenza o assenza in memoria, p. 107"),
    ("Verifica dei contatti e dei connettori di entrambi gli alloggiamenti e del cablaggio verso il BCS",
     "il guasto e' simmetrico sui due slot, quindi a monte dei pacchi", "continuita' e assenza di ossidazione, p. 57"),
    ("Verbalizzazione scritta dell'esito del test condotto prima del 14 agosto con due pacchi nuovi",
     "il fatto e' finora soltanto riferito a voce", "dichiarazione con i numeri di serie dei pacchi provati"),
    ("Annotazione a verbale del numero di serie presente in ciascun alloggiamento, con fotografia dei contatti",
     "e' la prima finestra in cui i due pacchi sono di proprieta' diversa", "tracciabilita' della configurazione"),
]

def tab_richieste():
    return tab(["Verifica richiesta", "Motivo", "Esito atteso"],
               ["<tr><td class='w'>%s</td><td class='w'>%s</td><td class='w'>%s</td></tr>" % (esc(a), esc(b), esc(c))
                for a, b, c in RICHIESTE])

kpi = "".join([
    tile("%d km" % km_perc, "percorsi nella finestra", "contachilometri da %d a %d" % (min(km_tot), max(km_tot))),
    tile("%.2f" % cons_medio, "punti al chilometro in marcia", "su %.1f km con dato completo" % km_t),
    tile("7", "episodi di lettura persa", "%d sullo slot A, %d sullo slot B, 1 su entrambi" % (ep_a, ep_b)),
    tile("%d punti" % perdita_sosta, "persi in %.1f h di sosta" % ore_sosta, "%.1f punti ogni 24 ore" % (perdita_sosta / ore_sosta * 24)),
    tile("%d su %d" % (n_uno, len(regime)), "letture con scarto entro 1 punto", "%d esattamente coincidenti" % n_zero),
    tile("%.1f km/h" % (sum(vel) / len(vel)), "velocita' media sui tragitti", "da %.1f a %.1f" % (min(vel), max(vel))),
])

P = {}
P["intro"] = u"Questa relazione copre i dodici giorni compresi fra il 13 e il 25 agosto 2026, cioe' il periodo immediatamente successivo alla sostituzione di uno dei due pacchi batteria avvenuta presso il centro assistenza la mattina del 14 agosto. E' un aggiornamento del quadro esposto nel report di diagnosi del 4 agosto 2026 e ne va letta insieme: il documento completo, con la storia dei tredici mesi precedenti e il riferimento agli alberi diagnostici del manuale d'officina, resta quello."

P["sintesi"] = u"Il risultato principale di questa finestra e' che la sostituzione del pacco sospetto non ha eliminato il problema. Con la " + privato.dato("pacco_439") + " rimossa dal veicolo e inviata in assistenza, e con un pacco di provenienza diversa al suo posto, due dei tre fenomeni descritti nel report si sono ripresentati identici, e uno dei due ha colpito anche il pacco che non ha alcuna storia su questo mezzo. Il terzo fenomeno, lo squilibrio progressivo fra i due pacchi, e' invece scomparso insieme al pacco a cui era stato attribuito."

P["sintesi_165"] = u"A questo si aggiunge un fatto che il report del 4 agosto non poteva conoscere, documentato dai filmati girati in officina: la mattina del 14 agosto, con due pacchi sostitutivi del centro assistenza regolarmente rilevati e carichi al 99 per cento, il veicolo non si avviava e il cruscotto esponeva il codice 165. Due batterie estranee, viste e piene, non bastavano a farlo funzionare."

P["sintesi2"] = u"Ne segue una conclusione che cambia la direzione dell'intervento. Lo squilibrio era effettivamente proprio di quel pacco, e su questo il report del 4 agosto era corretto. Le perdite di lettura e il crollo di carica durante la sosta appartengono invece al veicolo, non ai pacchi, perche' sono rimasti a bordo quando il pacco sospetto se n'e' andato e colpiscono con la stessa frequenza un pacco estraneo. Nessuna sostituzione di batteria puo' risolverli."

P["sintesi3"] = u"Un elemento nuovo, che nei tredici mesi precedenti non era mai emerso, e' che i due fenomeni residui risultano temporalmente associati fra loro: le tre soste in cui la carica cala in modo rilevante hanno tutte un episodio di lettura anomala entro quattro ore, mentre le cinque soste lunghe e stabili non ne hanno nessuno. Il paragrafo 6 sviluppa questo punto, che e' anche quello su cui si concentra la prima delle verifiche richieste."

P["e165_a"] = u"Il piano concordato con il centro assistenza non era quello che poi si e realizzato. Prevedeva di mandare in assistenza entrambi i pacchi del proprietario, la " + privato.dato("pacco_439") + " e la " + privato.dato("pacco_168") + ", sostituendoli con due pacchi interi messi a disposizione dal centro, cosi che il mezzo restasse utilizzabile e l accertamento potesse procedere su tutte e due le batterie di proprieta. Il piano e fallito la mattina del 14 agosto, e la ragione e documentata dai filmati girati in quel momento."

P["e165_b"] = u"Il reperto qui sopra e il cruscotto ripreso alle 10:16. Espone contemporaneamente il numero 165 accanto a un icona di avviso nella riga superiore, la modalita <em>E-SAVE</em>, due indicatori di batteria entrambi pieni a quattro tacche su quattro, la carica complessiva al 99 per cento, il contachilometri a 06923 chilometri e la velocita a zero. Con quei pacchi montati il veicolo non si avviava."

P["e165_c"] = u"La lettura di questo reperto e il punto piu importante di tutta la relazione. I due pacchi montati erano visti dal sistema, erano riconosciuti come presenti ed erano carichi quasi al massimo: non si trattava quindi di una perdita di lettura come quelle descritte piu avanti, ne di carica insufficiente. Il veicolo aveva davanti a se due batterie regolarmente rilevate e piene, e si rifiutava comunque di funzionare esponendo un codice di errore. Se la causa dei problemi fosse nei pacchi, due pacchi estranei e carichi avrebbero fatto funzionare il mezzo."

P["e165_d"] = u"Il codice 165 non compare nella <em>Diagnostic Code List</em> del manuale d officina, che alle pagine 107 e 108 elenca quarantasei voci nella versione V1.0.0. In quella lista i codici della famiglia 13x riguardano la batteria 1, quelli della famiglia 15x la batteria 2 e quelli della famiglia 19x i guasti di comunicazione; della famiglia 16x compare soltanto il 161, definito <em>Remote lock</em>. Il valore 165 non e presente. Non e quindi possibile decodificarlo con la documentazione disponibile, ed e la prima delle verifiche richieste piu avanti. Il fatto stesso che il cruscotto esponga un codice assente dalla lista ufficiale rende necessaria la lettura della memoria errori con lo strumento del costruttore, perche significa che la documentazione disponibile non copre il repertorio effettivo del firmware installato."

P["e165_e"] = u"Va dichiarato con precisione cosa il reperto prova e cosa non prova. Prova che alle 10:16 del 14 agosto il cruscotto esponeva il numero 165 accanto a un icona di avviso, con due pacchi rilevati e carichi al 99 per cento complessivo. Che il numero sia un codice di errore e l interpretazione coerente con la sua posizione nell area di notifica del display, ma non e confermata da documentazione. Che il veicolo non si avviasse in quel momento e riferito dal proprietario e non e visibile nei fotogrammi: e uno dei punti che il centro assistenza puo mettere a verbale."

P["e165_f"] = u"Non e inoltre ricostruibile dai dati disponibili la sequenza esatta dei montaggi di quella mattina. Il registro eventi dell app segna due disconnessioni alle 09:25, l app dichiara nessuna batteria a bordo alle 10:05 con la sola alimentazione di riserva all 83 per cento, registra il primo utilizzo della " + privato.dato("pacco_135") + " alle 10:08, e alle 10:16 il cruscotto mostra due pacchi pieni con il codice 165. La prima lettura utile della coppia definitiva e delle 11:18. Quali due pacchi fossero effettivamente montati alle 10:16 e in quale ordine siano stati provati puo dirlo soltanto chi era presente. Nei filmati si vedono etichette adesive scritte a mano applicate ai pacchi, con il nome del proprietario seguito da 1 o da 2. Nel vano ripreso il 16 agosto uno solo dei due pacchi ne porta una: la lettura piu naturale e che siano etichettati i soli pacchi del proprietario, il che concorderebbe con l identificazione del paragrafo 3, ma resta un inferenza perche le etichette non sono numeri di serie e la corrispondenza non e documentata."

P["crus_a"] = u"Gli screenshot dell app sono la lettura di un secondo osservatore, non del veicolo. I filmati del pomeriggio del 14 agosto e del 16 agosto permettono per la prima volta di confrontare i due, e il confronto aggiunge un elemento che gli screenshot da soli non potevano dare."

P["crus_b"] = u"Il filmato delle 14:35 del 14 agosto riprende il cruscotto per ventiquattro secondi consecutivi e mostra letture che si alternano fra loro. In alcuni fotogrammi il display riporta 69 per cento e 06955 chilometri, coerente con l app. In altri, a pochi secondi di distanza e senza che nulla sia stato toccato, riporta 53 per cento con il contachilometri azzerato a 00000 km, e sedici secondi dopo 55 per cento con il contachilometri ancora azzerato."

P["crus_c"] = u"Due cose vanno notate separatamente. La prima e che un contachilometri che va a zero non e un dato di batteria: e il display che perde il valore ricevuto dalla centralina e mostra il proprio stato di riposo. La seconda, la piu rilevante, e che nello stesso istante in cui il cruscotto dichiara 53 e poi 55 per cento l app registra 69 per cento, con la scheda A al 73 e la scheda B al 66. I due osservatori dissentono di quattordici o sedici punti sulla carica dello stesso veicolo nello stesso momento, e non perche uno dei due misuri male, ma perche almeno uno dei due non sta ricevendo il dato aggiornato."

P["crus_d"] = u"Nello stesso senso va letto l orologio. Nel filmato delle 15:14 del 16 agosto segna 00:00 invece dell ora corrente, e in fotogrammi successivi della stessa ripresa mostra l ora giusta; nel filmato del 14 agosto alle 14:14 e invece corretto fin dal primo fotogramma. Un orologio che riparte da zero e poi si risincronizza e il comportamento di un modulo che ha perso l alimentazione o lo stato e lo ha recuperato, non quello di una batteria scarica."

P["crus_e"] = u"Due riprese forniscono infine conferme incrociate rassicuranti sul metodo seguito, perche mostrano che quando il sistema legge, legge bene. Il filmato delle 14:14 del 14 agosto riporta 74 per cento e 06947 chilometri, e l app alle 14:11 registra 74 per cento. Il filmato delle 15:14 del 16 agosto riporta 99 per cento e 06961 chilometri, coerente con i 6967 chilometri che l app registra alle 15:45 dopo un tragitto di circa sei chilometri. Le due fonti concordano dove entrambe funzionano, e questo dice che le discordanze osservate altrove sono guasti e non errori di trascrizione."

P["pacchi"] = u"La corrispondenza fra le etichette A e B dell'app e i numeri di serie non e' scritta da nessuna parte nell'interfaccia e va ricostruita. Lo strumento e' il conteggio cicli, che ogni pacco memorizza al proprio interno e che l'utente non puo' azzerare: la scheda B riporta 102 cicli il 14 agosto e 104 il 25, e prosegue quindi senza interruzione dai 101 cicli che la " + privato.dato("pacco_168") + " aveva il 3 agosto; la scheda A parte da 132 cicli, valore che nessun pacco mai montato su questo veicolo ha avuto, e corrisponde quindi al pacco entrato il 14 agosto. Va notato che questa mappatura inverte quella del periodo precedente, in cui la scheda A era la " + privato.dato("pacco_439") + ": le etichette designano l'alloggiamento, non il pacco."

P["pacchi2"] = u"Le date che l'app riporta sotto le voci <em>First Use</em> e <em>Last Use</em> vanno lette come date di registrazione sul veicolo corrente e non come date di primo o ultimo impiego reale: la nota in calce alla schermata lo precisa, e il valore del 21 luglio 2024 associato al pacco rimosso non va quindi interpretato come la data in cui ha smesso di essere usato, che e' invece il 13 o 14 agosto 2026."

P["soc"] = u"Ogni punto del grafico e' una lettura dell'app. I cerchi rossi lungo la linea di base segnalano le letture in cui uno dei due slot dichiara zero mentre l'altro e' regolarmente carico. Non sono scaricamenti: in tutti i casi il valore rientra da solo, senza ricarica, a un livello coerente con quello che il pacco aveva prima. Le due risalite verticali del 20 e del 24 agosto sono invece ricariche reali."

P["scarto"] = u"Escludendo le cinque letture della mattinata del 14 agosto, che appartengono al transitorio successivo al montaggio quando i due pacchi partivano da stati di carica molto diversi, restano %d letture di regime. In %d di queste le due percentuali coincidono esattamente e in %d lo scarto non supera il punto singolo. Il segno non e' costante: lo slot A e' piu' carico in %d letture e lo slot B in %d. E' il comportamento normale di una coppia sana, ed e' l'opposto di quanto il report del 4 agosto documentava nel periodo precedente, dove lo scarto aveva segno costante in tutte e ventidue le rilevazioni e cresceva nel tempo." % (len(regime), n_zero, n_uno, n_pos, n_neg)

P["scarto2"] = u"Le sole sette letture in cui lo scarto supera il punto cadono tutte fra il pomeriggio del 23 agosto e la mattina del 24, cioe' esattamente nella finestra in cui lo slot B ha subito due episodi di perdita di lettura. Non descrivono quindi una deriva progressiva ma un intorno di instabilita' attorno a un guasto di comunicazione. Fuori da quel pomeriggio lo scarto non supera mai il punto singolo."

P["letture"] = u"Sette episodi in dodici giorni, tre sul pacco del proprietario, tre sul pacco di provenienza esterna e uno su entrambi i pacchi insieme. La simmetria e' il dato piu' significativo: il pacco esterno non ha storia su questo veicolo, e che si guasti in lettura esattamente come l'altro e con la stessa frequenza non e' spiegabile come coincidenza."

P["letture2"] = u"La percentuale non e' l'unico campo a cadere. In diciannove rilevazioni almeno uno fra percentuale, temperatura e conteggio cicli risulta azzerato: la temperatura scende a zero gradi in otto letture, il conteggio cicli va a zero in tre, a volte mentre la percentuale resta valida. Sono i tre campi che il pacco trasmette al veicolo e cadono insieme o a gruppi. Delle celle degradate non possono in alcun modo produrre un conteggio cicli pari a zero: la firma e' quella di un canale di comunicazione intermittente."

P["letture3"] = u"Il quarto episodio merita attenzione a se'. E' l'unico che non si e' risolto spontaneamente: lo slot A resta a zero dalle 23:30 del 20 agosto fino almeno alle 09:19 del 21, e la lettura torna corretta soltanto il 22 agosto alle 12:59, dopo che i pacchi sono stati estratti e reinseriti a mano. Che l'estrazione fisica sblocchi la condizione e' un argomento a favore di un difetto di contatto piuttosto che di una condizione logica del firmware."

P["letture4"] = u"Un dettaglio di rilievo pratico immediato per chi guida il mezzo: durante un episodio la schermata iniziale dell'app ricalcola l'autonomia sul solo pacco che risponde, mentre la schermata <em>Battery</em> continua a esporre il valore pieno. Il 17 agosto le due schermate riportano 39 e 78 chilometri nello stesso momento, il 20 agosto 40 e 80. Durante un guasto il secondo numero non e' affidabile."

P["riposo"] = u"Le %.1f ore di sosta pura documentate in questa finestra, isolate col criterio del contachilometri invariato agli estremi, portano una perdita cumulata di %d punti percentuali, pari a %.1f punti ogni ventiquattro ore. Il confronto col periodo di agosto e settembre 2025 e' netto: la' 339 ore avevano prodotto un solo punto di perdita, cioe' 0,07 punti al giorno. Il comportamento a riposo, che il report definiva eccellente, in questa finestra non lo e' piu'." % (ore_sosta, perdita_sosta, perdita_sosta / ore_sosta * 24)

P["riposo2"] = u"La perdita non e' pero' distribuita, ed e' questo il punto. Tre soste, per complessive 15,1 ore, concentrano venti dei venticinque punti persi. Le restanti 81,7 ore ne perdono cinque. Cinque soste di almeno otto ore, per un totale di 71,8 ore, si chiudono con un punto di perdita o nessuno, esattamente come nel 2025. Il fenomeno resta quindi episodico e non continuo, e questo esclude un assorbimento parassita permanente."

P["riposo3"] = u"Tutte e tre le soste che perdono tre punti o piu' hanno un episodio di lettura anomala entro quattro ore da uno dei due estremi. Nessuna delle cinque soste lunghe e stabili ne ha uno. Tre su tre da un lato e zero su cinque dall'altro e' il primo elemento in tredici mesi di osservazione che collega i due fenomeni, che il report del 4 agosto teneva distinti, correttamente per lo stato delle conoscenze di allora."

P["riposo4"] = u"Va detto con precisione cosa questo dimostra e cosa non dimostra. Dimostra una correlazione temporale su un campione piccolo, otto finestre in tutto. Non dimostra un nesso causale, e la direzione stessa del nesso resta aperta: puo' darsi che la perdita di comunicazione impedisca all'elettronica di entrare in sospensione profonda e che il consumo derivi da questo, ma puo' anche darsi che i due fenomeni siano effetti paralleli di un unico difetto di contatto a monte, senza che l'uno causi l'altro. La verifica che discrimina fra le due letture e' la misura della corrente a riposo eseguita durante un episodio e non soltanto a regime, ed e' la seconda delle richieste al paragrafo 8."

P["riposo5"] = u"Un'obiezione va affrontata prima che la sollevi qualcun altro, perche' e' la sola che potrebbe svuotare il dato. Poiche' la percentuale mostrata dall'app e' una stima dello stato di carica e non una misura, una caduta di undici punti potrebbe non essere energia perduta ma soltanto una ristima del sistema di gestione della batteria dopo un errore di comunicazione. Tre elementi giocano contro questa lettura. Il primo e' che il valore non torna: dopo la sosta del 18 agosto la coppia resta a 49 e 50 per cento alle 21:13, alle 21:24 e ancora alle 09:30 del mattino seguente, mentre le letture erronee dei sette episodi rientrano tutte entro poche ore. Il secondo e' che la caduta e' simmetrica sui due pacchi, undici punti ciascuno, mentre una ristima erronea colpisce un pacco solo, ed e' esattamente cosi' che si comportano gli episodi di lettura persa. Il terzo e' che nella stessa finestra scende anche il livello dichiarato della batteria di servizio, da 95 a 88 per cento, che ha un sistema di gestione distinto: perche' anche quella cali occorre che una corrente sia effettivamente circolata."

P["riposo6"] = u"Sul piano quantitativo, undici punti su due pacchi da 1488 Wh nominali ciascuno corrispondono a circa 327 Wh in 9,7 ore, cioe' una potenza media dell'ordine di 34 W, che a 48 volt sono circa 0,7 ampere. E' un valore superiore alla soglia di 0,5 ampere che l'albero diagnostico del codice 12, a pagina 109 del manuale d'officina, indica come condizione per la sostituzione della batteria. Il calcolo assume che i punti percentuali siano proporzionali all'energia, il che e' vero soltanto in prima approssimazione, e va quindi preso come ordine di grandezza e non come misura. Ha pero' il pregio di mostrare che il fenomeno osservato cade nella regione che il costruttore stesso considera anomala, e che la misura prevista dal manuale e' quella giusta da eseguire."

P["consumi"] = u"Su %.1f chilometri coperti da %d tragitti con dato di consumo completo il rapporto fra punti consumati e chilometri percorsi e' di %.2f punti al chilometro. Il valore e' allineato a quelli delle tre finestre precedenti, che stavano fra 0,99 e 1,13, e conferma per la quarta volta consecutiva che non esiste degrado di capacita'. L'autonomia dichiarata a carica piena e' 91 chilometri il 20 agosto e 92 il 24, sovrapponibile ai valori storici." % (km_t, len(tt), cons_medio)

P["consumi2"] = u"La dispersione fra i singoli tragitti, che va da 0,49 a 2,28 punti al chilometro sui percorsi di almeno tre chilometri, e' interamente spiegata dal dislivello e non dalla velocita': i tragitti piu' costosi sono le salite verso l'abitato in collina, quelli piu' economici le discese verso la costa, e il tragitto piu' veloce del periodo, a 40,5 km/h di media, e' anche uno dei piu' efficienti. I valori oltre due punti al chilometro su percorsi inferiori al chilometro non sono significativi, perche' su distanze cosi' brevi la risoluzione di un punto percentuale domina il calcolo."

P["chiusura"] = u"Le sette verifiche seguenti sono quelle che i dati di questa finestra rendono pertinenti. Le nove richieste del paragrafo 11 del report del 4 agosto restano tutte valide e nessuna e' superata: queste si aggiungono. La prima e' la piu' importante perche' e' la sola a produrre una risposta binaria: tutte le altre descrivono uno stato, questa mette alla prova l'ipotesi. Se il veicolo, privo di entrambi i pacchi del proprietario e alimentato con pacchi di provenienza diversa, continua a perdere carica a riposo e a perdere la lettura dei pacchi, allora l'intervento va portato sul sistema di controllo delle batterie, sul cablaggio del vano e sui connettori degli alloggiamenti."

P["nota"] = u"I dati provengono da 228 screenshot dell'app raccolti fra il 13 e il 25 agosto 2026 e raggruppati in sessioni di cattura per prossimita' temporale, con soglia di 180 secondi. Le sessioni utili hanno prodotto le 57 rilevazioni di questa relazione. La trascrizione riga per riga sta in <code>dati/letture.jsonl</code>, le tabelle derivate in <code>dati/letture.csv</code> e <code>dati/tragitti.csv</code>, e gli script che le rigenerano in <code>tools/</code>. Gli stessi dati sono stati importati nel dossier principale del veicolo, che resta la fonte di verita' del caso."

P["nota2"] = u"I luoghi sono indicati con codici anonimi e una descrizione funzionale, perche' nessun indirizzo e' necessario alla diagnosi: la legenda e' fra le tabelle in fondo. I numeri di serie dei pacchi sono invece riportati per esteso, perche' sono l'oggetto stesso della verifica. Quindici riprese video effettuate presso il centro assistenza la mattina del 14 agosto e le fotografie del vano batterie non sono state esaminate, per assenza sulla macchina di uno strumento di estrazione dei fotogrammi, e restano disponibili nelle cartelle di origine."

HTML = u"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Finestra 13-25 agosto 2026 - comportamento dei due pacchi batteria</title>
<style>
:root{color-scheme:light;
 --bg:#f6f5f2; --surface:#fcfcfb; --line:#e3e1db; --grid:#eceae4;
 --ink:#0b0b0b; --ink2:#52514e; --ink3:#7c7a73;
 --s1:#2a78d6; --s2:#eb6834; --bad:#e34948; --seq:#2a78d6; --lane:#eceae4;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --bg:#111110; --surface:#1a1a19; --line:#2f2f2c; --grid:#292927;
 --ink:#fff; --ink2:#c3c2b7; --ink3:#8d8c84;
 --s1:#3987e5; --s2:#d95926; --bad:#e66767; --seq:#3987e5; --lane:#252523;}}
:root[data-theme="dark"]{color-scheme:dark;
 --bg:#111110; --surface:#1a1a19; --line:#2f2f2c; --grid:#292927;
 --ink:#fff; --ink2:#c3c2b7; --ink3:#8d8c84;
 --s1:#3987e5; --s2:#d95926; --bad:#e66767; --seq:#3987e5; --lane:#252523;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15.5px/1.62 Georgia,"Times New Roman",serif;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto;padding:36px 22px 90px}
h1{font-size:29px;line-height:1.22;margin:0 0 8px;font-weight:600;letter-spacing:-.01em}
h2{font-size:20px;margin:46px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line);font-weight:600}
p{margin:0 0 12px;color:var(--ink2);max-width:82ch;text-align:justify;hyphens:auto}
p.lead{color:var(--ink);font-size:16.5px}
.meta{color:var(--ink3);font-size:13px;margin:0 0 4px;font-family:ui-sans-serif,system-ui,sans-serif}
.dest{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--s2);
 border-radius:8px;padding:12px 16px;margin:18px 0 6px;font-size:13.5px;
 font-family:ui-sans-serif,system-ui,sans-serif;color:var(--ink2)}
.dest b{color:var(--ink);font-weight:600}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px;margin:22px 0 6px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px;
 font-family:ui-sans-serif,system-ui,sans-serif}
.tile .v{font-size:25px;font-weight:650;letter-spacing:-.02em;color:var(--ink)}
.tile .l{font-size:12px;color:var(--ink2);margin-top:2px;line-height:1.35}
.tile .s{font-size:11px;color:var(--ink3);margin-top:4px;line-height:1.35}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px;margin:14px 0;overflow-x:auto}
svg.chart{display:block;width:100%;min-width:720px;height:auto}
.grid{stroke:var(--grid);stroke-width:1}
.grid.zero{stroke:var(--ink3)}
.ax{fill:var(--ink3);font-size:11px;font-family:ui-sans-serif,system-ui,sans-serif}
.ax.r{fill:var(--ink2)}
.val{fill:var(--ink2);font-size:11px;font-family:ui-sans-serif,system-ui,sans-serif}
.lbl{font-size:12px;font-weight:600;font-family:ui-sans-serif,system-ui,sans-serif}
.lbl.s1{fill:var(--s1)} .lbl.s2{fill:var(--s2)} .lbl.pos{fill:var(--s1)}
.lbl.neg{fill:var(--bad)} .lbl.bad{fill:var(--bad)} .lbl.mut{fill:var(--ink3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.ln.s1{stroke:var(--s1)} .ln.s2{stroke:var(--s2)}
.pt{stroke:var(--surface);stroke-width:2}
.pt.s1{fill:var(--s1)} .pt.s2{fill:var(--s2)}
circle.bad{fill:none;stroke:var(--bad);stroke-width:2.5}
.bar.pos{fill:var(--s1)} .bar.neg{fill:var(--bad)} .bar.seq{fill:var(--seq)} .bar.crit{fill:var(--bad)}
.lane{fill:var(--lane)}
.ev.grave{fill:var(--bad)} .ev.lieve{fill:var(--ink3);opacity:.6}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:640px;
 font-family:ui-sans-serif,system-ui,sans-serif}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:top}
th{color:var(--ink3);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
td{color:var(--ink2)}
td.w{white-space:normal;max-width:420px}
tr.warn td{background:color-mix(in srgb,var(--bad) 9%,transparent)}
details{margin:10px 0}
summary{cursor:pointer;color:var(--ink2);font-size:13px;padding:6px 0;
 font-family:ui-sans-serif,system-ui,sans-serif}
code{background:var(--grid);padding:1px 5px;border-radius:4px;font-size:12.5px}
em{font-style:italic}
figure{margin:0}
figure img{display:block;width:100%;height:auto;border-radius:8px}
figcaption{color:var(--ink3);font-size:12px;margin-top:8px;font-family:ui-sans-serif,system-ui,sans-serif;line-height:1.45}
</style></head><body><div class="wrap">

<h1>Comportamento dei due pacchi batteria dal 13 al 25 agosto 2026</h1>
<p class="meta">__veicolo__ &middot; 57 rilevazioni ricavate da 228 schermate dell'app &middot; relazione del 26 agosto 2026</p>

<div class="dest"><b>Destinatario</b> __destinatario__<br>
<b>Documento di riferimento</b> report di diagnosi del 4 agosto 2026, consegnato il 5 agosto. Questa relazione ne aggiorna i paragrafi 6.2, 6.3, 9.1 e 10 e va letta insieme a esso.</div>

<p class="lead">__intro__</p>

<h2>1. In sintesi</h2>
<p>__sintesi__</p>
<p>__sintesi2__</p>
<p>__sintesi_165__</p>
<p>__sintesi3__</p>

<div class="kpi">__KPI__</div>

<h2>2. La prova del 14 agosto e il codice 165</h2>
<p>__e165_a__</p>
<div class="card">__IMG165__</div>
<p>__e165_b__</p>
<p>__e165_c__</p>
<p>__e165_d__</p>
<p>__e165_e__</p>
<p>__e165_f__</p>
<details><summary>Reperti estratti dai filmati, con file di origine e istante</summary><div class="card">__TREPERTI__</div></details>

<h2>3. I pacchi a bordo, e come sono stati identificati</h2>
<div class="card">__TPACCHI__</div>
<p>__pacchi__</p>
<p>__pacchi2__</p>

<h2>4. Andamento della carica dei due slot</h2>
<div class="card">__C1__</div>
<p>__soc__</p>

<h2>5. Lo scarto fra i due slot</h2>
<div class="card">__C2__</div>
<p>__scarto__</p>
<p>__scarto2__</p>

<h2>6. Le perdite di lettura</h2>
<div class="card">__C3__</div>
<div class="card">__TEPISODI__</div>
<p>__letture__</p>
<p>__letture2__</p>
<p>__letture3__</p>
<p>__letture4__</p>

<h2>7. Il guasto si vede anche sul cruscotto, non solo nell app</h2>
<p>__crus_a__</p>
<div class="card">__IMG00000__</div>
<p>__crus_b__</p>
<p>__crus_c__</p>
<p>__crus_d__</p>
<p>__crus_e__</p>

<h2>8. Il comportamento a riposo, e la correlazione con le perdite di lettura</h2>
<div class="card">__C5__</div>
<p>__riposo__</p>
<p>__riposo2__</p>
<p>__riposo3__</p>
<p>__riposo4__</p>
<p>__riposo5__</p>
<p>__riposo6__</p>
<div class="card">__TSOSTE__</div>

<h2>9. Il consumo dei tragitti</h2>
<div class="card">__C4__</div>
<p>__consumi__</p>
<p>__consumi2__</p>

<h2>10. Verifiche richieste</h2>
<p>__chiusura__</p>
<div class="card">__TRICHIESTE__</div>

<h2>11. Tabelle di dettaglio</h2>
<details><summary>Tutte le rilevazioni (__NREC__); le righe evidenziate contengono un'anomalia di lettura</summary><div class="card">__TL__</div></details>
<details><summary>Tutti i tragitti (__NTRAG__)</summary><div class="card">__TT__</div></details>
<details><summary>Osservazione per singola rilevazione</summary><div class="card">__TN__</div></details>
<details><summary>Legenda dei luoghi</summary><div class="card">__TG__</div></details>

<h2>12. Provenienza dei dati e riproducibilita'</h2>
<p>__nota__</p>
<p>__nota2__</p>

</div></body></html>"""

FRAMMENTI = {
    "grafico_soc":      chart_soc(),
    "grafico_scarto":   chart_delta(),
    "grafico_anomalie": chart_guasti(),
    "grafico_consumi":  chart_consumi(),
    "grafico_soste":    chart_soste(),
    "tabella_soste":    tab_soste(),
    "tabella_reperti":  tab_reperti(),
    "tabella_letture":  tab_letture(),
    "tabella_tragitti": tab_tragitti(),
    "tabella_luoghi":   tab_luoghi(),
    "reperto_165":      img_b64("01",
                                "Cruscotto del 14 agosto 2026 alle 10:16: codice 165, due pacchi rilevati e carichi al 99 per cento, contachilometri 06923 km"),
}

if __name__ == "__main__":
    out = str(percorsi.LAVORAZIONE / "frammenti-finestra4.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(FRAMMENTI, io.open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("rilevazioni %d | tragitti %d | soste %d | frammenti %d"
          % (len(rec), len(trag), len(soste), len(FRAMMENTI)))
    print("km percorsi %d | consumo %.2f punti/km | sosta %.1f h con %d punti persi"
          % (km_perc, cons_medio, ore_sosta, perdita_sosta))
    print("scritti: data/finestra4-letture.csv, data/finestra4-tragitti.csv, _lavorazione/frammenti-finestra4.json")

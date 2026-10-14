#!/usr/bin/env python3
"""Converte il report Markdown in una pagina HTML autosufficiente e stampabile.

Non usa dipendenze esterne: copre deliberatamente il solo sottoinsieme di
Markdown usato nel report, cioe' intestazioni, paragrafi, tabelle, righelli
orizzontali, corsivo, grassetto, codice inline e note a pie' di pagina. Il
foglio di stile e' incorporato e contiene le regole di stampa: formato A4,
interruzione di pagina prima di ogni capitolo, intestazioni di tabella
ripetute a ogni pagina e orientamento orizzontale per le tabelle larghe delle
appendici.
"""

import argparse
import html
import pathlib
import re

CSS = """
:root { --ink:#1a1a1a; --mute:#5c5c5c; --rule:#d4d4d4; --bg:#fff; --accent:#8a1c1c; }
* { box-sizing:border-box; }
body { margin:0 auto; padding:32px 28px 64px; max-width:960px; background:var(--bg);
  color:var(--ink); font:15px/1.62 Georgia,"Times New Roman",serif;
  font-variant-numeric:tabular-nums; }
h1 { font-size:1.85em; line-height:1.25; margin:0 0 .2em; font-weight:600; }
h1 + p { color:var(--mute); font-size:.95em; }
h2 { font-size:1.28em; margin:2.1em 0 .5em; padding-bottom:.22em;
  border-bottom:2px solid var(--rule); font-weight:600; }
h3 { font-size:1.06em; margin:1.5em 0 .35em; font-weight:600; color:#333; }
p { margin:0 0 .85em; text-align:justify; hyphens:auto; }
hr { border:0; border-top:1px solid var(--rule); margin:2em 0; }
code { font:.88em/1.4 "Consolas","DejaVu Sans Mono",monospace; background:#f2f2f0;
  padding:.08em .32em; border-radius:2px; word-break:break-word; }
em { font-style:italic; }
strong { font-weight:600; }
table { border-collapse:collapse; width:100%; margin:.9em 0 1.4em; font-size:.87em;
  font-family:"Helvetica Neue",Arial,sans-serif; }
th, td { border:1px solid var(--rule); padding:4px 7px; text-align:left;
  vertical-align:top; }
th { background:#f0efec; font-weight:600; font-size:.95em; }
tbody tr:nth-child(even) td { background:#fafaf8; }
table.wide { font-size:.68em; }
table.wide th, table.wide td { padding:2px 3px; }
.toc { background:#faf9f6; border:1px solid var(--rule); padding:14px 20px;
  margin:1.6em 0 2em; font-size:.93em; }
.toc h2 { border:0; margin:0 0 .4em; font-size:1.02em; }
.toc ol { margin:0; padding-left:0; list-style:none; }
.toc li { margin:.14em 0; }
.footnotes { margin-top:2.4em; padding-top:1em; border-top:1px solid var(--rule);
  font-size:.88em; color:#333; }
.footnotes ol { padding-left:1.4em; }
sup a { text-decoration:none; color:var(--accent); font-weight:600; }

@page { size:A4 portrait; margin:15mm 13mm; }
@page landscape { size:A4 landscape; margin:12mm 10mm; }

/* i motori di stampa scartano i colori di sfondo se non lo si dichiara: senza questa
   regola le tabelle perdono le righe e i grafici perdono le barre */
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
@media print {
  body { max-width:none; padding:0; font-size:10.2pt; line-height:1.48; }
  h1 { font-size:17pt; }
  h2 { font-size:12.6pt; break-before:page; break-after:avoid; }
  h1 + p + .toc + hr + h2, h2.first { break-before:auto; }
  h3 { break-after:avoid; font-size:11pt; }
  p, li { orphans:2; widows:2; }
  table { font-size:8.3pt; break-inside:auto; }
  thead { display:table-header-group; }
  tr, td, th { break-inside:avoid; }
  table.wide { font-size:6.4pt; page:landscape; }
  .toc { break-after:page; }
  a { color:inherit; text-decoration:none; }
}
"""


def inline(s, codes):
    s = html.escape(s, quote=False)
    def keep_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"
    s = re.sub(r"`([^`]+)`", keep_code, s)
    s = re.sub(r"\[\^(\w+)\]", r'<sup id="r\1"><a href="#fn\1">\1</a></sup>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00",
                  lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", s)


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]


def convert(md):
    lines = md.splitlines()
    notes, body, toc, codes = {}, [], [], []
    i, first_h2 = 0, True

    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^\[\^(\w+)\]:\s*(.+)$", ln)
        if m:
            notes[m.group(1)] = m.group(2)
            i += 1
            continue
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(set(c) <= set("-: ") and c for c in r)]
            if not rows:
                continue
            cls = ' class="wide"' if len(rows[0]) > 9 else ""
            out = [f"<table{cls}><thead><tr>"]
            out += [f"<th>{inline(c, codes)}</th>" for c in rows[0]]
            out.append("</tr></thead><tbody>")
            for r in rows[1:]:
                out.append("<tr>" + "".join(
                    f"<td>{inline(c, codes)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            body.append("".join(out))
            continue
        if re.match(r"^-{3,}$", ln.strip()):
            body.append("<hr>")
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2)
            sid = slug(txt)
            extra = ""
            if lvl == 2:
                toc.append((txt, sid))
                if first_h2:
                    extra, first_h2 = ' class="first"', False
            body.append(f'<h{lvl} id="{sid}"{extra}>{inline(txt, codes)}</h{lvl}>')
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("|", "#")) \
                and not re.match(r"^-{3,}$", lines[i].strip()) \
                and not re.match(r"^\[\^\w+\]:", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        body.append(f"<p>{inline(' '.join(buf), codes)}</p>")

    nav = ""
    if toc:
        items = "".join(f'<li><a href="#{s}">{html.escape(t)}</a></li>' for t, s in toc)
        nav = f'<nav class="toc"><h2>Indice</h2><ol>{items}</ol></nav>'

    fn = ""
    if notes:
        items = "".join(
            f'<li id="fn{k}">{inline(v, codes)} <a href="#r{k}">&#8617;</a></li>'
            for k, v in notes.items())
        fn = f'<section class="footnotes"><ol>{items}</ol></section>'

    title = next((re.sub(r"^#\s+", "", l) for l in lines if l.startswith("# ")), "Report")
    html_body = "\n".join(body)
    # l'indice si colloca dopo il primo blocco introduttivo
    k = html_body.find("<hr>")
    if k != -1:
        html_body = html_body[:k] + nav + html_body[k:]
    else:
        html_body = nav + html_body

    return (f'<!doctype html><html lang="it"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>"
            f"{html_body}{fn}</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", default="REPORT-DIAGNOSI.md")
    ap.add_argument("--out", default="REPORT-DIAGNOSI.html")
    a = ap.parse_args()
    src = pathlib.Path(a.source)
    out = pathlib.Path(a.out)
    out.write_text(convert(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"scritto {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

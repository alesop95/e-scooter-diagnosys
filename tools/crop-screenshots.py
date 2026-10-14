#!/usr/bin/env python3
"""Ritaglia gli screenshot dell'app NIU alla sola fascia che contiene i dati.

Vale per gli screenshot del telefono usato nel 2025, a 1080x2400; quelli del S25 Ultra, a
1440x3120, si leggono con `tools/leggi-schermate.py`, e qui vengono saltati. Le due schermate utili, "Veicolo" e
"Batteria", collocano i propri dati fra y=660 e y=2050: sopra c'e' la barra di
stato e l'intestazione, sotto la barra di navigazione. Il ritaglio elimina il
resto e riduce la larghezza, abbattendo il costo di lettura senza toccare i
valori. L'operazione e' locale e non consuma token.
"""

import argparse
import pathlib
import sys

from PIL import Image

TOP, BOTTOM = 660, 2050
OUT_WIDTH = 600
SKIP_MARKERS = ("_LinkedIn", "_Reddit")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="cartella con gli screenshot .jpg")
    ap.add_argument("--out", required=True, help="cartella di destinazione")
    ap.add_argument("--width", type=int, default=OUT_WIDTH)
    ap.add_argument("--top", type=int, default=TOP)
    ap.add_argument("--bottom", type=int, default=BOTTOM)
    args = ap.parse_args()

    src = pathlib.Path(args.source)
    dst = pathlib.Path(args.out)
    dst.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".avif"))
    written = skipped = 0

    for path in files:
        if any(m in path.name for m in SKIP_MARKERS):
            skipped += 1
            continue
        with Image.open(path) as im:
            if im.size != (1080, 2400):
                skipped += 1
                continue
            box = (0, args.top, im.width, min(args.bottom, im.height))
            crop = im.crop(box)
            if args.width and crop.width > args.width:
                ratio = args.width / crop.width
                crop = crop.resize(
                    (args.width, int(crop.height * ratio)), Image.LANCZOS
                )
            crop.convert("RGB").save(dst / (path.stem + ".jpg"), quality=90)
            written += 1

    print(f"sorgenti: {len(files)}")
    print(f"scritti:  {written}")
    print(f"esclusi:  {skipped}")
    print(f"output:   {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Extract NPC portraits from Google Docs "Web page (.html, zipped)" downloads of Corgo's NPC document.

    python3 tools/npc_art.py <download.zip> [<download.zip> ...] [--max 1024]
    python3 tools/npc_art.py --tokens      # only rebuild the tokens from the portraits already in art/

Needs Pillow (`pip install Pillow`), so it is not part of `npm run build`. Run `npm run parse` first: the
images are matched against data/npcs.parsed.json.

Each zip holds one HTML file and an images/ folder. In the HTML every portrait sits inside a clipping span: the doc shows a portrait-shaped window of a landscape image, set by
the span's size and the image's negative margins. This tool:

- maps each image to the heading that holds it (the export nests a portrait inside its NPC's `###`
  heading, ahead of the text), and that heading to an NPC by faction (the `##` heading) and title. An image followed by anything else ("SOLDIER VARIANTS") is reported, not guessed;
- applies the doc's crop, scaled from display pixels to the image's own, so the portrait is framed the way
  Corgo framed it;
- shrinks it to at most --max pixels on the long side (never enlarges) and writes it as WebP to
  npcs-module/art/;
- writes a square token beside it in npcs-module/art/tokens/: the top of the portrait, as wide as the
  portrait, because Foundry letterboxes a tall image inside a square token and every portrait has the head
  at the top (a centred crop, Foundry's "cover" fit, cuts many heads off);
- records the mapping in text/npc_art.json, merged with the entries already there, so zips can be added
  one faction at a time.

The zips are read in place, never extracted. Nothing reaches the actors until text/npc_art.json has
"enabled": true; see build_npcs.actor_art().
"""
import argparse, io, json, re, sys, zipfile
from html import unescape
from pathlib import Path

from PIL import Image

from common import dump_json
from build_npcs import norm

for _stream in (sys.stdout, sys.stderr):  # Windows consoles; see tools/common.py
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
PARSED = ROOT / "data/npcs.parsed.json"
MANIFEST = ROOT / "text/npc_art.json"
ART = ROOT / "npcs-module/art"
TOKENS = ART / "tokens"
TOKEN_SIZE = 512

HEADING = re.compile(r"<h([1-4])\b[^>]*>(.*?)</h\1>", re.S)
IMAGE = re.compile(r"<span style=\"([^\"]*)\"><img\b([^>]*)>", re.S)


def css(style, name):
    m = re.search(rf"(?<![\w-]){name}:\s*(-?[\d.]+)px", style)
    return float(m.group(1)) if m else 0.0


def image(span, attrs):
    src = unescape(re.search(r'src="([^"]+)"', attrs).group(1))
    style = unescape(re.search(r'style="([^"]*)"', attrs).group(1))
    if re.search(r"rotate\((?!0\.00rad)", style):
        print(f"  warning: {src} is rotated in the doc; the crop ignores rotation")
    return {"src": src, "span": (css(span, "width"), css(span, "height")),
            "shown": (css(style, "width"), css(style, "height")),
            "offset": (-css(style, "margin-left"), -css(style, "margin-top"))}


def events(html):
    """The document's headings and images, in order. The export puts a portrait inside its NPC's heading
    element, ahead of the heading's text, so an image is yielded just before the heading that holds it."""
    pos = 0
    for h in HEADING.finditer(html):
        for m in IMAGE.finditer(html, pos, h.start()):      # an image outside any heading
            yield "img", image(*m.groups())
        for m in IMAGE.finditer(h.group(2)):
            yield "img", image(*m.groups())
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", h.group(2)))).strip()
        yield "h" + h.group(1), text
        pos = h.end()
    for m in IMAGE.finditer(html, pos):
        yield "img", image(*m.groups())


def crop_box(img, size):
    """The doc's visible window of the image, in the image's own pixels."""
    sx, sy = size[0] / img["shown"][0], size[1] / img["shown"][1]
    x, y = img["offset"][0] * sx, img["offset"][1] * sy
    box = (max(0, round(x)), max(0, round(y)),
           min(size[0], round(x + img["span"][0] * sx)), min(size[1], round(y + img["span"][1] * sy)))
    return box


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write_token(im, name):
    """The top square of a portrait, as tokens/<name>; a landscape image keeps its middle instead."""
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    tok = im.crop((left, 0, left + side, side))
    tok.thumbnail((TOKEN_SIZE, TOKEN_SIZE), Image.LANCZOS)
    TOKENS.mkdir(parents=True, exist_ok=True)
    tok.save(TOKENS / name, "WEBP", quality=85, method=6)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("zips", nargs="*", type=Path)
    ap.add_argument("--max", type=int, default=1024, help="longest side of a portrait, in pixels")
    ap.add_argument("--tokens", action="store_true", help="rebuild every token from the portraits in art/")
    args = ap.parse_args()
    if args.tokens:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["art"].values():
            write_token(Image.open(ART / entry["file"]), entry["file"])
        print(f"{len(manifest['art'])} tokens written to {TOKENS.relative_to(ROOT)}")
        return
    if not args.zips:
        ap.error("give the doc's zips, or --tokens")

    npcs = {(norm(r["faction"]), norm(r["title"])): r for r in json.loads(PARSED.read_text(encoding="utf-8"))}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"enabled": False, "art": {}}
    ART.mkdir(parents=True, exist_ok=True)
    unmatched, done = [], []
    for path in args.zips:
        with zipfile.ZipFile(path) as z:
            page = next(n for n in z.namelist() if n.endswith(".html"))
            evs = list(events(z.read(page).decode("utf-8")))
            faction = None
            for i, (kind, val) in enumerate(evs):
                if kind == "h2":
                    faction = val
                if kind != "img":
                    continue
                nxt = next((e for e in evs[i + 1:] if e[0] != "img"), None)
                rec = npcs.get((norm(faction or ""), norm(nxt[1]))) if nxt and nxt[0] == "h3" else None
                if rec is None:
                    unmatched.append(f"{path.name}: {val['src']} precedes "
                                     + (f"{nxt[0]} {nxt[1]!r}" if nxt else "nothing") + f" in {faction!r}")
                    continue
                key = f"{rec['faction']}/{rec['title']}"
                if key in done:
                    unmatched.append(f"{path.name}: {val['src']} is a second image for {key}")
                    continue
                im = Image.open(io.BytesIO(z.read(val["src"])))
                box = crop_box(val, im.size)
                im = im.crop(box)
                im.thumbnail((args.max, args.max), Image.LANCZOS)
                if im.mode in ("RGBA", "LA", "P") and im.convert("RGBA").getchannel("A").getextrema()[0] == 255:
                    im = im.convert("RGB")
                name = f"{slug(rec['faction'])}-{slug(rec['title'])}.webp"
                im.save(ART / name, "WEBP", quality=85, method=6)
                write_token(im, name)
                manifest["art"][key] = {"file": name, "source": f"{path.name}:{val['src']}", "crop": list(box),
                                        "size": list(im.size)}
                done.append(key)
                print(f"  {key}: {val['src']} -> art/{name} {im.size[0]}x{im.size[1]}")
    manifest["art"] = dict(sorted(manifest["art"].items()))
    dump_json(MANIFEST, manifest)
    seen = {k.split("/")[0] for k in done}
    missing = [f"{r['faction']}/{r['title']}" for r in npcs.values()
               if r["faction"] in seen and f"{r['faction']}/{r['title']}" not in manifest["art"]]
    print(f"{len(done)} portraits written; {len(manifest['art'])} in {MANIFEST.relative_to(ROOT)}")
    for u in unmatched:
        print(f"  not used: {u}")
    for m in missing:
        print(f"  no portrait: {m}")


if __name__ == "__main__":
    main()

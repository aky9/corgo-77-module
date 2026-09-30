"""Shared helpers for building Corgo's 77 Collection item documents."""
import hashlib, html, json, re, sys

# Item names carry characters a legacy Windows console can't encode ("Ć", curly quotes, "♦"), and Python
# raises UnicodeEncodeError rather than mangling them, which killed the build mid-print. Ask for UTF-8 and
# fall back to replacing what the console can't show: a progress line is never worth failing a build over.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # not a real stream (redirected, or already wrapped)
        pass

MODULE_ID = "corgo-77-collection"
SOURCE_BOOK = "Corgo's 77 Collection V3"
# Corgo's public document (the original, not a personal copy)
SOURCE_URL = "https://docs.google.com/document/d/13EnSAoiLDsC7zmL-Jr1RqIh_EnuVuFnExqiipDVquMk/edit"

_B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def doc_id(kind, key):
    """Deterministic 16-character Foundry ID, so rebuilding the module keeps the same IDs."""
    n = int(hashlib.sha256(f"{MODULE_ID}:{kind}:{key}".encode()).hexdigest(), 16)
    out = ""
    for _ in range(16):
        n, r = divmod(n, 62)
        out += _B62[r]
    return out


ACRONYMS = {"AP", "CBT", "CT", "DAS", "DB", "DR", "EPL", "ER", "GG", "HA", "HAR", "HB", "HJKE", "HJSH",
            "HMG", "HSS", "JKE", "JSH", "KSJR", "LX", "MAW", "OSSC", "RE", "RT", "SAR", "SBR", "SOR", "SPT",
            "ST", "STKM", "SVT", "TAP", "TB", "TKI", "TKK", "VST", "WIP", "SMG", "EMP", "EQ", "PQ", "FBC",
            "ACPA", "TUP", "BD", "AI", "NET"}


def _case_part(p):
    core = p.strip('()".,')
    if not core:
        return p
    if re.search(r"\d", core) or core in ACRONYMS or len(core) == 1:
        return p
    return p.replace(core, core[0].upper() + core[1:].lower(), 1)


def title_case(heading):
    """'ARASAKA HJKE-11 YUKIMURA' -> 'Arasaka HJKE-11 Yukimura'"""
    words = []
    for w in heading.split(" "):
        words.append("-".join(_case_part(p) for p in w.split("-")))
    return " ".join(words)


def parse_cost(raw):
    """'1,250eb (Very Expensive)' -> (1250, 'Very Expensive')"""
    m = re.match(r"([\d,]+)\s*eb\s*(?:\((.*?)\))?", raw or "")
    if not m:
        return 0, None
    return int(m.group(1).replace(",", "")), m.group(2)


def html_escape(s):
    return html.escape(s, quote=False)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, data, ensure_ascii=False):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=ensure_ascii)


def description_html(facts, notes, section, entry=None, rules=None):
    """The item description: its entry from Corgo's document, the facts this module adds, the Foundry notes,
    and the source line.

    `entry` is the HTML entry_text.lookup returns. The few items with no entry (listed in entry_text.py) pass
    the module's own text as `rules` instead.
    """
    parts = []
    if entry:
        # The entry opens with its own stat line, so a fact it already states would render twice. Keep only
        # the ones this module adds on top of it - "Enhances" above all, which the sheet shows and
        # validate.mjs resolves against the packs.
        facts = [(k, v) for k, v in facts if f"<strong>{html_escape(k)}:</strong>" not in entry]
        parts.append(entry)
    if facts:
        # A newline after each <br>: Foundry strips tags for list summaries and tooltips, and a tag with no
        # whitespace around it welds the words either side of it ("(Very Expensive)Type: Neuralware").
        parts.append("<p>" + "<br>\n".join(f"<strong>{html_escape(k)}:</strong> {html_escape(v)}"
                                           for k, v in facts) + "</p>")
    if rules:
        parts.append(f"<p>{html_escape(rules)}</p>")
    if notes:
        parts.append("<p><strong>Foundry notes:</strong></p>\n<ul>\n" +
                     "\n".join(f"<li>{html_escape(n)}</li>" for n in notes) + "\n</ul>")
    parts.append(
        f'<p><em>From <a href="{SOURCE_URL}">{html_escape(SOURCE_BOOK)}</a> by Corgopolis '
        f"({html_escape(section)}).</em></p>")
    return "\n".join(parts)


def folder_doc(pack, name, sort):
    _id = doc_id(f"folder:{pack}", name)
    return {"_id": _id, "_key": f"!folders!{_id}", "name": name, "type": "Item", "folder": None,
            "sorting": "a", "sort": (sort + 1) * 100000, "color": None, "description": "", "flags": {}}

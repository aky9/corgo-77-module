"""Optional: use Corgo's original wording in item descriptions instead of the rewritten rules.

Off by default. Enable with `python3 tools/build.py --original-text <export of Corgo's doc> --out build/packs`
(npm run build:original). Corgo gave Kane permission to use his text in this module. The text is read from
your own export at build time; it is never stored in this repo (data/ and build/ are git-ignored).
Items with no single entry in Corgo's doc (Capacity Chart magazines, Gun Shields) keep the rewritten text.
"""
import html, re
from pathlib import Path

_TEXT = None
FOUND, MISSING = [], []
# section key -> (start marker, end marker or None for "next top-level heading")
SECTIONS = {
    "weapons": ("# **WEAPON CATALOG**", "# **AMMUNITION**"),
    "ammo": ("# **AMMUNITION**", None),
    "attachments": ("# **ATTACHMENT CATALOG", "# **MOD CATALOG"),
    "mods": ("# **MOD CATALOG", "# **THRONGLIN"),
    "armor": ("# **ARMOR & FASHION**", "# **SHIELDS**"),
    "shields": ("# **SHIELDS**", None),
    "iconic-armor": ("# **ICONIC ARMOR**", "# **ICONIC CYBERWARE**"),
    "gear": ("# **GENERAL GEAR", "# **CYBERWARE**"),
    "cyberware": ("# **CYBERWARE**", "# **OPERATING SYSTEMS"),
    "operating-systems": ("# **OPERATING SYSTEMS", "# **CYBERWARE ALTERNATIVES"),
    "cyberware-alternatives": ("# **CYBERWARE ALTERNATIVES", "# **2070s FULL BODY CONVERSIONS"),
    "iconic-cyberware": ("# **ICONIC CYBERWARE", "# **ICONIC GEAR"),
    "iconic-gear": ("# **ICONIC GEAR", "# **ICONIC WEAPONS"),
    "iconic-weapons": ("# **ICONIC WEAPONS", "# **ICONIC VEHICLES"),
}
HEADING = re.compile(r"^(#{1,6}) (.+)$")


def enable(path):
    global _TEXT
    _TEXT = Path(path).read_text(encoding="utf-8")


def enabled():
    return _TEXT is not None


# Corgo names some entries in curly quotes ('FOXHOUND', "KAGAMI"). The parsers keep whatever the
# export had, so normalise both sides of a heading comparison rather than one.
QUOTES = str.maketrans("", "", "\u2018\u2019\u201c\u201d")


def _unquote(s):
    return s.translate(QUOTES)


def _plain(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s).replace("\\", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip().upper()


def _section(key):
    start, end = SECTIONS[key]
    a = _TEXT.find(start)  # first occurrence: the doc's "Copy of WEAPONS" tab comes later
    if a < 0:
        return []
    b = _TEXT.find(end, a + 1) if end else -1
    if b < 0:  # no end marker (or the export stops short of it): run to the next top-level heading
        m = re.compile(r"^# ", re.M).search(_TEXT, a + len(start))
        b = m.start() if m else len(_TEXT)
    return _TEXT[a:b].splitlines()


def _find(section_key, heading, intro_only=False):
    lines, want = _section(section_key), _unquote(heading.upper())
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m:
            continue
        title = _unquote(_plain(m.group(2)))
        if title == want or re.match(re.escape(want) + r"(\s|\[|\{|$)", title):
            level, out = len(m.group(1)), []
            for nxt in lines[i + 1:]:
                n = HEADING.match(nxt)
                if n and (intro_only or len(n.group(1)) <= level):
                    break
                out.append(nxt)
            return out
    return None


def _inline(s):
    # drop links, keep their text. The URL may contain escaped parentheses (a fandom wiki article
    # whose title ends in "(Computer_message)"), so match one nested level rather than the first ")".
    s = re.sub(r"\[([^\]]*)\]\((?:[^()]|\\\\\(|\\\\\)|\([^()]*\))*\)", r"\1", s)
    # An escaped *pair* is formatting the export escaped, not a literal asterisk: Corgo nests bold inside
    # bold (a bullet's "\\*\\*Bimodal:\\*\\*") and Google Docs escapes every marker inside a table. A lone
    # "\\*" really is a literal asterisk and is left alone below.
    s = re.sub(r"(?<!\\)\\\*\\\*(.+?)(?<!\\)\\\*\\\*", r"**\1**", s)
    s = re.sub(r"\*{3,}(?=\S)|(?<=\S)\*{3,}", "**", s)     # nested pairs collapse to one marker run
    s = s.replace("\\*", "\x00")                              # escaped asterisks are literal
    s = html.escape(s.replace("\\", ""), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s.replace("*", "").replace("\x00", "*").strip()


def _join_split_links(lines):
    """Rejoin a markdown link the export broke across lines: "[text" on one, "](url)" on the next.

    Corgo's document does this where a link sits at a line end, and left alone the link text and the URL
    both end up visible in the description (XtremSight's and Superjet's source notes).
    """
    def seam(prev, cont):
        # emphasis markers either side of the break are stranded once the link is dropped, and would
        # otherwise open a <strong> with nothing to close it.
        return prev.rstrip().rstrip("*") + cont.strip().lstrip("*")

    out = []
    for line in lines:
        open_link = out and out[-1].count("[") > out[-1].count("]")
        if out and re.match(r"^\s*\**\]\(", line):
            out[-1] = seam(out[-1], line)
        elif open_link and "](" in line:
            out[-1] = seam(out[-1], " " + line)
        else:
            out.append(line)
    return out


def _cell(c):
    """Undo the export's escaping inside a table cell.

    Google Docs escapes every marker in a table, so a cell reads "\\*\\*UPSIZED RECOIL\\*\\*" where Corgo
    means bold, and "\\\\\\*" where he means a literal asterisk (the multiplication sign in the Upsized
    Power table). Only a matched escaped pair around text is treated as formatting; a doubled backslash
    stays literal. A heading's "#" markers inside a cell are dropped: the cell is already a header.
    """
    return re.sub(r"^\s*(?:\\?#)+\s*", "", c)


def _to_html(lines):
    out, bullets, table = [], [], []
    lines = _join_split_links(lines)

    def flush():
        if bullets:
            # newlines between items, so stripping the tags for a plain-text preview leaves separators
            out.append("<ul>\n" + "\n".join(f"<li>{b}</li>" for b in bullets) + "\n</ul>")
            bullets.clear()
        if table:
            rows = [r for r in table if not re.fullmatch(r"\|?[\s:\-|]+\|?", r)]
            cells = [[_inline(_cell(c)) for c in r.strip().strip("|").split("|")] for r in rows]
            if cells:
                head = "\n".join(f"<th>{c}</th>" for c in cells[0])
                body = "\n".join("<tr>\n" + "\n".join(f"<td>{c}</td>" for c in r) + "\n</tr>"
                                 for r in cells[1:])
                out.append(f"<table>\n<tr>\n{head}\n</tr>\n{body}\n</table>")
            table.clear()

    for raw in lines:
        line = raw.strip()
        if not line or _plain(line).startswith("(ART"):
            flush()
            continue
        h = HEADING.match(line)
        if h:  # a sub-heading kept inside an entry: render as a line, not as literal "###"
            flush()
            out.append(f"<p><strong>{_inline(h.group(2))}</strong></p>")
            continue
        if line.startswith("|"):
            if bullets:
                flush()
            table.append(line)
            continue
        if table:
            flush()
        m = re.match(r"^[-*•]\s+(.*)$", line)
        if m and not line.startswith("**"):
            bullets.append(_inline(m.group(1)))
            continue
        flush()
        body = _inline(line)
        if re.sub(r"<[^>]+>|\s", "", body):  # a line of nothing but emphasis markers adds an empty <p>
            out.append(f"<p>{body}</p>")
    flush()
    return "\n".join(out)


def lookup(section_key, heading, group_heading=None, intro_only=False):
    """HTML of Corgo's original entry, or None (disabled, or no entry with that heading)."""
    if _TEXT is None or not heading:
        return None
    block = _find(section_key, heading, intro_only=intro_only)
    if block is None:
        MISSING.append(f"{section_key}: {heading}")
        return None
    FOUND.append(heading)
    parts = []
    if group_heading:
        intro = _find(section_key, group_heading, intro_only=True)
        if intro:
            parts.append(_to_html(intro))
    parts.append(_to_html(block))
    return "\n".join(p for p in parts if p)

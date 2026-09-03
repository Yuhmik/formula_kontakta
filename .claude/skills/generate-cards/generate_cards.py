#!/usr/bin/env python3
"""Default implementation of the /generate-cards skill (see SKILL.md).

Extracts CARD_BEGIN(name, path/, style[, copies[, columns]]) ... CARD_END
blocks from source .md files and writes each card to path/name.html.

Usage:
    python generate_cards.py                # regenerate all cards
    python generate_cards.py <CardName>      # regenerate only the named card

Run from the project root (or pass --root <path>).
CHAR_CONFIG below is the canonical gender-substitution config — SKILL.md no
longer embeds its own copy, so there is nothing else to keep in sync here.
The generation RULES themselves (styles, markdown syntax, gender-agreement
principles) are documented in SKILL.md and инструкции_по_генерации.md; if
you change a rule, update this script to match (or vice versa) and keep
both docs' prose in sync with what the code actually does.

DIAGNOSTICS: the script cannot understand Russian grammar, so it cannot
prove a sentence is correctly gendered — but it CAN mechanically detect the
two situations most likely to hide a mistake, grouped by type and printed
after the file list (see print_diagnostics): a GENDER_RULE(...) condition
naming a character absent from CHAR_CONFIG (always a bug — the condition
silently evaluates false and its content vanishes); and an inverted
character's un-inverted surname form still present somewhere in the
output (a strong signal some mention was never covered by a
surname_regex/cross-reference pair).
"""
import argparse
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Grouped by problem type: one explanation per type, printed once, followed
# by the list of items it applies to (see print_diagnostics).
DIAGNOSTICS = {"unknown_name": [], "leftover_form": [], "original_conflict": []}
DIAGNOSTIC_EXPLANATIONS = {
    "unknown_name": "GENDER_RULE ссылается на персонажа, которого нет в CHAR_CONFIG — условие всегда ложно, содержимое пропадает:",
    "leftover_form": "Похоже, пропущена гендерная замена — неинвертированная форма всё ещё есть в выводе:",
    "original_conflict": "Файлы <!-- original --> не перезаписаны:",
}
_REPORTED_UNKNOWN_CONDITIONS = set()


def diag(kind, item):
    DIAGNOSTICS[kind].append(item)


def print_diagnostics():
    for kind, items in DIAGNOSTICS.items():
        if not items:
            continue
        print()
        print(DIAGNOSTIC_EXPLANATIONS[kind])
        for item in items:
            print(f"  - {item}")


def resolve_output_path(path, root):
    # Every generated file's first line marks its origin ("<!-- generated
    # from ... -->"); a hand-authored file's first line is "<!-- original
    # -->" instead (see инструкции_по_генерации.md, "Маркировка
    # происхождения файлов"). If a card's declared destination already
    # exists and IS hand-authored, something is misconfigured (wrong path
    # in CARD_BEGIN, or a name collision with a real document) — silently
    # overwriting it would destroy hand-written content, so redirect to
    # "<name>_conflict.html" and flag it instead.
    #
    # Returns (path_to_write, protected_path). protected_path is the
    # ORIGINAL intended path when a redirect happened, otherwise None —
    # callers with their own stale-file cleanup MUST exclude protected_path
    # from deletion, or that cleanup (which only knows "not the current
    # output path" = "stale, delete it") destroys the very file this
    # function exists to protect.
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                first_line = f.readline().strip()
        except OSError:
            first_line = ""
        if first_line == "<!-- original -->":
            base, ext = os.path.splitext(path)
            conflict_path = f"{base}_conflict{ext}"
            diag("original_conflict", os.path.relpath(path, root))
            return conflict_path, path
    return path, None


VALID_STYLES = {"document", "handwritten", "reference"}

# ── Gender-inversion config ──────────────────────────────────────────────
# Update this table when a character's gender changes for a run, or when a
# new invertible character is added — it is the single source of truth for
# gender substitution (see the module docstring: nothing else mirrors it).
#
# igroki_key          = key in персонаж column of Игроки.md
# default_gender      = gender used in source files (Персонажи.md, ...)
# card_key            = substring matched against card Name to identify the
#                        character's own card
# surname_regex       = (pattern, replacement) pairs applied to ALL cards
# primary_regex       = (pattern, replacement) pairs applied ONLY to the
#                        character's own card
CHAR_CONFIG = [
    dict(
        igroki_key="Горихвостова-Чаадаевская",
        default_gender="М",
        card_key="Горихвостов",
        nominative_default="Горихвостов",
        nominative_inverted="Горихвостова",
        surname_regex=[
            ("Горихвостовым", "Горихвостовой"),
            ("Горихвостове", "Горихвостовой"),
            ("Горихвостову", "Горихвостовой"),
            ("Горихвостова", "Горихвостовой"),
            (r"Горихвостов вызывал\b", "Горихвостова вызывала"),
            (r"Горихвостов\b", "Горихвостова"),
        ],
        primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
    ),
    dict(
        igroki_key="Строганов-ст",
        default_gender="М",
        card_key="Строганов_ст",
        nominative_default="Строганов-старший",
        nominative_inverted="Строганова-старшая",
        surname_regex=[
            ("Строгановым-старшим", "Строгановой-старшей"),
            ("Строганове-старшем", "Строгановой-старшей"),
            ("Строганову-старшему", "Строгановой-старшей"),
            ("Строганова-старшего", "Строгановой-старшей"),
            ("Строганов-старший", "Строганова-старшая"),
        ],
        primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
    ),
    dict(
        igroki_key="Строганов-мл",
        default_gender="М",
        card_key="Строганов_мл",
        nominative_default="Строганов-младший",
        nominative_inverted="Строганова-младшая",
        surname_regex=[
            ("Строгановым-младшим", "Строгановой-младшей"),
            ("Строганове-младшем", "Строгановой-младшей"),
            ("Строганову-младшему", "Строгановой-младшей"),
            ("Строганова-младшего", "Строгановой-младшей"),
            ("Строганов-младший", "Строганова-младшая"),
        ],
        primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
            (r"\bартельщику\b", "артельщице"), (r"\bАртельщику\b", "Артельщице"),
            (r"\bартельщик\b", "артельщица"), (r"\bАртельщик\b", "Артельщица"),
            (r"\bгосподин\b", "госпожа"), (r"\bГосподин\b", "Госпожа"),
        ],
    ),
    dict(
        igroki_key="Раскольниченко",
        default_gender="М",
        card_key="Раскольниченко",
        nominative_default="Раскольниченко",
        nominative_inverted="Раскольниченко",
        surname_regex=[],
        primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
    ),
    dict(
        igroki_key="Валемонте",
        default_gender="М",
        card_key="Валемонте",
        nominative_default="Валемонте",
        nominative_inverted="Валемонте",
        surname_regex=[],
        primary_regex=[
            ("маг и артист", "иллюзионистка и медиум"),
            (r"\bграф\b", "графиня"), (r"\bГраф\b", "Графиня"),
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
    ),
    dict(
        igroki_key="Ласневский",
        default_gender="Ж",
        card_key="Ласневск",
        nominative_default="Ласневская",
        nominative_inverted="Ласневский",
        surname_regex=[
            ("к Ласневской", "к Ласневскому"),
            ("К Ласневской", "К Ласневскому"),
            ("о Ласневской", "о Ласневском"),
            ("О Ласневской", "О Ласневском"),
            ("об Ласневской", "об Ласневском"),
            ("Об Ласневской", "Об Ласневском"),
            ("Ласневскую", "Ласневского"),
            ("Ласневской", "Ласневского"),
            ("Ласневская", "Ласневский"),
            ("занемогла", "занемог"),
        ],
        primary_regex=[
            ("Была ", "Был "), ("была ", "был "),
            (" ранена", " ранен"),
            ("пострадала", "пострадал"),
            ("оказалась", "оказался"),
            ("тихая", "тихий"),
            ("блаженная", "блаженный"),
            (r"\bона\b", "он"), (r"\bОна\b", "Он"),
            (r"\bеё\b", "его"), (r"\bЕё\b", "Его"),
            (r"\bей\b", "ему"), (r"\bЕй\b", "Ему"),
        ],
    ),
]


def get_current_gender(cfg, igroki_text):
    escaped = re.escape(cfg["igroki_key"])
    m = re.search(
        rf"^\|\s*{escaped}\s*\|\s*([МЖ]?)\s*\|", igroki_text, re.MULTILINE
    )
    if m and m.group(1):
        return m.group(1)
    return cfg["default_gender"]


def test_gender_condition(condition, char_config, igroki_text):
    for or_group in re.split(r"\s+or\s+", condition):
        all_true = True
        for clause in re.split(r"\s+and\s+", or_group):
            m = re.match(r"^(.+?)\s*-\s*([МЖ])$", clause.strip())
            if not m:
                all_true = False
                break
            name_hint, want_gender = m.group(1).strip(), m.group(2)
            cfg_match = next(
                (
                    c
                    for c in char_config
                    if c["nominative_default"] == name_hint
                    or c["nominative_inverted"] == name_hint
                ),
                None,
            )
            if cfg_match is None:
                dedup_key = (name_hint, condition)
                if dedup_key not in _REPORTED_UNKNOWN_CONDITIONS:
                    _REPORTED_UNKNOWN_CONDITIONS.add(dedup_key)
                    diag("unknown_name", f'"{name_hint}" — GENDER_RULE({condition})')
                all_true = False
                break
            if get_current_gender(cfg_match, igroki_text) != want_gender:
                all_true = False
                break
        if all_true:
            return True
    return False


def check_leftover_gender_forms(card_label, text, active_inversions):
    # Every surname_regex FROM pattern (plus the bare nominative_default)
    # is supposed to have been substituted away by now, everywhere it's
    # currently active — a literal match still present is either a
    # genuinely missed mention (most likely: a new word form or
    # cross-reference not yet added to $charConfig/CHAR_CONFIG) or, much
    # more rarely, text a GENDER_RULE branch deliberately protected. See
    # generate-roles/generate_roles.py's module docstring for the
    # Раскольниченко/Строганов-мл incident that motivated this check.
    for cfg in active_inversions:
        patterns = [re.escape(cfg["nominative_default"])] + [
            pat for pat, _ in cfg["surname_regex"]
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if not m:
                continue
            start, end = max(0, m.start() - 25), min(len(text), m.end() + 25)
            snippet = text[start:end].replace("\n", " ⏎ ")
            diag(
                "leftover_form",
                f'{cfg["igroki_key"]} в карточке "{card_label}": '
                f"«{pat}» — …{snippet}…",
            )
            break  # one hit per card is enough signal, avoid pile-up


def resolve_gender_rules(text, char_config, igroki_text):
    pattern = re.compile(r"GENDER_RULE\(([^)]+)\)(.*?)GENDER_END", re.DOTALL)
    placeholders = []
    out = []
    last_pos = 0
    for m in pattern.finditer(text):
        out.append(text[last_pos : m.start()])
        if test_gender_condition(m.group(1), char_config, igroki_text):
            idx = len(placeholders)
            placeholders.append(m.group(2))
            out.append(f"@@GR{idx}@@")
        last_pos = m.end()
    out.append(text[last_pos:])
    return "".join(out), placeholders


# ── Minimal markdown → HTML conversion for card bodies ──────────────────


def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def convert_inline_markdown(s):
    s = html_escape(s)
    # <br> is the one inline HTML tag authors write by hand inside table
    # cells/paragraphs (a full line of raw HTML already passes through
    # unescaped elsewhere - see convert_card_html_body's "^<[a-zA-Z]" branch
    # - but inline text like a table cell always goes through here and
    # would otherwise get escaped to "&lt;br&gt;").
    s = re.sub(r"&lt;br\s*/?&gt;", "<br>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def convert_html_table(rows):
    out = ["<table>"]
    header_cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    out.append("<thead><tr>")
    for c in header_cells:
        out.append(f"<th>{convert_inline_markdown(c)}</th>")
    out.append("</tr></thead><tbody>")
    for r in range(2, len(rows)):
        cells = [c.strip() for c in rows[r].strip().strip("|").split("|")]
        out.append("<tr>")
        for c in cells:
            out.append(f"<td>{convert_inline_markdown(c)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def convert_card_html_body(body):
    # Mirrors ConvertTo-CardHtmlBody's Append/AppendLine distinction exactly:
    # <ul>/<ol> and their <li>s are concatenated with NO separator, only the
    # closing tag gets a trailing newline; every other construct gets its own
    # line. Fragments below are joined with "" (not "\n") to preserve that.
    lines = re.split(r"\r?\n", body)
    parts = []
    heading_used = False
    uses_mermaid = False
    i = 0
    n = len(lines)
    while i < n:
        trimmed = lines[i].strip()

        if trimmed == "":
            i += 1
            continue

        if trimmed.startswith("<!--"):
            comment_lines = [lines[i]]
            while i < n and "-->" not in lines[i]:
                i += 1
                comment_lines.append(lines[i])
            i += 1
            parts.append("\n".join(comment_lines) + "\n")
            continue

        if re.match(r"^<[a-zA-Z]", trimmed):
            parts.append(lines[i] + "\n")
            i += 1
            continue

        m = re.match(r"^```(\w*)$", trimmed)
        if m:
            lang = m.group(1)
            i += 1
            code_lines = []
            while i < n and lines[i].strip() != "```":
                code_lines.append(lines[i])
                i += 1
            i += 1
            code = html_escape("\n".join(code_lines))
            if lang == "mermaid":
                uses_mermaid = True
                parts.append(f'<pre class="mermaid">{code}</pre>\n')
            else:
                parts.append(f"<pre><code>{code}</code></pre>\n")
            continue

        if re.match(r"^\|.*\|$", trimmed):
            table_rows = []
            while i < n and re.match(r"^\|.*\|$", lines[i].strip()):
                table_rows.append(lines[i])
                i += 1
            parts.append(convert_html_table(table_rows) + "\n")
            continue

        if re.match(r"^[-*]\s+\S", trimmed):
            parts.append("<ul>")
            while i < n:
                m2 = re.match(r"^[-*]\s+(.*)$", lines[i].strip())
                if not m2:
                    break
                parts.append(f"<li>{convert_inline_markdown(m2.group(1))}</li>")
                i += 1
            parts.append("</ul>\n")
            continue

        if re.match(r"^\d+\.\s+\S", trimmed):
            parts.append("<ol>")
            while i < n:
                m2 = re.match(r"^\d+\.\s+(.*)$", lines[i].strip())
                if not m2:
                    break
                parts.append(f"<li>{convert_inline_markdown(m2.group(1))}</li>")
                i += 1
            parts.append("</ol>\n")
            continue

        if re.match(r"^-{3,}$", trimmed):
            parts.append("<hr>\n")
            i += 1
            continue

        m = re.match(r"^\*\*([^*]+)\*\*$", trimmed)
        if m:
            tag = "h1" if not heading_used else "h2"
            heading_used = True
            parts.append(f"<{tag}>{convert_inline_markdown(m.group(1))}</{tag}>\n")
            i += 1
            continue

        parts.append(f"<p>{convert_inline_markdown(trimmed)}</p>\n")
        i += 1

    return "".join(parts).rstrip(), uses_mermaid


# ── Per-style HTML wrapper ────────────────────────────────────────────────

DOCUMENT_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { background: #f4ecd8; }
body {
  font-family: "Old Standard TT", "Palatino Linotype", "Book Antiqua", Georgia, serif;
  color: #2b2013;
  font-size: 11pt;
  line-height: 1.35;
}
.page { margin: 0 auto; background: #f4ecd8; }
h1 { text-align: center; font-weight: 700; font-size: 13pt; letter-spacing: 0.05em; text-transform: uppercase; margin: 0 0 4mm 0; }
h1::after { content: ""; display: block; width: 42mm; margin: 3mm auto 0 auto; border-top: 0.8pt solid #5a4a2f; }
h2 { font-weight: 700; font-size: 11.5pt; margin: 4mm 0 2mm 0; }
p { text-align: justify; text-indent: 8mm; margin-bottom: 2mm; hyphens: auto; }
img { max-width: 100%; height: auto; }
ul, ol { margin: 1.5mm 0 2.5mm 5mm; padding-left: 4mm; }
ul { list-style-type: "\\2013\\0020"; }
li { margin-bottom: 1.5mm; text-align: justify; hyphens: auto; }
hr { border: none; border-top: 0.8pt solid #5a4a2f; width: 42mm; margin: 4mm auto; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 10pt; }
th, td { border: 0.6pt solid #8a7a5f; padding: 1.5mm 2.5mm; text-align: left; }
th { background: rgba(138, 122, 95, 0.12); font-weight: 700; }
pre { background: rgba(138, 122, 95, 0.08); padding: 3mm; font-size: 9pt; overflow-x: auto; white-space: pre-wrap; }
strong { font-weight: 700; }
em { font-style: italic; }
p, h1, h2, img, table, pre, li { break-inside: avoid; page-break-inside: avoid; }
h1, h2 { break-after: avoid; page-break-after: avoid; }
@media print { html, body { background: #fff; } .page { background: transparent; } }
@media screen { body { padding: 10mm 0; background: #d8cdb4; } .page { width: 210mm; min-height: 297mm; padding: 16mm 18mm; box-shadow: 0 2mm 8mm rgba(0, 0, 0, 0.3); } }"""

HANDWRITTEN_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { background: #f4ecd8; }
body {
  font-family: "Caveat", cursive;
  color: #2b2013;
  font-size: 17pt;
  line-height: 1.3;
}
.page { margin: 0 auto; background: #f4ecd8; }
h1 { font-weight: 700; font-size: 26pt; text-align: left; margin: 0 0 4mm 0; }
h2 { font-weight: 700; font-size: 20pt; margin: 4mm 0 1.5mm 0; }
p { text-align: left; text-indent: 0; hyphens: none; margin-bottom: 2.5mm; }
img { max-width: 100%; height: auto; }
ul, ol { margin: 1.5mm 0 2.5mm 6mm; }
li { margin-bottom: 1.5mm; text-align: left; hyphens: none; }
hr { border: none; border-top: 0.8pt solid #8a7a5f; width: 42mm; margin: 4mm 0; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 14pt; }
th, td { border: 0.6pt solid #8a7a5f; padding: 1.5mm 2.5mm; text-align: left; }
th { background: rgba(138, 122, 95, 0.12); font-weight: 700; }
pre { background: rgba(138, 122, 95, 0.08); padding: 3mm; font-size: 12pt; overflow-x: auto; white-space: pre-wrap; font-family: "Old Standard TT", Georgia, serif; }
strong { font-weight: 700; }
em { font-style: italic; }
p, h1, h2, img, table, pre, li { break-inside: avoid; page-break-inside: avoid; }
h1, h2 { break-after: avoid; page-break-after: avoid; }
@media print { html, body { background: #fff; } .page { background: transparent; } }
@media screen { body { padding: 10mm 0; background: #d8cdb4; } .page { width: 210mm; min-height: 297mm; padding: 18mm 20mm; box-shadow: 0 2mm 8mm rgba(0, 0, 0, 0.3); } }"""

REFERENCE_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { background: #fff; }
body {
  font-family: Georgia, "Times New Roman", serif;
  color: #1a1a1a;
  font-size: 11pt;
  line-height: 1.4;
}
.sheet { max-width: 190mm; margin: 0 auto; }
h1 { font-size: 15pt; font-weight: 700; border-bottom: 1pt solid #333; padding-bottom: 2mm; margin-bottom: 4mm; }
h2 { font-size: 12.5pt; font-weight: 700; margin: 5mm 0 2mm 0; }
p { margin-bottom: 2mm; text-align: left; }
img { max-width: 100%; height: auto; }
ul, ol { margin: 1.5mm 0 3mm 6mm; }
li { margin-bottom: 1mm; }
hr { border: none; border-top: 1pt solid #999; margin: 4mm 0; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 10pt; }
th, td { border: 0.6pt solid #999; padding: 1.5mm 2.5mm; text-align: left; }
th { background: #eee; font-weight: 700; }
pre { background: #f4f4f4; border: 1px solid #ddd; padding: 3mm; font-size: 9pt; overflow-x: auto; white-space: pre-wrap; }
pre.mermaid { background: #fff; border: none; text-align: center; }
strong { font-weight: 700; }
em { font-style: italic; }
p, h1, h2, img, table, pre, li { break-inside: avoid; page-break-inside: avoid; }
h1, h2 { break-after: avoid; page-break-after: avoid; }
@media screen { body { padding: 10mm; } }"""


def add_copies_grid_css(css, top_class, cut_color, columns):
    return css + f"""

@page {{ size: A4; margin: 10mm; }}
.{top_class}.copies {{ padding: 0; }}
@media screen {{ .{top_class}.copies {{ padding: 10mm; }} }}
.copies-grid {{ display: grid; grid-template-columns: repeat({columns}, 1fr); gap: 0; }}
.copy-cell {{ padding: 10mm; border-right: 1pt dashed {cut_color}; border-bottom: 1pt dashed {cut_color}; break-inside: avoid; page-break-inside: avoid; }}
.copy-cell:nth-child({columns}n) {{ border-right: none; }}
.copy-cell:nth-last-child(-n+{columns}) {{ border-bottom: none; }}"""


def get_card_wrapper(style, uses_mermaid, copies, columns):
    if style == "document":
        wrap = dict(
            font_links='  <link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '  <link href="https://fonts.googleapis.com/css2?family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">',
            css=DOCUMENT_CSS,
            extra_head="",
            open="<div class=\"page\">",
            close="</div>",
            top_class="page",
            cut_color="#8a7a5f",
        )
    elif style == "handwritten":
        wrap = dict(
            font_links='  <link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '  <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap" rel="stylesheet">',
            css=HANDWRITTEN_CSS,
            extra_head="",
            open="<div class=\"page\">",
            close="</div>",
            top_class="page",
            cut_color="#8a7a5f",
        )
    else:  # reference
        mermaid_script = ""
        if uses_mermaid:
            mermaid_script = (
                '  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>\n'
                "  <script>mermaid.initialize({ startOnLoad: true });</script>"
            )
        wrap = dict(
            font_links="",
            css=REFERENCE_CSS,
            extra_head=mermaid_script,
            open="<div class=\"sheet\">",
            close="</div>",
            top_class="sheet",
            cut_color="#999",
        )

    if copies > 1:
        wrap["css"] = add_copies_grid_css(
            wrap["css"], wrap["top_class"], wrap["cut_color"], columns
        )
        wrap["open"] = re.sub(
            r'(class=")(\w+)"', r'\1\2 copies"', wrap["open"], count=1
        )
    else:
        if style in ("document", "handwritten"):
            wrap["css"] += "\n@page { size: A4; margin: 10mm; }"
        else:
            wrap["css"] += "\n@page { size: A4; margin: 10mm 15mm; }\n.sheet { padding: 0 6mm; }"

    return wrap


TAG_PATTERN = re.compile(
    r"^CARD_BEGIN\(([^,]+),\s*([^,]+),\s*([^,)]+)(?:,\s*(\d+))?(?:,\s*(\d+))?\)([\s\S]*?)^CARD_END",
    re.MULTILINE,
)
NO_STYLE_PATTERN = re.compile(r"^CARD_BEGIN\(([^,]+),\s*([^,)]+)\)", re.MULTILINE)
LEGACY_PATTERN = re.compile(r"^CARD_BEGIN\(([^,)]+)\)", re.MULTILINE)


def find_source_files(root):
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        parts = rel.split(os.sep) if rel != "." else []
        if any(p in ("public", "черновики", ".claude") for p in parts):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith(".md"):
                result.append(os.path.join(dirpath, fn))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("card_name", nargs="?", default="")
    parser.add_argument("--root", default=os.getcwd())
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    filter_name = args.card_name

    with open(os.path.join(root, "Игроки.md"), "r", encoding="utf-8-sig") as f:
        igroki_text = f.read()

    active_inversions = [
        c for c in CHAR_CONFIG if get_current_gender(c, igroki_text) != c["default_gender"]
    ]

    generated = []
    skipped = []

    for path in find_source_files(root):
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
        if not text:
            continue
        fname = os.path.basename(path)

        for m in TAG_PATTERN.finditer(text):
            name = m.group(1).strip()
            directory = m.group(2).strip().rstrip("/\\")
            style = m.group(3).strip()
            copies = int(m.group(4)) if m.group(4) else 1
            columns = int(m.group(5)) if m.group(5) else 2
            body = re.sub(r"^[\r\n]+", "", m.group(6))
            body = re.sub(r"[\r\n]+$", "", body)

            if filter_name and name != filter_name:
                continue

            if style not in VALID_STYLES:
                skipped.append(
                    f'{fname}: CARD_BEGIN({name}) – неизвестный стиль "{style}" '
                    "(нужен document/handwritten/reference), пропущено"
                )
                continue

            orig_name = name

            body, placeholders = resolve_gender_rules(body, CHAR_CONFIG, igroki_text)

            for cfg in active_inversions:
                for pat, repl in cfg["surname_regex"]:
                    body = re.sub(pat, repl, body)
                    name = re.sub(pat, repl, name)
                if cfg["card_key"] and re.search(
                    re.escape(cfg["card_key"]), name, re.IGNORECASE
                ):
                    for pat, repl in cfg["primary_regex"]:
                        body = re.sub(pat, repl, body)

            for i, ph in enumerate(placeholders):
                body = body.replace(f"@@GR{i}@@", ph)

            check_leftover_gender_forms(name, body, active_inversions)

            conv_html, uses_mermaid = convert_card_html_body(body)
            wrap = get_card_wrapper(style, uses_mermaid, copies, columns)

            inner_html = conv_html
            if copies > 1:
                cells = [f'<div class="copy-cell">\n{conv_html}\n</div>' for _ in range(copies)]
                inner_html = f'<div class="copies-grid">\n' + "\n".join(cells) + "\n</div>"

            title_text = name.replace("_", " ")
            origin_comment = f'<!-- generated from `{fname}` CARD "{orig_name}" -->'

            full_html = f"""{origin_comment}
<!DOCTYPE html>
<html lang="ru">

<head>
  <meta charset="utf-8">
  <title>{title_text}</title>
{wrap['font_links']}
  <style>
{wrap['css']}
  </style>
{wrap['extra_head']}
</head>

<body>
  {wrap['open']}
{inner_html}
  {wrap['close']}
</body>

</html>
"""

            out_dir = os.path.join(root, directory)
            os.makedirs(out_dir, exist_ok=True)
            out_file, protected_path = resolve_output_path(
                os.path.join(out_dir, f"{name}.html"), root
            )
            with open(out_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(full_html)
            generated.append(os.path.relpath(out_file, root))

            for stale_name in dict.fromkeys([orig_name, name]):
                for ext in (".md", ".html"):
                    stale = os.path.join(out_dir, f"{stale_name}{ext}")
                    if stale != out_file and stale != protected_path and os.path.exists(stale):
                        os.remove(stale)

        for m in NO_STYLE_PATTERN.finditer(text):
            skipped.append(
                f"{fname}: CARD_BEGIN({m.group(1).strip()}) – нет стиля "
                "(третьим аргументом нужен document/handwritten/reference), пропущено"
            )

        for m in LEGACY_PATTERN.finditer(text):
            skipped.append(
                f"{fname}: CARD_BEGIN({m.group(1).strip()}) – нет пути назначения и стиля, пропущено"
            )

    if generated:
        print("Сгенерированы:")
        for g in generated:
            print(f"  {g}")
    if skipped:
        print()
        print("Пропущены:")
        for s in skipped:
            print(f"  {s}")
    if not generated and not skipped:
        print("Карточки не найдены.")

    print_diagnostics()


if __name__ == "__main__":
    sys.exit(main())

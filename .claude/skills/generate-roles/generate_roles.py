#!/usr/bin/env python3
"""Python port of the /generate-roles skill (see SKILL.md and
инструкции_по_генерации.md).

Generates public/Роли.md, public/Роли.html and public/персонажи/<name>.html
from Персонажи.md + Игроки.md + материалы/графика/персонажи/портреты.md.

Usage:
    python generate_roles.py [--root <path>] [--out-dir <path>] [--dry-run]

Run from the project root (or pass --root <path>).

IMPORTANT / KNOWN LIMITATIONS (read before trusting this blindly):

This script mechanically implements the parts of инструкции_по_генерации.md
that are genuinely rule-based: PUB_INFO/GM_INFO/GENDER_RULE extraction,
portrait/contact lookup, имя substitution, footer, and HTML/MD structure.
Those are fully reliable.

Grammatical gender agreement (SurnameRegex/PrimaryRegex below, mirroring
$charConfig in ../generate-cards/SKILL.md) is NOT fully general. It is
curated per observed text, not derived from real language understanding.
Two consequences:

1. PrimaryRegex-style word pairs (pronouns, adjectives, titles) are scoped
   to each character's own block, exactly like generate-cards. Applying
   generic pronoun swaps (он/она/его/её) globally across the whole prose
   corpus would be unsafe (a stray "он" almost never refers to the
   inverted character), so this script does NOT attempt that.
2. Cross-references to an inverted character from *other* characters'
   biographies (e.g. Горихвостов's card mentioning Ласневская/Ласневский)
   need explicit compound-phrase pairs in CHAR_CONFIG[...]['cross_ref_regex'].
   These have been curated by grep-ing the corpus for every mention of each
   currently-invertible character as of the time this script was written.
   If you add a NEW sentence elsewhere that mentions an invertible
   character, grep for it and add a pair here, or it will not be gendered.

When re-running after editing Персонажи.md, diff the output against the
committed public/ files and read the diff before trusting it — this script
will make cross-references *consistent* with the documented rules, which
may not match ad hoc choices baked into previously hand-tuned files.

DIAGNOSTICS: the script cannot understand Russian grammar, so it cannot
prove a sentence is correctly gendered — but it CAN mechanically detect the
situations most likely to hide a mistake, grouped by type and printed
after the file list (see print_diagnostics): a GENDER_RULE(...) condition
naming a character absent from CHAR_CONFIG (always a bug — the condition
silently evaluates false and its content vanishes); an inverted
character's un-inverted surname form still present somewhere in the
output (a strong signal some mention was never covered by a
surname_regex/cross-reference pair); and an inverted character mentioned
inside another character's own card (not necessarily wrong, but exactly
where a missed pronoun is most likely — worth a human's eyes).
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
DIAGNOSTICS = {
    "unknown_name": [],
    "leftover_form": [],
    "co_mention": [],
    "original_conflict": [],
}
DIAGNOSTIC_EXPLANATIONS = {
    "unknown_name": "GENDER_RULE ссылается на персонажа, которого нет в CHAR_CONFIG — условие всегда ложно, содержимое пропадает:",
    "leftover_form": "Похоже, пропущена гендерная замена — неинвертированная форма всё ещё есть в выводе:",
    "co_mention": "Инвертированный персонаж упомянут в чужой карточке — проверьте согласование родов и падежей:",
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
    # происхождения файлов"). If a computed destination already exists and
    # IS hand-authored, silently overwriting it would destroy hand-written
    # content — redirect to "<name>_conflict.html" and flag it instead.
    #
    # Returns (path_to_write, protected_path). protected_path is the
    # ORIGINAL intended path when a redirect happened, otherwise None — the
    # per-character stale-file cleanup below MUST exclude protected_path
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


CROSSPOL_PHRASES = [
    "Кросспол уместен.",
    "Гендер персонажа можно инвертировать.",
    "Кросспол *ожидается*.",
]

# ── Character configuration ──────────────────────────────────────────────
# One entry per "## " block in Персонажи.md, IN FILE ORDER (blocks are
# paired with this list positionally — see split_character_blocks/main).
#
# igroki_key          = key in персонаж column of Игроки.md
# default_gender      = gender as written in Персонажи.md
# invertible          = whether grammatical substitution ever applies
# special_no_grammar  = never apply grammar substitution even if gender
#                        differs from default (Чарторыжский: see CLAUDE.md
#                        "Chartoryzhsky's hidden variant")
# nominative_default / nominative_inverted = spellings used in GENDER_RULE
#                        conditions elsewhere in the corpus
# surname_regex       = (pattern, replacement) applied to EVERY block
#                        (declined surname forms + curated cross-references
#                        to this character from other characters' text)
# primary_regex       = (pattern, replacement) applied ONLY to this
#                        character's own block (heading/subtitle/PUB_INFO/bio)
# portrait_key        = {gender: exact heading text in портреты.md}
CHAR_CONFIG = [
    dict(
        igroki_key="Самохвалов", default_gender="М", invertible=False,
        nominative_default="Самохвалов", nominative_inverted="Самохвалов",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "господин Самохвалов"},
    ),
    dict(
        igroki_key="Самохвалова", default_gender="Ж", invertible=False,
        nominative_default="Самохвалова", nominative_inverted="Самохвалова",
        surname_regex=[], primary_regex=[],
        portrait_key={"Ж": "госпожа Самохвалова"},
    ),
    dict(
        igroki_key="Самохвалова-мл", default_gender="Ж", invertible=False,
        nominative_default="Самохвалова-мл", nominative_inverted="Самохвалова-мл",
        surname_regex=[], primary_regex=[],
        portrait_key={"Ж": "мадемуазель Самохвалова"},
    ),
    dict(
        igroki_key="Горихвостов-Чаадаевский", default_gender="М", invertible=True,
        filename_default="Горихвостов-Чаадаевский", filename_inverted="Горихвостова-Чаадаевская",
        nominative_default="Горихвостов", nominative_inverted="Горихвостова",
        surname_regex=[
            ("Горихвостов-Чаадаевский", "Горихвостова-Чаадаевская"),
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
        portrait_key={"М": "Горихвостов-Чаадаевский", "Ж": "Горихвостова-Чаадаевская"},
    ),
    dict(
        igroki_key="Чарторыжский", default_gender="М", invertible=False,
        special_no_grammar=True,
        nominative_default="Чарторыжский", nominative_inverted="Чарторыжский",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "майор Чарторыжский", "Ж": "майор Чарторыжский"},
    ),
    dict(
        igroki_key="Свербеев", default_gender="М", invertible=False,
        nominative_default="Свербеев", nominative_inverted="Свербеев",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "полковник Свербеев"},
    ),
    dict(
        igroki_key="Доложейко", default_gender="М", invertible=False,
        nominative_default="Доложейко", nominative_inverted="Доложейко",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "пристав Доложейко"},
    ),
    dict(
        igroki_key="Громов", default_gender="М", invertible=False,
        nominative_default="Громов", nominative_inverted="Громов",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "иерей Громов"},
    ),
    dict(
        igroki_key="Ефросинья", default_gender="Ж", invertible=False,
        nominative_default="Ефросинья", nominative_inverted="Ефросинья",
        surname_regex=[], primary_regex=[],
        portrait_key={"Ж": "сестра Ефросинья"},
    ),
    dict(
        igroki_key="Пирогов", default_gender="М", invertible=False,
        nominative_default="Пирогов", nominative_inverted="Пирогов",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "доктор Пирогов"},
    ),
    dict(
        igroki_key="Фишнер", default_gender="Ж", invertible=False,
        nominative_default="Фишнер", nominative_inverted="Фишнер",
        surname_regex=[], primary_regex=[],
        portrait_key={"Ж": "фельдшерица Фишнер"},
    ),
    dict(
        igroki_key="Строганов-ст", default_gender="М", invertible=True,
        filename_default="Строганов-ст", filename_inverted="Строганова-ст",
        nominative_default="Строганов-старший", nominative_inverted="Строганова-старшая",
        # common_stem(nominative_default, nominative_inverted) would give
        # the bare "Строганов" — shared with Строганов-мл, so diagnostics'
        # co-mention check would flood every card that mentions the OTHER
        # brother. A prefix like "Строганов-стар" doesn't work either:
        # declined cross-reference forms insert letters between the surname
        # and the modifier (dative "Строгановой-старшей", genitive
        # "Строганова-старшего"), so requiring them adjacent misses most
        # real mentions. The bare modifier is distinctive enough on its own
        # within this corpus.
        diag_stem="старш",
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
        portrait_key={"М": "артельщик Строганов-старший", "Ж": "артельщица Строганова-старшая"},
    ),
    dict(
        igroki_key="Строганов-мл", default_gender="М", invertible=True,
        filename_default="Строганов-мл", filename_inverted="Строганова-мл",
        nominative_default="Строганов-младший", nominative_inverted="Строганова-младшая",
        diag_stem="младш",  # see Строганов-ст's diag_stem comment
        surname_regex=[
            ("Строгановым-младшим", "Строгановой-младшей"),
            ("Строганове-младшем", "Строгановой-младшей"),
            ("Строганову-младшему", "Строгановой-младшей"),
            ("Строганова-младшего", "Строгановой-младшей"),
            ("Строганов-младший", "Строганова-младшая"),
            # cross-reference: Раскольниченко's card
            ("купчишка", "купчиха"),
            ("не такой серый", "не такая серая"),
            ("Живой, рисковый, не как его братец", "Живая, рисковая, не как её братец"),
            ("Такой мог бы помочь", "Такая могла бы помочь"),
            ("Для него – собственное дело", "Для неё – собственное дело"),
            # cross-reference: Ледонтова's card
            ("купец-де", "купчиха-де"),
        ],
        primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
            (r"\bартельщику\b", "артельщице"), (r"\bАртельщику\b", "Артельщице"),
            (r"\bартельщик\b", "артельщица"), (r"\bАртельщик\b", "Артельщица"),
            (r"\bгосподин\b", "госпожа"), (r"\bГосподин\b", "Госпожа"),
            ("недостаточно серьёзным", "недостаточно серьёзной"),
            ("стал вхож", "стала вхожа"),
            ("брат и компаньон", "сестра и компаньонка"),
            (
                "не так давно стал считаться за взрослого",
                "не так давно стала считаться за взрослую",
            ),
        ],
        portrait_key={"М": "артельщик Строганов-младший", "Ж": "артельщица Строганова-младшая"},
    ),
    dict(
        igroki_key="Валемонте", default_gender="М", invertible=True,
        nominative_default="Валемонте", nominative_inverted="Валемонте",
        surname_regex=[], primary_regex=[
            ("маг и артист", "иллюзионистка и медиум"),
            (r"\bграф\b", "графиня"), (r"\bГраф\b", "Графиня"),
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
        portrait_key={"М": "граф Валемонте", "Ж": "графиня Валемонте"},
    ),
    dict(
        igroki_key="Раскольниченко", default_gender="М", invertible=True,
        nominative_default="Раскольниченко", nominative_inverted="Раскольниченко",
        surname_regex=[], primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
        portrait_key={"М": "Раскольниченко", "Ж": "Раскольниченко"},
    ),
    dict(
        igroki_key="Ледонтова", default_gender="Ж", invertible=False,
        nominative_default="Ледонтова", nominative_inverted="Ледонтова",
        surname_regex=[], primary_regex=[],
        portrait_key={"Ж": "Камилла Ледонтова"},
    ),
    dict(
        igroki_key="Краузе", default_gender="М", invertible=True,
        nominative_default="Краузе", nominative_inverted="Краузе",
        surname_regex=[], primary_regex=[
            (r"\bон\b", "она"), (r"\bОн\b", "Она"),
            (r"\bего\b", "её"), (r"\bЕго\b", "Её"),
            (r"\bему\b", "ей"), (r"\bЕму\b", "Ей"),
            (r"\bим\b", "ей"), (r"\bИм\b", "Ей"),
        ],
        portrait_key={"М": "господин Краузе", "Ж": "госпожа Краузе"},
    ),
    dict(
        igroki_key="Ласневский", default_gender="Ж", invertible=True,
        filename_default="Ласневская", filename_inverted="Ласневский",
        nominative_default="Ласневская", nominative_inverted="Ласневский",
        surname_regex=[
            # cross-references: Горихвостов's card
            ("Племяннице Ласневской, приехавшей", "Племяннику Ласневскому, приехавшему"),
            ("она была тяжело ранена", "он был тяжело ранен"),
            ("видел её на месте крушения", "видел его на месте крушения"),
            ("тронуть племянницу", "тронуть племянника"),
            ("что племянницу лучше", "что племянника лучше"),
            ("что племянница больна", "что племянник болен"),
            # cross-references: Пирогов's card
            ("племянница Ласневская больна", "племянник Ласневский болен"),
            ("за Ласневскую переживает", "за Ласневского переживает"),
            ("Надо её проведать", "Надо его проведать"),
            # cross-references: госпожа Самохвалова's card
            ("гостила племянница", "гостил племянник"),
            (
                "Ласневская, бледная тихая барышня",
                "Ласневский, бледный тихий юноша",
            ),
            ("больна, а врача", "болен, а врача"),
            # generic surname forms (own card + anywhere else)
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
            ("племянницу", "племянника"),
            ("племянница", "племянник"),
        ],
        primary_regex=[
            ("Мадемуазель", "господин"), ("мадемуазель", "господин"),
            ("Племянница", "Племянник"), ("племянница", "племянник"),
            ("заглянувшая", "заглянувший"),
            ("Успела", "Успел"),
            ("держалась", "держался"),
            ("задавала", "задавал"),
            ("занедужила", "занедужил"),
            ("Была ", "Был "), ("была ", "был "),
            (" ранена", " ранен"),
            ("пострадала", "пострадал"),
            ("оказалась", "оказался"),
            ("не появлялась", "не появлялся"),
            ("появилась", "появился"),
            ("запомнилась", "запомнился"),
            ("Бледная", "Бледный"),
            ("тихая", "тихий"),
            ("блаженная", "блаженный"),
            (r"\bона\b", "он"), (r"\bОна\b", "Он"),
            (r"\bеё\b", "его"), (r"\bЕё\b", "Его"),
            (r"\bей\b", "ему"), (r"\bЕй\b", "Ему"),
        ],
        portrait_key={"Ж": "Ласневская", "М": "Ласневский"},
    ),
    dict(
        igroki_key="Захар", default_gender="М", invertible=False,
        nominative_default="Захар", nominative_inverted="Захар",
        surname_regex=[], primary_regex=[],
        portrait_key={"М": "Захар"},
    ),
]

for _cfg in CHAR_CONFIG:
    _cfg.setdefault("special_no_grammar", False)
    _cfg.setdefault("filename_default", _cfg["igroki_key"])
    _cfg.setdefault("filename_inverted", _cfg["igroki_key"])
    _cfg.setdefault("diag_stem", None)


# ── Игроки.md parsing ─────────────────────────────────────────────────────


def parse_markdown_table(text, heading_hint):
    """Parses the first markdown table found in text into a list of dict rows."""
    lines = text.split("\n")
    rows = []
    header = None
    in_table = False
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            in_table = True
            continue
        if all(re.fullmatch(r"-{2,}|:?-+:?", c) for c in cells):
            continue  # separator row
        if not any(cells):
            continue
        row = dict(zip(header, cells))
        rows.append(row)
    return rows


def get_igroki_row(igroki_rows, key):
    for r in igroki_rows:
        if r.get("персонаж", "").strip() == key:
            return r
    return None


def current_gender(cfg, igroki_rows):
    row = get_igroki_row(igroki_rows, cfg["igroki_key"])
    if row and row.get("пол", "").strip():
        return row["пол"].strip()
    return cfg["default_gender"]


# ── Портреты.md parsing ───────────────────────────────────────────────────


def parse_portraits(text):
    reserve_idx = text.find("## Запасник")
    active_text = text if reserve_idx == -1 else text[:reserve_idx]
    blocks = []
    pattern = re.compile(
        r"^## (.+?) – .*?\(([МЖ])[,)]", re.MULTILINE
    )
    matches = list(pattern.finditer(active_text))
    for idx, m in enumerate(matches):
        heading = m.group(1).strip()
        gender = m.group(2)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(active_text)
        chunk = active_text[start:end]
        img_match = re.search(r"<img[^>]*>", chunk)
        img_tag = img_match.group(0) if img_match else ""
        blocks.append((heading, gender, img_tag))
    return blocks


def find_portrait(cfg, gender, portrait_blocks):
    key = cfg["portrait_key"].get(gender)
    if not key:
        return ""
    for heading, g, img in portrait_blocks:
        if heading == key and g == gender:
            return img
    return ""


# ── GENDER_RULE resolution (same algorithm as generate-cards) ────────────


def test_gender_condition(condition, char_config, igroki_rows):
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
            if current_gender(cfg_match, igroki_rows) != want_gender:
                all_true = False
                break
        if all_true:
            return True
    return False


def normalize_ws(s):
    return " ".join(s.split())


def resolve_gender_rules(text, char_config, igroki_rows, protected_out=None):
    # GENDER_RULE(...) is used both inline ("GENDER_RULE(X - М) text GENDER_END",
    # all on one line — see e.g. Персонажи.md:85) and block-style (condition,
    # content, GENDER_END each on their own line — Персонажи.md's Костюм
    # blocks). The captured content is .strip()-ped before being used as the
    # replacement, rather than kept verbatim with its surrounding newlines:
    # that avoids adding any padding beyond what the source already had, so
    # downstream blank-line paragraph splitting sees exactly the source's
    # blank-line structure — no more, no less. This matters for two cases:
    # two adjacent kept/dropped blocks with no blank line between them must
    # not gain a spurious one (Чарторыжский's two "Горихвостов - М" blocks,
    # meant to read as one paragraph), and a blank line genuinely INSIDE one
    # kept block's own content must survive (Чарторыжский's Ж branch, which
    # itself spans two source paragraphs).
    #
    # If `protected_out` is given, the content of any KEPT branch whose
    # condition is compound (uses "and"/"or", so names more than one
    # character) is added to it. Such branches are hand-written for one
    # exact combination and often mention a pronoun belonging to the OTHER
    # named character, not to the card's own subject — e.g. Персонажи.md:745
    # "GENDER_RULE(Строганова-младшая - Ж and Раскольниченко - М) Может он
    # и не только..." — "он" is Раскольниченко, not Строганов-мл. The
    # caller must skip grammar substitution for any paragraph that ends up
    # matching (via normalize_ws) an entry in this set, or the card's own
    # pronoun rules will blindly "fix" a pronoun that was already correct.
    pattern = re.compile(r"GENDER_RULE\(([^)]+)\)(.*?)GENDER_END", re.DOTALL)
    placeholders = []
    out = []
    last_pos = 0
    for m in pattern.finditer(text):
        out.append(text[last_pos : m.start()])
        condition = m.group(1)
        if test_gender_condition(condition, char_config, igroki_rows):
            content = m.group(2).strip()
            idx = len(placeholders)
            placeholders.append(content)
            out.append(f"@@GR{idx}@@")
            if protected_out is not None and re.search(r"\s+(?:and|or)\s+", condition):
                protected_out.add(normalize_ws(content))
        last_pos = m.end()
    out.append(text[last_pos:])
    text = "".join(out)
    for i, ph in enumerate(placeholders):
        text = text.replace(f"@@GR{i}@@", ph)
    return text


def add_paragraph_breaks_around_gender_rule_chains(text):
    # A block-style GENDER_RULE(...)...GENDER_END (its content starting on
    # its OWN line, not inline right after the condition) reads as a
    # self-contained aside and should start a new paragraph relative to
    # whatever plain text precedes/follows it — UNLESS it's directly
    # chained to a neighboring GENDER_RULE tag with nothing between them,
    # in which case the chain is meant to continue as one paragraph (see
    # Чарторыжский's two adjacent "Горихвостов - М" blocks,
    # Персонажи.md:270-275, vs. Раскольниченко's aside in Строганов-мл's
    # card at Персонажи.md:745-747, which follows plain text directly and
    # must NOT merge into it). Applied to raw text before
    # resolve_gender_rules runs; harmless for a fully-dropped branch since
    # split_bio_paragraphs discards empty blocks anyway. Inline tags
    # (condition and content on the same line, e.g. Персонажи.md:85) are
    # deliberately not matched here — they already read as part of the
    # surrounding paragraph and should stay that way.
    block_tag = re.compile(r"GENDER_RULE\([^)]+\)\n.*?\nGENDER_END", re.DOTALL)
    for m in reversed(list(block_tag.finditer(text))):
        start, end = m.start(), m.end()
        before, after = text[:start], text[end:]
        if before and not re.search(r"GENDER_END\n$", before) and not re.search(r"\n\n$", before):
            text = before + "\n\n" + text[start:]
            end += 2
        after = text[end:]
        if after and not re.match(r"\nGENDER_RULE\(", after) and not re.match(r"\n\n", after):
            text = text[:end] + "\n\n" + after
    return text


def strip_gm_info(text):
    return re.sub(r"GM_INFO.*?GM_END\n?", "", text, flags=re.DOTALL)


# ── Персонажи.md parsing ──────────────────────────────────────────────────


def extract_footer(text):
    # Persons.md's leading comment mentions "FOOTER_INFO...FOOTER_END" as
    # documentation, inline in prose. Require the real tags to stand alone
    # on their own line so that mention isn't matched instead.
    m = re.search(r"(?m)^FOOTER_INFO$(.*?)^FOOTER_END$", text, re.DOTALL)
    if not m:
        return []
    lines = [l.strip() for l in m.group(1).split("\n") if l.strip()]
    return lines


def split_character_blocks(text):
    # Drop everything before the first "## " heading (leading comment, FOOTER_INFO).
    first = text.find("\n## ")
    if first == -1:
        return []
    text = text[first + 1 :]
    parts = re.split(r"(?m)^## ", text)
    return [p for p in parts if p.strip()]


def parse_pub_info(block_text):
    # Returns the RAW (still-tagged) PUB_INFO text, not pre-split lines —
    # Строганов-мл's PUB_INFO wraps its opening paragraph in two multi-line
    # GENDER_RULE branches (Персонажи.md:720-725), and splitting into lines
    # before resolving them would shred each tag into fragments with no
    # complete GENDER_RULE(...)...GENDER_END left to match, leaving the raw
    # tag text in the output. Caller must resolve_gender_rules() on the
    # returned text first, then split into lines itself.
    m = re.search(r"PUB_INFO\n(.*?)\nPUB_END", block_text, re.DOTALL)
    if not m:
        return "", ""
    rest = block_text[m.end() :]
    return m.group(1), rest


def parse_heading_and_subtitle(block_text):
    lines = block_text.split("\n")
    heading_line = lines[0].strip()
    m = re.search(r"\s*(\*\(.*?\)\*)\s*$", heading_line)
    paren_suffix = ""
    if m:
        paren_suffix = m.group(1)
        heading_line = heading_line[: m.start()].strip()

    subtitle_lines = []
    i = 1
    while i < len(lines):
        s = lines[i].strip()
        if s == "PUB_INFO":
            break
        if s:
            subtitle_lines.append(s)
        i += 1
    remainder = "\n".join(lines[i:])
    return heading_line, paren_suffix, subtitle_lines, remainder


def split_bio_paragraphs(text):
    # Unlike PUB_INFO (one physical line = one paragraph, per
    # инструкции_по_генерации.md), the free-form biography joins
    # consecutive non-blank source lines into a single paragraph; only a
    # blank line starts a new one. Verified against Горихвостов's "Порою
    # Горихвостову хочется... Порою мечтается..." (3 lines, no blank
    # between, one <p> in the committed card) and Самохвалова's "За кого
    # же выдать дочь?" monologue (8 lines incl. GENDER_RULE branches, no
    # blank between, one <p>).
    #
    # Caller must resolve_gender_rules() on `text` BEFORE calling this, not
    # after splitting. resolve_gender_rules leaves the source's original
    # blank-line structure untouched (see its docstring) — exactly what
    # this function needs to split on. Splitting first would cut through
    # any GENDER_RULE block whose own content spans a blank line
    # (Чарторыжский's Ж branch does: two source paragraphs inside one
    # tag), destroying the tag before it can be resolved.
    blocks = re.split(r"\n\s*\n", text.strip())
    paragraphs = []
    for block in blocks:
        joined = " ".join(l.strip() for l in block.split("\n") if l.strip())
        if joined:
            paragraphs.append(joined)
    return paragraphs


def apply_regex_list(text, pairs):
    for pat, repl in pairs:
        text = re.sub(pat, repl, text)
    return text


def strip_crosspol_phrases(paragraphs):
    out = []
    for p in paragraphs:
        for phrase in CROSSPOL_PHRASES:
            p = p.replace(phrase, "")
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            out.append(p)
    return out


def parse_ref_section(text):
    m = re.search(r"(?m)^ref:(.*)$", text)
    if not m:
        return "", []
    intro = m.group(1).strip()
    rest = text[m.end() :]
    items = []
    for line in rest.split("\n"):
        s = line.strip()
        m2 = re.match(r"^[-*]\s+(.*)$", s)
        if m2:
            items.append(m2.group(1))
    return intro, items


class Character:
    pass


def build_characters(root, filter_key=None):
    with open(os.path.join(root, "Игроки.md"), "r", encoding="utf-8-sig") as f:
        igroki_rows = parse_markdown_table(f.read(), "Игроки")

    with open(
        os.path.join(root, "материалы", "графика", "персонажи", "портреты.md"),
        "r",
        encoding="utf-8-sig",
    ) as f:
        portrait_blocks = parse_portraits(f.read())

    with open(os.path.join(root, "Персонажи.md"), "r", encoding="utf-8-sig") as f:
        persons_text = f.read()

    footer_lines = extract_footer(persons_text)
    blocks = split_character_blocks(persons_text)

    if len(blocks) != len(CHAR_CONFIG):
        print(
            f"ВНИМАНИЕ: в Персонажи.md найдено {len(blocks)} блоков персонажей, "
            f"а в CHAR_CONFIG описано {len(CHAR_CONFIG)}. Персонажи сопоставляются "
            "по позиции, так что при рассинхронизации данные всех персонажей "
            "после несовпадения перепутаны. Обновите CHAR_CONFIG в generate_roles.py "
            "(и, при необходимости, CHAR_CONFIG в generate-cards/generate_cards.py) "
            "прежде чем доверять этому запуску.",
            file=sys.stderr,
        )

    active_inversions = [
        c
        for c in CHAR_CONFIG
        if c["invertible"] and current_gender(c, igroki_rows) != c["default_gender"]
    ]

    characters = []
    for raw_block_text, cfg in zip(blocks, CHAR_CONFIG):
        if filter_key and cfg["igroki_key"] != filter_key:
            continue

        # GM_INFO blocks can appear anywhere (including before PUB_INFO, e.g.
        # a "реклама роли" note) and are stripped globally up front — that's
        # safe since GM_INFO never nests inside GENDER_RULE or vice versa.
        # GENDER_RULE resolution, however, is deliberately NOT done globally
        # here: PUB_INFO/bio/ref chunks each resolve it locally below (bio
        # per blank-line block — see split_bio_paragraphs for why).
        block_text = strip_gm_info(raw_block_text)

        heading_line, paren_suffix, subtitle_lines, remainder = parse_heading_and_subtitle(
            block_text
        )
        # Content from a KEPT GENDER_RULE branch whose condition names more
        # than one character (e.g. "Строганова-младшая - Ж and
        # Раскольниченко - М") is collected here and later exempted from
        # this card's own grammar substitution — see resolve_gender_rules's
        # docstring for why a blind pronoun swap would corrupt it.
        protected = set()

        pub_raw, rest = parse_pub_info(remainder)
        pub_raw = resolve_gender_rules(pub_raw, CHAR_CONFIG, igroki_rows, protected)
        pub_paragraphs = [l.strip() for l in pub_raw.split("\n") if l.strip()]

        ref_marker = re.search(r"(?m)^ref:", rest)
        if ref_marker:
            bio_raw = rest[: ref_marker.start()]
            ref_raw = rest[ref_marker.start() :]
        else:
            bio_raw = rest
            ref_raw = ""
        ref_raw = resolve_gender_rules(ref_raw, CHAR_CONFIG, igroki_rows, protected)

        gender = current_gender(cfg, igroki_rows)
        row = get_igroki_row(igroki_rows, cfg["igroki_key"]) or {}

        def grammar(text):
            if cfg["special_no_grammar"]:
                return text
            # Compound-condition GENDER_RULE content may end up merged into
            # a larger paragraph (with plain text before/after it, joined
            # by split_bio_paragraphs) rather than standing alone, so an
            # exact whole-paragraph match against `protected` can't be
            # relied on. Swap any protected substring for an opaque token
            # before running substitutions, then restore it verbatim after
            # — this protects it wherever it lands, regardless of paragraph
            # boundaries.
            working = text
            local = []
            for i, content in enumerate(protected):
                if content and content in working:
                    token = f"@@PROT{i}@@"
                    working = working.replace(content, token)
                    local.append((token, content))
            out = working
            for inv_cfg in active_inversions:
                out = apply_regex_list(out, inv_cfg["surname_regex"])
                if inv_cfg is cfg:
                    out = apply_regex_list(out, inv_cfg["primary_regex"])
            for token, content in local:
                out = out.replace(token, content)
            return out

        heading_line = grammar(heading_line)
        subtitle_lines = [grammar(s) for s in subtitle_lines]
        pub_paragraphs = [grammar(p) for p in pub_paragraphs]

        bio_raw = add_paragraph_breaks_around_gender_rule_chains(bio_raw)
        bio_raw = resolve_gender_rules(bio_raw, CHAR_CONFIG, igroki_rows, protected)
        bio_paragraphs = split_bio_paragraphs(bio_raw)
        bio_paragraphs = [grammar(p) for p in bio_paragraphs]

        occupied = bool(row.get("игрок - контакт", "").strip()) and row.get(
            "игрок - контакт", ""
        ).strip() not in ("-", "Роль свободна")
        if occupied:
            pub_paragraphs = strip_crosspol_phrases(pub_paragraphs)

        имя = row.get("имя", "").strip()
        имя = имя if имя and имя != "-" else ""

        display_name = heading_line
        if имя:
            display_name += f", {имя}"

        ref_intro, ref_items = parse_ref_section(ref_raw)

        img_tag = find_portrait(cfg, gender, portrait_blocks)

        contact_field = row.get("игрок - контакт", "").strip()
        status_field = row.get("статус заявки", "").strip()
        if occupied:
            contact_line = f"Игрок: {contact_field}"
        elif status_field:
            contact_line = status_field
        else:
            contact_line = ""

        ch = Character()
        ch.igroki_key = cfg["igroki_key"]
        # The output filename follows the character's currently-declined
        # surname, not the fixed Игроки.md key — e.g. Строганов-мл inverted
        # to Ж writes Строганова-мл.html, matching how the (previously
        # hand-generated) persona cards have always been named.
        ch.filename_default = cfg["filename_default"]
        ch.filename_inverted = cfg["filename_inverted"]
        if cfg["invertible"] and gender != cfg["default_gender"]:
            ch.file_key = cfg["filename_inverted"]
        else:
            ch.file_key = cfg["filename_default"]
        ch.heading = heading_line
        ch.paren_suffix = paren_suffix
        ch.display_name = display_name
        ch.subtitle = ", ".join(subtitle_lines)
        ch.pub_paragraphs = pub_paragraphs
        ch.bio_paragraphs = bio_paragraphs
        ch.ref_intro = ref_intro
        ch.ref_items = ref_items
        ch.img_tag = img_tag
        ch.contact_line = contact_line
        characters.append(ch)

    run_cross_reference_diagnostics(characters, active_inversions)

    return characters, footer_lines


def common_stem(a, b, min_len=4):
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return a[:n] if n >= min_len else None


def run_cross_reference_diagnostics(characters, active_inversions):
    # Mechanical stand-ins for "does this read correctly" — the script
    # can't judge grammar, but it can notice the two situations most
    # likely to hide a missed gender substitution: the character's OWN
    # un-inverted surname form still present anywhere (a near-certain
    # miss), and any mention of an inverted character inside someone
    # ELSE's card (not necessarily wrong, but exactly where a stray
    # pronoun belonging to them is most likely to have been missed — see
    # this file's module docstring for the Раскольниченко/Строганов-мл
    # incident that prompted this).
    scan_text = {
        ch.igroki_key: "\n".join(
            [ch.heading, ch.subtitle] + ch.pub_paragraphs + ch.bio_paragraphs
        )
        for ch in characters
    }

    for cfg in active_inversions:
        default_form = cfg["nominative_default"]
        inverted_form = cfg["nominative_inverted"]
        if default_form == inverted_form:
            continue  # indeclinable name (e.g. Валемонте) - nothing to tell apart

        # Leftover-form warning: the bare nominative catches an unconverted
        # mention written in the base form, and each surname_regex FROM
        # pattern catches a still-unconverted DECLINED form specifically
        # (genitive/dative/etc) — every one of these patterns is supposed
        # to have been substituted away by grammar(), everywhere, so any
        # literal match remaining is either a genuinely missed mention or
        # (much rarer) a false positive from protected/ref: text that's
        # deliberately exempt from substitution.
        leftover_patterns = [re.escape(default_form)] + [
            pat for pat, _ in cfg["surname_regex"]
        ]
        for ch in characters:
            text = scan_text[ch.igroki_key]
            for pat in leftover_patterns:
                m = re.search(pat, text)
                if not m:
                    continue
                start, end = max(0, m.start() - 25), min(len(text), m.end() + 25)
                snippet = text[start:end].replace("\n", " ⏎ ")
                diag(
                    "leftover_form",
                    f'{cfg["igroki_key"]} в карточке "{ch.igroki_key}": '
                    f"«{pat}» — …{snippet}…",
                )
                break  # one hit per card is enough signal, avoid pile-up

        # Co-mention info: broader stem match (catches declined forms like
        # "Строганова-младшего" or "Ласневскому" that don't literally equal
        # either nominative spelling) - not proof of a bug, just the exact
        # spot where a missed pronoun for the OTHER character is most
        # likely, so it's worth a human's eyes regardless of whether the
        # surname form itself looks converted.
        stem = cfg["diag_stem"] or common_stem(default_form, inverted_form)
        if not stem:
            continue
        for ch in characters:
            if ch.igroki_key == cfg["igroki_key"]:
                continue
            if stem in scan_text[ch.igroki_key]:
                diag("co_mention", f'{cfg["igroki_key"]} — карточка "{ch.igroki_key}"')


# ── Inline markdown → HTML (bold/italic/links) ────────────────────────────


def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_md_to_html(s):
    s = html_escape(s)
    s = re.sub(r"&lt;br\s*/?&gt;", "<br>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def paren_suffix_to_html(suffix):
    if not suffix:
        return ""
    inner = suffix.strip("*")
    return f" <em>{inner}</em>"


# ── public/Роли.md ─────────────────────────────────────────────────────


def render_roles_md(characters, footer_lines):
    out = ["<!-- generated from `Персонажи.md` -->", "", "# Роли", ""]
    for ch in characters:
        heading = ch.display_name + (f" {ch.paren_suffix}" if ch.paren_suffix else "")
        out.append(f"## {heading}")
        out.append(f"*{ch.subtitle}*")
        out.append("")
        for p in ch.pub_paragraphs:
            out.append(p)
            out.append("")
        if ch.img_tag:
            out.append(ch.img_tag)
            out.append("")
        if ch.contact_line:
            out.append(f"*{ch.contact_line}*")
            out.append("")
        out.append("---")
        out.append("")
    for line in footer_lines:
        out.append(line)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# ── public/Роли.html ────────────────────────────────────────────────────

ROLES_HTML_CSS = """    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: Georgia, "Times New Roman", serif;
      color: #1a1a1a;
      font-size: 10pt;
      line-height: 1.3;
      padding: 10mm;
    }
    h1 { font-size: 16pt; font-weight: 700; text-align: center; margin-bottom: 6mm; }
    h2 { font-size: 11.5pt; font-weight: 700; margin-bottom: 1mm; }
    .subtitle { font-style: italic; margin-bottom: 2mm; }
    p { margin-bottom: 1.5mm; text-align: justify; }
    .contact { font-style: italic; margin-top: 1mm; }
    section.character { break-inside: avoid; page-break-inside: avoid; margin-bottom: 4mm; padding-bottom: 3mm; border-bottom: 0.5pt solid #999; }
    section.character:last-of-type { border-bottom: none; }
    @page { size: A4; margin: 12mm 15mm; }"""


def render_roles_html(characters):
    sections = []
    for ch in characters:
        heading = html_escape(ch.display_name) + paren_suffix_to_html(ch.paren_suffix)
        paras = "\n    ".join(
            f"<p>{inline_md_to_html(p)}</p>"
            for p in ch.pub_paragraphs
            if not p.startswith("На игре предстоит")
        )
        contact = (
            f'\n    <p class="contact">{html_escape(ch.contact_line)}</p>'
            if ch.contact_line
            else ""
        )
        sections.append(
            f"""  <section class="character">
    <h2>{heading}</h2>
    <p class="subtitle">{inline_md_to_html(ch.subtitle)}</p>
    {paras}{contact}
  </section>"""
        )
    body = "\n\n".join(sections)
    return f"""<!-- generated from `Персонажи.md` -->
<!DOCTYPE html>
<html lang="ru">

<head>
  <meta charset="utf-8">
  <title>Роли</title>
  <style>
{ROLES_HTML_CSS}
  </style>
</head>

<body>
  <h1>Роли</h1>

{body}
</body>

</html>
"""


# ── public/персонажи/<name>.html ──────────────────────────────────────────

PERSONA_CSS = """* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: Georgia, "Times New Roman", serif; color:#1a1a1a; font-size:11pt; line-height:1.45; }
body { margin:10mm; }
@media print { body { margin:0; } }
@media print { img.portrait { opacity:0.5; filter:contrast(1.5); } }
h1 { font-size:16pt; margin-bottom:1mm; }
.subtitle { font-style:italic; margin-bottom:3mm; color:#333; }
img.portrait { float:right; margin:0 0 4mm 5mm; max-width:170px; }
p { margin-bottom:2.2mm; text-align:justify; }
h2.section { clear:both; font-size:12.5pt; margin:3mm 0 2mm; }
ul { margin-left:6mm; margin-bottom:2mm; }
li { margin-bottom:1mm; }"""

PERSONA_PAGE_CSS = "@page { size:A4; margin:5mm; }"

STARBREAK_CSS = ".starbreak { text-align:center; margin:3mm 0; color:#666; }"


def portrait_img_to_persona_tag(img_tag):
    # Роли.md/портреты.md <img> tags carry width="400"; persona cards use a
    # bare <img class="portrait" src=... alt=...> (sized via CSS instead).
    src_m = re.search(r'src="([^"]*)"', img_tag)
    alt_m = re.search(r'alt="([^"]*)"', img_tag)
    src = src_m.group(1) if src_m else ""
    alt = alt_m.group(1) if alt_m else ""
    return f'<img class="portrait" src="{src}" alt="{alt}">'


def render_bio_paragraph(p):
    # "🙙" marks a scene break in a handful of cards (Валемонте, Ледонтова)
    # and gets a dedicated centered style rather than plain justified prose.
    if p.strip() == "🙙":
        return '<p class="starbreak">🙙</p>'
    return f"<p>{inline_md_to_html(p)}</p>"


def render_persona_html(ch):
    title = html_escape(ch.heading)
    h1 = html_escape(ch.display_name) + paren_suffix_to_html(ch.paren_suffix)
    pub_html = "\n  ".join(f"<p>{inline_md_to_html(p)}</p>" for p in ch.pub_paragraphs)
    bio_html = "\n  ".join(render_bio_paragraph(p) for p in ch.bio_paragraphs)
    portrait_html = (
        f"  {portrait_img_to_persona_tag(ch.img_tag)}\n" if ch.img_tag else ""
    )
    ref_html = ""
    if ch.ref_items:
        intro_html = f"  <p>{inline_md_to_html(ch.ref_intro)}</p>\n" if ch.ref_intro else ""
        items_html = "\n    ".join(f"<li>{inline_md_to_html(i)}</li>" for i in ch.ref_items)
        ref_html = f"""
{intro_html}  <h2 class="section">Для вдохновения</h2>
  <ul>
    {items_html}
  </ul>"""

    uses_starbreak = any(p.strip() == "🙙" for p in ch.bio_paragraphs)
    full_body = h1 + pub_html + bio_html + ref_html
    extra_css_lines = []
    if "<strong>" in full_body:
        extra_css_lines.append("strong { font-weight:700; }")
    if "<em>" in full_body:
        extra_css_lines.append("em { font-style:italic; }")
    css = PERSONA_CSS
    if uses_starbreak:
        css += "\n" + STARBREAK_CSS
    if extra_css_lines:
        css += "\n" + "\n".join(extra_css_lines)
    css += "\n" + PERSONA_PAGE_CSS

    return f"""<!-- generated from `Персонажи.md` -->
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
{portrait_html}  <h1>{h1}</h1>
  <p class="subtitle">{inline_md_to_html(ch.subtitle)}</p>
  {pub_html}

  {bio_html}
{ref_html}
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Write into this directory instead of public/ (for dry-run review).",
    )
    parser.add_argument("character", nargs="?", default=None)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    characters, footer_lines = build_characters(root, filter_key=args.character)

    out_root = os.path.abspath(args.out_dir) if args.out_dir else os.path.join(root, "public")

    roles_md = render_roles_md(characters, footer_lines)
    roles_html = render_roles_html(characters)

    os.makedirs(out_root, exist_ok=True)
    if not args.character:
        roles_md_path, _ = resolve_output_path(os.path.join(out_root, "Роли.md"), root)
        with open(roles_md_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(roles_md)
        roles_html_path, _ = resolve_output_path(os.path.join(out_root, "Роли.html"), root)
        with open(roles_html_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(roles_html)
        print(os.path.relpath(roles_md_path, root))
        print(os.path.relpath(roles_html_path, root))

    persona_dir = os.path.join(out_root, "персонажи")
    os.makedirs(persona_dir, exist_ok=True)
    for ch in characters:
        html = render_persona_html(ch)
        path, protected_path = resolve_output_path(
            os.path.join(persona_dir, f"{ch.file_key}.html"), root
        )
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print(os.path.relpath(path, root))

        # Stale-file cleanup: if the character's gender flipped since the
        # last run, the old declined filename is now orphaned — remove it
        # (mirrors generate-cards' same cleanup for CARD_BEGIN outputs).
        for stale_key in (ch.igroki_key, ch.filename_default, ch.filename_inverted):
            stale_path = os.path.join(persona_dir, f"{stale_key}.html")
            if (
                stale_path != path
                and stale_path != protected_path
                and os.path.exists(stale_path)
            ):
                os.remove(stale_path)

    print_diagnostics()


if __name__ == "__main__":
    sys.exit(main())

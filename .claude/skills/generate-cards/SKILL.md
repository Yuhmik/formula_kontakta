---
name: generate-cards
description: Regenerate card files from CARD_BEGIN/CARD_END blocks in source .md files. Use whenever the user types /generate-cards, mentions regenerating or updating cards, or has just edited a CARD_BEGIN block and needs the output file refreshed. Optionally accepts a card name to update only that one card.
---

Extract all `CARD_BEGIN(Name, path/, style[, copies[, columns]]) … CARD_END` blocks from source .md files and write each card to `path/Name.html`.

`style` selects the visual template and is one of:
- `document` – styling of an in-universe historical document: a printed artifact that exists inside the game world (letter, notice, printed card) – aged paper, Old Standard TT.
- `handwritten` – the same in-universe artifact, but handwritten (Caveat script): a character's draft, journal, or observation notes.
- `reference` – a meta-text addressed to the player, игротехник, or GM as a real person, not to the character. Nothing rendered as `reference` exists inside the game world – it's rules/procedure, not fiction, so it carries no period styling: clean tables and lists, readable on screen or print.

`copies` (optional, default 1) repeats the same card `copies` times in a grid on the page, for printing one sheet and cutting it into several identical copies (short notes handed to multiple players). Copies are separated by shared dashed cut lines (not a box around each copy) – a single line between each pair of neighboring copies, crossing into a "+" wherever a row division meets a column division. Text sits 1cm from every cut line and 1cm from the paper edge, the same distance on every side. If more copies are requested than fit on one sheet, the grid simply continues onto the next printed page.

`columns` (optional, default 2, only meaningful when `copies` > 1) sets how many columns the grid uses. Short notes read fine at 2; a longer card (several paragraphs) usually needs `columns=1` so each copy has the full page width – set it explicitly per card, there's no automatic detection by text length.

`CARD_BEGIN` is a general-purpose mechanism, use it to generate any card-like content from a master .md source; the pipeline gives you the style templates, HTML generation, gender/name substitution, and the `copies`/`columns` print grid.

**Gender-inversion word forms – SurnameRegex vs PrimaryRegex:** in `generate_cards.py`'s `CHAR_CONFIG`, `primary_regex` fires only on the character's own card (matched via `card_key` against the card name); `surname_regex` fires on every card. This isn't a difference in what kind of gender rule applies – it's blast radius. `primary_regex` holds generic pronouns (`\bон\b`, `\bего\b`, …) that occur constantly and usually refer to someone else entirely; applied globally they'd corrupt unrelated pronouns in other characters' cards. `surname_regex` holds specific tokens (surnames, or a distinctive word form like `занемогла` → `занемог`) unlikely to collide with unrelated text, so it's safe everywhere. When a gender-dependent word form can appear in *other* characters' cards (e.g. Ласневская's illness described in Пирогов's medical journal), put it in `surname_regex`, not `primary_regex`, and fix it once at the pipeline level rather than hand-wrapping every occurrence in `GENDER_RULE(...)...GENDER_END` in the source `.md`.

## Invocation

- `/generate-cards` — regenerate all cards
- `/generate-cards <CardName>` — regenerate only the named card (e.g. `/generate-cards Контакт`)

## Default: run the script

Run from the project root:

```
python .claude/skills/generate-cards/generate_cards.py [CardName]
```

Omit `[CardName]` to regenerate every card. If files already existed they were overwritten with the current source content — that is the expected behaviour.

Check the script's full output every time, including diagnostics (grouped by type — see its module-level `DIAGNOSTICS`/`print_diagnostics`). Never just relay these to the user as-is: read the specific card/text they point at, and come back with either a fix already drafted or a concrete finding, not a raw log dump.

- **"GENDER_RULE ссылается на персонажа, которого нет в CHAR_CONFIG"** — always a bug. Read the named condition in the source `.md`: if it's a typo of an existing character's name, propose fixing the source; if it's a genuinely new invertible character, draft the `CHAR_CONFIG` entry for them.
- **"Похоже, пропущена гендерная замена"** — read the flagged card and find the un-inverted form in context. Draft the specific `surname_regex` pair (or compound phrase, for a cross-reference to another character's card — see `.claude/skills/generate-roles/generate_roles.py`'s docstring for the same class of issue there) and propose adding it to that character's `CHAR_CONFIG` entry.
- **"Целевой файл уже существует и помечен как `<!-- original -->`"** — the script refused to overwrite a hand-authored file and wrote to `*_conflict.html` instead (see `resolve_output_path`). This means a `CARD_BEGIN`'s destination path collides with a real hand-written document — read both files and figure out which is right: fix the `CARD_BEGIN(name, path/, ...)` in the source `.md` if the card was pointed at the wrong path/name, or rename/move the hand-authored file if it's the one in the way. Delete the `*_conflict.html` once resolved; don't leave it sitting next to the original.

Propose each fix as a concrete edit to `generate_cards.py` (not a description of what should change), apply it once the user confirms, and re-run the script (for that card, or all of them) to verify the diagnostic is actually gone before reporting the run as done.

## When to fall back to manual generation

`generate_cards.py` is a deterministic, non-LLM implementation of the rules above: a fixed table of word-form substitutions (`CHAR_CONFIG`), not real language understanding. It cannot correctly gender a brand-new sentence or cross-reference it hasn't seen a matching pattern for — see the script's own module docstring. Generate a card by hand (applying the rules above and "Смена гендера персонажа" in `инструкции_по_генерации.md` yourself) instead when:

- a new invertible character is added — add them to `CHAR_CONFIG` in `generate_cards.py` first (mirroring an existing entry), or the script won't know about them at all;
- a diagnostic fires that you can't resolve by adding a `CHAR_CONFIG` entry/pair;
- a card needs markdown syntax the converter doesn't support (see "Разметка внутри карточки" in `инструкции_по_генерации.md` for exactly what's handled — bold/italic, lists, tables, fenced code, `<br>`, raw HTML lines, `<!-- -->` comments, and nothing beyond that).

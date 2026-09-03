---
name: generate-roles
description: Generate or refresh public/Роли.md (the public character list), public/Роли.html (its print-ready A4 twin, no portraits), and public/персонажи/<персонаж>.html (one print-ready A4 personal character card per player) from Персонажи.md/Игроки.md. Use whenever the user types /generate-roles, asks to regenerate the role list, the printable role list, or personal character cards, rebuild Роли.md, Роли.html or the files in public/персонажи/, or has just edited Персонажи.md or Игроки.md and needs the public documents refreshed.
---

Generate `public/Роли.md`, `public/Роли.html`, and one HTML file per character in `public/персонажи/` from the project source files.

## Default: run the script

Run from the project root:

```
python .claude/skills/generate-roles/generate_roles.py
```

Pass a character's `Игроки.md` key (e.g. `Строганов-мл`) to regenerate only that one character's card, skipping `Роли.md`/`Роли.html`.

Check the script's full output every time — not just the generated-file list, but a block-count mismatch warning (printed to stderr, before generation even starts) and diagnostics (printed after, grouped by type — see the script's module docstring and `print_diagnostics`). Never just relay these to the user as-is: read the specific text they point at in `Персонажи.md`, and come back with either a fix already drafted or a concrete finding, not a raw log dump.

- **Block-count mismatch** (stderr, "в Персонажи.md найдено N блоков... а в CHAR_CONFIG описано M") — a character was added or removed in `Персонажи.md`. Every character after the mismatch is now paired with the wrong `CHAR_CONFIG` entry by position, so the whole run's output is unreliable until this is fixed. Draft the matching `CHAR_CONFIG` addition/removal (an existing entry is a template) and propose it before trusting anything else this run produced.
- **"GENDER_RULE ссылается на персонажа, которого нет в CHAR_CONFIG"** — always a bug. Read the named condition in `Персонажи.md`: if it's a typo of an existing character's name, propose fixing the source; if it's a genuinely new invertible character, draft the `CHAR_CONFIG` entry for them.
- **"Похоже, пропущена гендерная замена"** — read the flagged card and find the un-inverted form in context. Draft the specific `surname_regex` pair (or compound phrase, if it's a cross-reference — see the Раскольниченко/Строганов-мл case in the script's docstring for the pattern) and propose adding it to that character's `CHAR_CONFIG` entry.
- **"Инвертированный персонаж упомянут в чужой карточке"** — read that paragraph and check pronoun/adjective agreement yourself. If it's already correct, say so and move on. If it's wrong, draft the missing pair the same way as above.
- **"Целевой файл уже существует и помечен как `<!-- original -->`"** — the script refused to overwrite a hand-authored file and wrote to `*_conflict.html` instead (see `resolve_output_path`). This normally means a character's row in `Игроки.md` was renamed/retyped in a way that makes its computed filename collide with an unrelated real document — read both files and figure out which is right; don't leave the `*_conflict.html` sitting there once resolved.

Propose each fix as a concrete edit to `generate_roles.py` (not a description of what should change), apply it once the user confirms, and re-run the script to verify the diagnostic is actually gone before reporting the run as done.

## When to fall back to manual generation

`generate_roles.py` is a deterministic, non-LLM implementation: a fixed table of word-form substitutions (`CHAR_CONFIG`), not real language understanding. It cannot correctly gender a brand-new sentence, or a new cross-reference to an invertible character, that it hasn't seen a matching pattern for — see the script's own module docstring for the specific incident (Раскольниченко/Строганов-мл) that shaped this. Fall back to the manual process below (Steps 1–6, which use your own understanding of Russian instead of pattern matching) when:

- a new character is added to `Персонажи.md` — the script pairs character blocks to `CHAR_CONFIG` by position; add a matching entry there first, or it will warn about a count mismatch and misalign;
- a diagnostic fires that you can't resolve by adding a `CHAR_CONFIG` entry/pair;
- you need to hand-fix or double-check just ONE flagged character's card — Step 5 below can be applied to a single character without a full regeneration.

## Manual generation (fallback)

### Step 1 – Read the generation rules

Read `инструкции_по_генерации.md` in full. Authoritative sections:

- "Генерация публичного списка ролей `public/Роли.md`" – what goes into the role list and in what order.
- "Печатная версия `public/Роли.html`" – how the print twin of the role list differs from the `.md` version.
- "Персонажные карточки" – structure of each player's personal card in `public/персонажи/`.
- "Смена гендера персонажа" – the complete gender-adaptation ruleset, shared by all three outputs.

Apply these rules as written – do not rely on remembered or cached versions.

### Step 2 – Read the source data

Read these files in full:

- **`Персонажи.md`** — for each character: the header block (name, role, age lines that precede `PUB_INFO`), the `PUB_INFO`…`PUB_END` text, the `FOOTER_INFO`…`FOOTER_END` block (used at the end of `Роли.md`), the untagged biography text that follows `PUB_END` (used in the personal card – everything except `GM_INFO`…`GM_END` blocks, with `GENDER_RULE(...)`…`GENDER_END` blocks resolved per their condition), and the trailing `ref:` line plus its bullet list of links (used as the card's closing "Для вдохновения" section – skip this `ref:` line if it sits inside a `GM_INFO`…`GM_END` block instead of bare, as with Ласневская).
- **`Игроки.md`** — for each character: `пол` (gender for this run), `имя` (player name, if filled), contact handle (`игрок – контакт`), and application status (`статус заявки`).
- **`материалы/графика/персонажи/портреты.md`** — for each character select the portrait block whose heading matches the character name and gender marker (`М` or `Ж`) from `Игроки.md`. Characters with only one gender variant always use that variant.

### Step 3 – Generate `public/Роли.md`

Apply the rules from "Генерация публичного списка ролей" and "Смена гендера персонажа". Write the result to `public/Роли.md`.

The first line of the output must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

### Step 4 – Generate `public/Роли.html`

Same character order, subtitles, `PUB_INFO` paragraphs, and contact/status line as `public/Роли.md` from Step 3 – reuse that text verbatim rather than recomputing it, with these differences:

- drop every portrait `<img>` – text only, no images.
- drop the entire `PUB_INFO` paragraph (source line) that starts with "На игре предстоит..." – not just its first sentence. If that same line/paragraph runs on with more sentences after it (as with Ласневский: "На игре предстоит... Ему не придётся... Зато всё..." all on one source line), drop all of them together, since they're still part of the story-arc paragraph and not needed in this quick-reference sheet.
- drop the closing `FOOTER_INFO`…`FOOTER_END` notes section entirely – no footer.
- lay it out for A4 print (`@page { size: A4; }`), compact and plain – no in-universe period styling, this is a working reference document, not a fictional artifact (comparable in spirit to the `reference` style in `.claude/skills/generate-cards/SKILL.md`). Keep each character's block from breaking across a page (`break-inside: avoid`) where reasonably possible.

The first line of the output must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

### Step 5 – Generate `public/персонажи/<персонаж>.html`

Per "Персонажные карточки", build one card per character and write each to its own file `public/персонажи/<персонаж>.html`, where `<персонаж>` is that character's value in the `персонаж` column of `Игроки.md`. Each file is a single A4 print page (`@page { size: A4; }`).

Each card:

1. The portrait is the very first element on the page (before the heading), floated to the top-right corner. The heading, role/age subtitle, `PUB_INFO` paragraphs (reused verbatim from Step 3), and the biography text from point 2 below all flow as normal body content after it, wrapping around it on the left for as long as they're shorter than the image – don't insert any divider or heading right after the portrait, or the wrap breaks early. No caption or attribution line under the image, and no player contact/status line on the card (the card is handed directly to that player, who doesn't need to be told their own handle).
2. The untagged biography material for that character from `Персонажи.md`:
   - starts right after `PUB_END` (skipping over the optional `GM_INFO`…`GM_END` block that may sit directly after it), runs up to the next `## ` character heading
   - strips every `GM_INFO`…`GM_END` block entirely
   - resolves every `GENDER_RULE(condition)`…`GENDER_END` block: keep the enclosed text only if `condition` holds for this run (check each named character's `пол` in `Игроки.md`; support compound `and`/`or` conditions exactly as written in `Персонажи.md`); the `GENDER_RULE(...)`/`GENDER_END` tags themselves are never kept
   - applies the full "Смена гендера персонажа" ruleset to the surviving text – both for the card's own character when their gender is inverted this run, and for any other character named within that text (e.g. surname case forms)
3. Ends with a "Для вдохновения" section built from the character's bare (non-`GM_INFO`) `ref:` line and the bullet list of links directly under it: any text after `ref:` becomes an intro line before the list, an empty `ref:` means the section is just the list. `GENDER_RULE(...)`/`GENDER_END` blocks inside this bullet list are still resolved for inclusion (same condition-check as point 2) – some ref entries only make sense for one gender variant of a character – but no grammatical gender substitution is applied to the surviving text itself: these are links to real people/films/books outside the game. No `<hr>` or blank divider between the biography and this heading – it follows directly after the last paragraph.

Use simple, print-friendly HTML – no in-universe period styling, since this is a practical reference document handed to a real player, not a fictional artifact (comparable in spirit to the `reference` style in `.claude/skills/generate-cards/SKILL.md`): readable serif body text, the character's name/role as a heading, portrait floated top-right with text flowing around it (no caption, no contact line).

The first line of each file must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

### Step 6 – Report

Report `public/Роли.md`, `public/Роли.html`, and the list of generated files in `public/персонажи/` to the user.

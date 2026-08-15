---
name: generate-roles
description: Generate or refresh public/Роли.md (the public character list), public/Роли.html (its print-ready A4 twin, no portraits), and public/Карточки_персонажей.html (personal character cards, one page per player) from Персонажи.md/Игроки.md. Use whenever the user types /generate-roles, asks to regenerate the role list, the printable role list, or personal character cards, rebuild Роли.md, Роли.html or Карточки_персонажей.html, or has just edited Персонажи.md or Игроки.md and needs the public documents refreshed.
---

Generate `public/Роли.md`, `public/Роли.html`, and `public/Карточки_персонажей.html` from the project source files.

## Step 1 – Read the generation rules

Read `инструкции_по_генерации.md` in full. Authoritative sections:

- "Генерация публичного списка ролей `public/Роли.md`" – what goes into the role list and in what order.
- "Печатная версия `public/Роли.html`" – how the print twin of the role list differs from the `.md` version.
- "Персонажные карточки" – structure of each player's personal card in `public/Карточки_персонажей.html`.
- "Смена гендера персонажа" – the complete gender-adaptation ruleset, shared by all three outputs.

Apply these rules as written – do not rely on remembered or cached versions.

## Step 2 – Read the source data

Read these files in full:

- **`Персонажи.md`** — for each character: the header block (name, role, age lines that precede `PUB_INFO`), the `PUB_INFO`…`PUB_END` text, the `FOOTER_INFO`…`FOOTER_END` block (used at the end of `Роли.md`), the untagged biography text that follows `PUB_END` (used in the personal card – everything except `GM_INFO`…`GM_END` blocks, with `GENDER_RULE(...)`…`GENDER_END` blocks resolved per their condition), and the trailing `ref:` line plus its bullet list of links (used as the card's closing "Для вдохновения" section – skip this `ref:` line if it sits inside a `GM_INFO`…`GM_END` block instead of bare, as with Ласневская).
- **`Игроки.md`** — for each character: `пол` (gender for this run), `имя` (player name, if filled), contact handle (`игрок – контакт`), and application status (`статус заявки`).
- **`материалы/графика/персонажи/портреты.md`** — for each character select the portrait block whose heading matches the character name and gender marker (`М` or `Ж`) from `Игроки.md`. Characters with only one gender variant always use that variant.

## Step 3 – Generate `public/Роли.md`

Apply the rules from "Генерация публичного списка ролей" and "Смена гендера персонажа". Write the result to `public/Роли.md`.

The first line of the output must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

## Step 4 – Generate `public/Роли.html`

Same character order, subtitles, `PUB_INFO` paragraphs, and contact/status line as `public/Роли.md` from Step 3 – reuse that text verbatim rather than recomputing it, with these differences:

- drop every portrait `<img>` – text only, no images.
- drop the entire `PUB_INFO` paragraph (source line) that starts with "На игре предстоит..." – not just its first sentence. If that same line/paragraph runs on with more sentences after it (as with Ласневский: "На игре предстоит... Ему не придётся... Зато всё..." all on one source line), drop all of them together, since they're still part of the story-arc paragraph and not needed in this quick-reference sheet.
- drop the closing `FOOTER_INFO`…`FOOTER_END` notes section entirely – no footer.
- lay it out for A4 print (`@page { size: A4; }`), compact and plain – no in-universe period styling, this is a working reference document, not a fictional artifact (comparable in spirit to the `reference` style in `.claude/skills/generate-cards/SKILL.md`). Keep each character's block from breaking across a page (`break-inside: avoid`) where reasonably possible.

The first line of the output must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

## Step 5 – Generate `public/Карточки_персонажей.html`

Per "Персонажные карточки", build one card per character and assemble them into a single HTML file, one character per printed page (`page-break-after: always` on every card except the last, so print output splits at character boundaries).

Each card:

1. Starts with that character's full block already produced for `public/Роли.md` in Step 3 (heading, role/age subtitle, `PUB_INFO` paragraphs, portrait, player contact/status line) – reuse it verbatim rather than recomputing it.
2. Followed by the untagged biography material for that character from `Персонажи.md`:
   - starts right after `PUB_END` (skipping over the optional `GM_INFO`…`GM_END` block that may sit directly after it), runs up to the next `## ` character heading
   - strips every `GM_INFO`…`GM_END` block entirely
   - resolves every `GENDER_RULE(condition)`…`GENDER_END` block: keep the enclosed text only if `condition` holds for this run (check each named character's `пол` in `Игроки.md`; support compound `and`/`or` conditions exactly as written in `Персонажи.md`); the `GENDER_RULE(...)`/`GENDER_END` tags themselves are never kept
   - applies the full "Смена гендера персонажа" ruleset to the surviving text – both for the card's own character when their gender is inverted this run, and for any other character named within that text (e.g. surname case forms)
3. Ends with a "Для вдохновения" section built from the character's bare (non-`GM_INFO`) `ref:` line and the bullet list of links directly under it: any text after `ref:` becomes an intro line before the list, an empty `ref:` means the section is just the list. No gender substitution here – these are links to real people/films/books outside the game.

Use simple, print-friendly HTML – no in-universe period styling, since this is a practical reference document handed to a real player, not a fictional artifact (comparable in spirit to the `reference` style in `.claude/skills/generate-cards/SKILL.md`): readable serif body text, the character's name/role as a heading, portrait image inline, one `<section>`/page per character.

The first line of the output must be the origin marker, followed by an empty line:

```
<!-- generated from `Персонажи.md` -->
```

## Step 6 – Report

Report all three generated files to the user.

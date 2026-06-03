# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Формула контакта" — live-action roleplay (LARP), 2-day cottage-hosted event for 10–20 players. Small organizing team (2–4 people). All materials are in Russian; this is a creative writing / game-design project, not a software project. There are no build, test, or lint commands.

**Premise:** 1835, a rural Russian estate. An alien spacecraft makes an emergency landing; the aliens hide in local animals while the gentry investigates what they believe to be supernatural events. Players on both sides manage their goals without initially understanding each other.

## File structure

| File | Purpose |
|------|---------|
| `public/intro.md` | Player-facing premise text — uses pre-1918 archaic Russian orthography intentionally |
| `public/Роли.md` | Public character list players use to choose roles - updated automatically from Персонажи.md |
| `public/Атмосфера.md` | Atmosphere, historical background, costuming notes and references for players |
| `public/Таинственное.md` | Rules for the alien contact/possession mechanic - updated automatically from Пришельцы.md |
| `Персонажи.md` | GM reference: full character sheets with mechanics, objectives, resources |
| `Пришельцы.md` | GM reference: full aliens specification |
| `черновики/опрос.md` | Player comfort/consent survey |
| `черновики/Марица взаимодействий.xlsx` | Character relationship/interaction matrix |

Directories: `public/` — all public documents for players; `материалы/` — research, visual assets and sound files; `черновики/` — draft documents.

## Language rules

- All materials are written in **modern Russian** spelling.
- **Exception: `intro.md` only** uses pre-1918 archaic orthography (е → ѣ, etc.) for deliberate period atmosphere. Do not "correct" these spellings — they are intentional.
- When editing `intro.md`, preserve the archaic orthography throughout.

## Character sheet format (Персонажи.md)

Each character entry follows this structure:
- Brief biography and personality
- (optional) **Деньги:** X — monetary resources available
- (optional) **Поручения (действия):** — list of mechanical actions the character can perform during the LARP
- Goals, motivations, relationships, and moral dilemmas

When adding or editing a character, keep all these fields. `Персонажи.md` is full characters info for GM and is a source for auto-generated public `Список ролей.md` and personal character sheet for each player.

## Alien contact mechanic (core design)

Defined in `Пришельцы.md`. Key constraints to respect when writing related content:
- Aliens inhabit local animals, marked with ribbons
- Aliens can briefly take control of a human's mind (with ethical limits built into their nature)
- The controlled human has partial or full memory loss afterward
- Aliens need fuel: either 5 barrels of oil or spirit, or a safe high-altitude launch point
- This mechanic creates unreliable narration and dual-role play for "possessed" characters

## Historical period

Russia, 1835. Relevant details the writing draws on: Russian Empire Table of Ranks, provincial landowner society, Church hierarchy (благочинный = rural church supervisor), moonshining under state monopoly, serfdom, aftermath of the Polish uprising (1830–31) and the Decembrist movement. When expanding historical flavor, keep this period and context.

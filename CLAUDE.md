# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Never use em dash (—) in any texts. Use en dash (–) instead.

## Project

"Формула контакта" — live-action roleplay (LARP), 2-day cottage-hosted event for 17 players (+2 playing masters, +1 master assistant). Small organizing team (2–4 people). All materials are in Russian; this is a creative writing / game-design project, not a software project. There are no build, test, or lint commands, only a few `.claude/skills` to generate content derived from master files.

**Premise:** 1835, a rural Russian estate. An alien spacecraft makes an emergency landing; the aliens hide in local animals while the gentry investigates what they believe to be supernatural events. Players on both sides manage their goals without initially understanding each other.

## File structure

| File | Purpose |
|------|---------|
| `Персонажи.md` | GM reference: Full character descriptions: source for the three output types — public role list (PUB_INFO blocks), personal player cards (untagged text), GM-only notes (GM_INFO blocks). Tag system: `PUB_INFO`/`PUB_END`, `GM_INFO`/`GM_END`, untagged = personal player card |
| `Игроки.md` | GM reference: player applications |
| `АХЧ.md` | GM reference: material things to prepare |
| `Пришельцы.md` | GM reference: full aliens specification |
| `Механики.md` | GM reference: strictly-defined game rules — each mechanic has explicit trigger conditions and outcomes. What the GM executes as a rule, not as a judgment call |
| `Корреспонденция.md` | GM reference: all incoming and outgoing letters — player Поручения, GM event letters, interception potential and outcomes |
| `Записки.md` | GM tool: optional "morning notes" for players — inner monologue fragments offered at the start of each raout to players who need direction. 2–3 notes per character, psychology-focused, not event-specific. |
| `инструкции_по_генерации.md` | Rules for the automatic creation of public documents from GM references |
| `public/intro.md` | Player-facing premise text |
| `материалы/графика/персонажи/портреты.md` | Character portraits (internet links to images of paintures, with attributions) |
| `public/Атмосфера.md` | Atmosphere, historical background, costuming notes and references for players (see also `public/exposition/` and `материалы/*.md`) |
| `public/Открытые_механики.md` | Player-facing general mechanics reference: rauts schedule, commissions, free actions, letters, abilities, morning notes, safety conventions (physical/emotional interactions), police and weapons, etc. Written manually. |
| `public/Роли.md` | Public character list players use to choose roles - updated automatically according to инструкции_по_генерации.md |
| `public/Контакт.md` | Rules for the alien animal possession mechanic - updated automatically according to инструкции_по_генерации.md |
| `public/Общение_с_пришельцами.md` | Rules for the alien human contact mechanic - updated automatically according to инструкции_по_генерации.md |
| `public/letters/` | Print-ready letter files — one per letter from Корреспонденция.md. Player templates have fill-in blanks; GM incoming letters are distributed at the right moment. Each file has a GM note at top (italic, marked) and the period-style letter text below. Ефросинья's `Видение_*` files are a special case: short (3–5 sentences) first-person manic-episode outbursts giving strong emotion plus plot-trigger facts, not scenes to memorize — see existing files for tone. |
| `public/Медицина.md` | Player-facing mechanic card for the medicine mechanic |
| `public/characters/` | Player card files — one per character, generated from untagged text in Персонажи.md |
| `public/игротехам/` | Reference materials for game technicians and location GMs |
| `public/графика/` | Published images (banners, posters, and other visual assets) |
| `public/ассигнации/` | In-game banknotes for printing |
| `Динамика.md` | GM reference: authorial analysis of how the game may unfold — plot branches, pacing, resource balance, conflict geometry, GM nudge tools. What the GM interprets and adjusts, not executes by rule |
| `Мастерский_лист.md` | GM tool: game-flow control sheet for the main-location GM |
| `Построение_атмосферы.md` | GM reference: series plan for pre-game atmosphere publications — topics, principles, character connections, movie references, and discussion notes for the `public/exposition/` cycle |

Directories:
- `public/` — all public documents for players
- `public/exposition/` — pre-play publications for atmosphere building
- `материалы/` — research, visual assets and sound files (look at it for historical references!)
- `черновики/` — draft documents
- `tg-bot/` — Telegram bot for players. Files here (notably `game-knowledge.js`) are NOT an authoritative source of game information — the master files above are. But they must be kept in sync: when game materials change, update `tg-bot/game-knowledge.js` accordingly.
Ready-to-publication texts from `материалы/` goes to `public/exposition/`.


## Language rules

- All materials are written in **modern Russian** spelling.
- For `public/exposition/` files, prefer flowing, connected prose over short fragmented sentences — clipped one/two-sentence paragraphs read as artificial ("AI-generated"). Write in smooth periods with natural transitions between thoughts, except where a character's voice specifically calls for a punchier register (e.g. Ефросинья's `Видение_*` letters, see above).

Some texts may use pre-1918 archaic Russian orthography (е → ѣ, etc.) for deliberate period atmosphere. Do not "correct" these spellings — they are intentional, preserve the archaic orthography throughout.


## Character sheet format (Персонажи.md)

Each character entry follows this structure:
- `## Имя` heading, followed by two subtitle lines (role/relation, then age) with no labels
- `PUB_INFO`/`PUB_END` block – short public teaser: 2–3 sentences of description plus a sentence on what the character faces during the game; ends with crosspol/gender-invert notes when applicable
- (optional) `GM_INFO`/`GM_END` block right after PUB_END – casting notes, references, why the role matters (not shown to players)
- Free-form biography: goals, motivations, relationships, moral dilemmas; may contain `GENDER_RULE(condition)`/`GENDER_END` blocks for text conditional on another character's gender in that run
- (optional) **Деньги:** X – monetary resources available
- (optional) **Раздатка:** – printed materials for the player; list items, may include mechanical-action application forms or `CARD_BEGIN(имя, путь/)`/`CARD_END` blocks (wrapped in `GM_INFO`/`GM_END` since the card is generated separately, not shown inline)
- (optional) `GM_INFO`/`GM_END` block with **Материалы в процессе игры:** – GM-only notes on which follow-up materials to hand out and when
- **Костюм (в идеале):** – costuming guidance (plural **Костюмы:** for characters covering multiple people, e.g. location masters)
- **Питомец (для примера):** – example animal for the alien-possession mechanic; illustrative, not mandatory
- (optional) **Реквизит:** – special props needed for the role (e.g. conjurer's tricks)

When adding or editing a character, keep all these fields. `Персонажи.md` is full characters info for GM and is a source for auto-generated public `Список ролей.md` and personal character sheet for each player.

## Gender system

Three distinct mechanisms exist — keep them separate in analysis:

**1. Кросспол ("Кросспол уместен" / "Кросспол ожидается")**
The player's real-world gender does not need to match the character's gender. The character stays exactly as written in the fiction. When analysing in-fiction events (who can be recruited, who is suspected, who falls in love with whom), use the **character's** gender, not the player's.
- "Кросспол уместен": Горихвостов, Свербеев, Доложейко, Пирогов, Фишнер, Строганов-ст., Строганов-мл., Валемонте, Раскольниченко, Краузе
- "Кросспол ожидается": Чарторыжский — canonically a woman passing as a man; crossplay is the design intent, not optional.

**2. Гендер персонажа можно инвертировать**
The **character's** written gender can be changed to match the player's preference on request. When this happens, pronouns, relationships, and `GENDER_RULE` blocks change accordingly.
Currently invertible: Горихвостов, Строганов-ст., Строганов-мл., Валемонте, Раскольниченко, Ласневская, Краузе.

**3. GENDER_RULE blocks**
`GENDER_RULE(condition)` / `GENDER_END` blocks in `Персонажи.md` contain conditional text that activates only for a specific gender combination of characters. condition could contain one character name (mind gender variations of feminine/masculine Russian names) with gender marker (e.g. `Строганова-младшая - Ж`), or logical cobination with `and` or `or` (e.g. `Строганов-младший - М and Раскольниченко - Ж`). Flag these when relevant to plot or romance analysis.


## Alien contact mechanic (core design)

Defined in `Пришельцы.md`. Key constraints to respect when writing related content:
- Aliens inhabit local animals; **ribbons (ленточки) are out-of-game technical markers** for players/GMs only – characters in the fiction do not see or perceive them, they only notice the animals' strange behaviour
- Aliens can briefly take control of a human's mind (with ethical limits built into their nature)
- The controlled human has partial or full memory loss afterward
- Aliens need fuel: 5 barrels of a single liquid – oil or spirit, never mixed (the two paths do not add up) – or a safe high-altitude launch point
- This mechanic creates unreliable narration and dual-role play for "possessed" characters


## Historical period

Russia, 1835. Relevant details the writing draws on: Russian Empire Table of Ranks, provincial landowner society, Church hierarchy (благочинный = rural church supervisor), moonshining under state monopoly, serfdom, aftermath of the Polish uprising (1830–31) and the Decembrist movement. When expanding historical flavor, keep this period and context.

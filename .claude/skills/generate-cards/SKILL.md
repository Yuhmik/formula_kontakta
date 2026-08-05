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

**Gender-inversion word forms – SurnameRegex vs PrimaryRegex:** in the PowerShell script's `$charConfig`, `PrimaryRegex` fires only on the character's own card (matched via `CardKey` against the card name); `SurnameRegex` fires on every card. This isn't a difference in what kind of gender rule applies – it's blast radius. `PrimaryRegex` holds generic pronouns (`\bон\b`, `\bего\b`, …) that occur constantly and usually refer to someone else entirely; applied globally they'd corrupt unrelated pronouns in other characters' cards. `SurnameRegex` holds specific tokens (surnames, or a distinctive word form like `занемогла` → `занемог`) unlikely to collide with unrelated text, so it's safe everywhere. When a gender-dependent word form can appear in *other* characters' cards (e.g. Ласневская's illness described in Пирогов's medical journal), put it in `SurnameRegex`, not `PrimaryRegex`, and fix it once at the pipeline level rather than hand-wrapping every occurrence in `GENDER_RULE(...)...GENDER_END` in the source `.md`.

## Invocation

- `/generate-cards` — regenerate all cards
- `/generate-cards <CardName>` — regenerate only the named card (e.g. `/generate-cards Контакт`)

## Steps

1. Extract the optional card name filter from the user's invocation (empty string if not given).

2. Run this PowerShell script from the project root directory:

```powershell
$filterName = ""  # set to card name if user specified one, otherwise leave empty

$root = (Get-Location).Path

$validStyles = @('document', 'handwritten', 'reference')

# ── Gender-inversion config ──────────────────────────────────────────────────
# Full list of characters whose gender can be inverted between runs.
# DefaultGender      = gender used in source files (Персонажи.md, Пришельцы.md, etc.)
# IgrokiKey          = key column value in Игроки.md (matches the row for gender lookup)
# CardKey            = substring matched against card Name to identify character's own card
# NominativeDefault  = nominative surname in DefaultGender, as written in GENDER_RULE(...) conditions
# NominativeInverted = nominative surname in the opposite gender, as written in GENDER_RULE(...) conditions
# SurnameRegex  = [pattern, replacement] pairs applied to ALL cards (surname declension).
#                 List compound forms (longest) before simple \b forms to prevent cascade.
# PrimaryRegex  = [pattern, replacement] pairs applied ONLY to the character's own card
#                 (pronoun/verb substitution; too generic to apply globally).
# Update this table when character genders change or new invertible characters are added.
$charConfig = @(
    # ── Горихвостов-Чаадаевский (default М → can become Ж) ──────────────────
    [PSCustomObject]@{
        IgrokiKey          = 'Горихвостова-Чаадаевская'
        DefaultGender      = 'М'
        CardKey            = 'Горихвостов'
        NominativeDefault  = 'Горихвостов'
        NominativeInverted = 'Горихвостова'
        # Noun-type surname: nominative М=Горихвостов → Ж=Горихвостова;
        # all oblique М forms → Горихвостовой.
        # Nominative goes last to avoid matching prefix of longer forms.
        SurnameRegex  = @(
            ,@('Горихвостовым',  'Горихвостовой')
            ,@('Горихвостове',   'Горихвостовой')
            ,@('Горихвостову',   'Горихвостовой')
            ,@('Горихвостова',   'Горихвостовой')
            ,@('Горихвостов\b',  'Горихвостова')
        )
        PrimaryRegex  = @(
            ,@('\bон\b',  'она')
            ,@('\bОн\b',  'Она')
            ,@('\bего\b', 'её')
            ,@('\bЕго\b', 'Её')
            ,@('\bему\b', 'ей')
            ,@('\bЕму\b', 'Ей')
            ,@('\bим\b',  'ей')
            ,@('\bИм\b',  'Ей')
        )
    }
    # ── Строганов-старший (default М → can become Ж) ─────────────────────────
    [PSCustomObject]@{
        IgrokiKey          = 'Строганов-ст'
        DefaultGender      = 'М'
        CardKey            = 'Строганов_ст'
        NominativeDefault  = 'Строганов-старший'
        NominativeInverted = 'Строганова-старшая'
        # Compound-form (with suffix) first, then standalone \b forms.
        SurnameRegex  = @(
            ,@('Строгановым-старшим',  'Строгановой-старшей')
            ,@('Строганове-старшем',   'Строгановой-старшей')
            ,@('Строганову-старшему',  'Строгановой-старшей')
            ,@('Строганова-старшего',  'Строгановой-старшей')
            ,@('Строганов-старший',    'Строганова-старшая')
        )
        PrimaryRegex  = @(
            ,@('\bон\b',  'она')
            ,@('\bОн\b',  'Она')
            ,@('\bего\b', 'её')
            ,@('\bЕго\b', 'Её')
            ,@('\bему\b', 'ей')
            ,@('\bЕму\b', 'Ей')
            ,@('\bим\b',  'ей')
            ,@('\bИм\b',  'Ей')
        )
    }
    # ── Строганов-младший (default М → can become Ж) ─────────────────────────
    [PSCustomObject]@{
        IgrokiKey          = 'Строганов-мл'
        DefaultGender      = 'М'
        CardKey            = 'Строганов_мл'
        NominativeDefault  = 'Строганов-младший'
        NominativeInverted = 'Строганова-младшая'
        SurnameRegex  = @(
            ,@('Строгановым-младшим',  'Строгановой-младшей')
            ,@('Строганове-младшем',   'Строгановой-младшей')
            ,@('Строганову-младшему',  'Строгановой-младшей')
            ,@('Строганова-младшего',  'Строгановой-младшей')
            ,@('Строганов-младший',    'Строганова-младшая')
        )
        PrimaryRegex  = @(
            ,@('\bон\b',  'она')
            ,@('\bОн\b',  'Она')
            ,@('\bего\b', 'её')
            ,@('\bЕго\b', 'Её')
            ,@('\bему\b', 'ей')
            ,@('\bЕму\b', 'Ей')
            ,@('\bим\b',  'ей')
            ,@('\bИм\b',  'Ей')
        )
    }
    # ── Раскольниченко (default М → can become Ж) ────────────────────────────
    # Surname ending -енко is indeclinable — no SurnameRegex needed.
    [PSCustomObject]@{
        IgrokiKey          = 'Раскольниченко'
        DefaultGender      = 'М'
        CardKey            = 'Раскольниченко'
        NominativeDefault  = 'Раскольниченко'
        NominativeInverted = 'Раскольниченко'
        SurnameRegex  = @()
        PrimaryRegex  = @(
            ,@('\bон\b',  'она')
            ,@('\bОн\b',  'Она')
            ,@('\bего\b', 'её')
            ,@('\bЕго\b', 'Её')
            ,@('\bему\b', 'ей')
            ,@('\bЕму\b', 'Ей')
            ,@('\bим\b',  'ей')
            ,@('\bИм\b',  'Ей')
        )
    }
    # ── Валемонте (default М → can become Ж) ─────────────────────────────────
    # Foreign surname ending in vowel is indeclinable — no SurnameRegex needed.
    [PSCustomObject]@{
        IgrokiKey          = 'Валемонте'
        DefaultGender      = 'М'
        CardKey            = 'Валемонте'
        NominativeDefault  = 'Валемонте'
        NominativeInverted = 'Валемонте'
        SurnameRegex  = @()
        PrimaryRegex  = @(
            ,@('\bграф\b',  'графиня')
            ,@('\bГраф\b',  'Графиня')
            ,@('\bон\b',  'она')
            ,@('\bОн\b',  'Она')
            ,@('\bего\b', 'её')
            ,@('\bЕго\b', 'Её')
            ,@('\bему\b', 'ей')
            ,@('\bЕму\b', 'Ей')
            ,@('\bим\b',  'ей')
            ,@('\bИм\b',  'Ей')
        )
    }
    # ── Ласневская (default Ж → can become М) ────────────────────────────────
    [PSCustomObject]@{
        IgrokiKey          = 'Ласневский'
        DefaultGender      = 'Ж'
        CardKey            = 'Ласневск'
        NominativeDefault  = 'Ласневская'
        NominativeInverted = 'Ласневский'
        # Adjective-type surname: nom.Ж Ласневская → nom.М Ласневский;
        # oblique Ж forms (Ласневской, Ласневскую) → М genitive Ласневского.
        SurnameRegex  = @(
            ,@('Ласневскую', 'Ласневского')
            ,@('Ласневской', 'Ласневского')
            ,@('Ласневская', 'Ласневский')
            ,@('занемогла',  'занемог')
        )
        PrimaryRegex  = @(
            ,@('Была ',      'Был ')
            ,@('была ',      'был ')
            ,@(' ранена',    ' ранен')
            ,@('пострадала', 'пострадал')
            ,@('оказалась',  'оказался')
            ,@('тихая',      'тихий')
            ,@('блаженная',  'блаженный')
            ,@('\bона\b',    'он')
            ,@('\bОна\b',    'Он')
            ,@('\bеё\b',     'его')
            ,@('\bЕё\b',     'Его')
            ,@('\bей\b',     'ему')
            ,@('\bЕй\b',     'Ему')
        )
    }
)

# Determine a character's current gender this run by looking up their row in Игроки.md
# (falls back to DefaultGender if the row or the пол field is missing/empty).
function Get-CurrentGender($cfg, $igrokiText) {
    $escaped  = [regex]::Escape($cfg.IgrokiKey)
    $rowMatch = [regex]::Match($igrokiText, "^\|\s*$escaped\s*\|\s*([МЖ]?)\s*\|", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($rowMatch.Success -and $rowMatch.Groups[1].Value) { return $rowMatch.Groups[1].Value }
    return $cfg.DefaultGender
}

# Evaluate a GENDER_RULE condition, e.g. "Ласневская - Ж" or "A - М and B - Ж" (supports and/or,
# matching the syntax already used in Персонажи.md). Name is matched against NominativeDefault/
# NominativeInverted so either gendered spelling resolves to the same character.
function Test-GenderCondition([string]$condition, $charConfig, $igrokiText) {
    foreach ($orGroup in ($condition -split '\s+or\s+')) {
        $allTrue = $true
        foreach ($clause in ($orGroup -split '\s+and\s+')) {
            $clauseMatch = [regex]::Match($clause.Trim(), '^(.+?)\s*-\s*([МЖ])$')
            if (-not $clauseMatch.Success) { $allTrue = $false; break }
            $nameHint   = $clauseMatch.Groups[1].Value.Trim()
            $wantGender = $clauseMatch.Groups[2].Value
            $cfgMatch = $charConfig | Where-Object { $_.NominativeDefault -eq $nameHint -or $_.NominativeInverted -eq $nameHint } | Select-Object -First 1
            if (-not $cfgMatch) { $allTrue = $false; break }
            if ((Get-CurrentGender $cfgMatch $igrokiText) -ne $wantGender) { $allTrue = $false; break }
        }
        if ($allTrue) { return $true }
    }
    return $false
}

# Resolve GENDER_RULE(...)...GENDER_END blocks in a card body: the matching branch's text is
# kept but swapped for an opaque placeholder, so the blind surname-substitution pass below can
# never touch it (a correctly hand-written inverted form can otherwise collide with an unrelated
# source pattern for a different grammatical case - e.g. feminine accusative "Горихвостову" is
# the same string as the masculine dative source pattern). Placeholders are restored afterward.
function Resolve-GenderRules([string]$text, $charConfig, $igrokiText) {
    $pattern = '(?s)GENDER_RULE\(([^)]+)\)(.*?)GENDER_END'
    $placeholders = New-Object System.Collections.Generic.List[string]
    $sb = New-Object System.Text.StringBuilder
    $lastPos = 0
    foreach ($m in [regex]::Matches($text, $pattern)) {
        [void]$sb.Append($text.Substring($lastPos, $m.Index - $lastPos))
        if (Test-GenderCondition $m.Groups[1].Value $charConfig $igrokiText) {
            $idx = $placeholders.Count
            [void]$placeholders.Add($m.Groups[2].Value)
            [void]$sb.Append("@@GR${idx}@@")
        }
        $lastPos = $m.Index + $m.Length
    }
    [void]$sb.Append($text.Substring($lastPos))
    return [PSCustomObject]@{ Text = $sb.ToString(); Placeholders = $placeholders }
}

# ── Minimal markdown → HTML conversion for card bodies ───────────────────────
# Supports exactly the constructs used in source cards: standalone **bold** lines as
# headings (first one → h1, rest → h2), "- " bullet lists, "1. " numbered lists, "| a | b |"
# tables (row 0 = header, row 1 = separator, discarded), fenced ``` code blocks (```mermaid
# is flagged so the wrapper can load the mermaid renderer), "---" as <hr>, inline **bold**
# and *italic*, everything else as its own <p>. Deliberately not a general markdown engine.

function ConvertTo-HtmlEscaped([string]$s) {
    $s = $s -replace '&', '&amp;'
    $s = $s -replace '<', '&lt;'
    $s = $s -replace '>', '&gt;'
    return $s
}

function Convert-InlineMarkdown([string]$s) {
    $s = ConvertTo-HtmlEscaped $s
    $s = [regex]::Replace($s, '\*\*(.+?)\*\*', '<strong>$1</strong>')
    $s = [regex]::Replace($s, '(?<!\*)\*([^*]+?)\*(?!\*)', '<em>$1</em>')
    return $s
}

function ConvertTo-HtmlTable($rows) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('<table>')
    $headerCells = ($rows[0].Trim().Trim('|') -split '\|') | ForEach-Object { $_.Trim() }
    [void]$sb.Append('<thead><tr>')
    foreach ($c in $headerCells) { [void]$sb.Append("<th>$(Convert-InlineMarkdown $c)</th>") }
    [void]$sb.Append('</tr></thead><tbody>')
    for ($r = 2; $r -lt $rows.Count; $r++) {
        $cells = ($rows[$r].Trim().Trim('|') -split '\|') | ForEach-Object { $_.Trim() }
        [void]$sb.Append('<tr>')
        foreach ($c in $cells) { [void]$sb.Append("<td>$(Convert-InlineMarkdown $c)</td>") }
        [void]$sb.Append('</tr>')
    }
    [void]$sb.Append('</tbody></table>')
    return $sb.ToString()
}

function ConvertTo-CardHtmlBody([string]$body) {
    $lines = $body -split "`r?`n"
    $html = New-Object System.Text.StringBuilder
    $headingUsed = $false
    $usesMermaid = $false
    $i = 0
    while ($i -lt $lines.Count) {
        $trimmed = $lines[$i].Trim()

        if ($trimmed -eq '') { $i++; continue }

        # GM-only note written as an HTML comment (e.g. `<!-- *GM: ... -->`) - passed through
        # verbatim as a real HTML comment, so it stays invisible in the browser (as it already
        # was in the raw markdown) instead of being escaped into visible "<!-- ... -->" text.
        if ($trimmed -match '^<!--') {
            $commentLines = New-Object System.Collections.Generic.List[string]
            $commentLines.Add($lines[$i])
            while ($i -lt $lines.Count -and $lines[$i] -notmatch '-->') {
                $i++
                $commentLines.Add($lines[$i])
            }
            $i++
            [void]$html.AppendLine(($commentLines -join "`n"))
            continue
        }

        # Raw single-line HTML tag (<img>, <div>...</div>, <hr>, ...) - passed through verbatim
        # (unescaped), so authors can hand-write style="float:left/right; width:...; margin:..."
        # for in-text image placement, or a forced page break like
        # <div style="break-after: page; page-break-after: always;"></div>, that plain markdown
        # can't express.
        if ($trimmed -match '^<[a-zA-Z]') {
            [void]$html.AppendLine($lines[$i])
            $i++
            continue
        }

        if ($trimmed -match '^```(\w*)$') {
            $lang = $Matches[1]
            $i++
            $codeLines = New-Object System.Collections.Generic.List[string]
            while ($i -lt $lines.Count -and $lines[$i].Trim() -ne '```') {
                $codeLines.Add($lines[$i])
                $i++
            }
            $i++
            $code = ConvertTo-HtmlEscaped ($codeLines -join "`n")
            if ($lang -eq 'mermaid') {
                $usesMermaid = $true
                [void]$html.AppendLine("<pre class=`"mermaid`">$code</pre>")
            } else {
                [void]$html.AppendLine("<pre><code>$code</code></pre>")
            }
            continue
        }

        if ($trimmed -match '^\|.*\|$') {
            $tableRows = New-Object System.Collections.Generic.List[string]
            while ($i -lt $lines.Count -and $lines[$i].Trim() -match '^\|.*\|$') {
                $tableRows.Add($lines[$i])
                $i++
            }
            [void]$html.AppendLine((ConvertTo-HtmlTable $tableRows))
            continue
        }

        if ($trimmed -match '^[-*]\s+\S') {
            [void]$html.Append('<ul>')
            while ($i -lt $lines.Count -and $lines[$i].Trim() -match '^[-*]\s+(.*)$') {
                [void]$html.Append("<li>$(Convert-InlineMarkdown $Matches[1])</li>")
                $i++
            }
            [void]$html.AppendLine('</ul>')
            continue
        }

        if ($trimmed -match '^\d+\.\s+\S') {
            [void]$html.Append('<ol>')
            while ($i -lt $lines.Count -and $lines[$i].Trim() -match '^\d+\.\s+(.*)$') {
                [void]$html.Append("<li>$(Convert-InlineMarkdown $Matches[1])</li>")
                $i++
            }
            [void]$html.AppendLine('</ol>')
            continue
        }

        if ($trimmed -match '^-{3,}$') {
            [void]$html.AppendLine('<hr>')
            $i++
            continue
        }

        if ($trimmed -match '^\*\*([^*]+)\*\*$') {
            $tag = if (-not $headingUsed) { 'h1' } else { 'h2' }
            $headingUsed = $true
            [void]$html.AppendLine("<$tag>$(Convert-InlineMarkdown $Matches[1])</$tag>")
            $i++
            continue
        }

        [void]$html.AppendLine("<p>$(Convert-InlineMarkdown $trimmed)</p>")
        $i++
    }
    return [PSCustomObject]@{ Html = $html.ToString().TrimEnd(); UsesMermaid = $usesMermaid }
}

# ── Per-style HTML wrapper (self-contained <style> block, no shared stylesheet: cards land
#    in different directories - public/, public/letters/, public/игротехам/ - so each file
#    carries its own CSS rather than depending on a relative path to letter.css). ────────────

$documentCss = @'
* { margin: 0; padding: 0; box-sizing: border-box; }
@page { size: A4; margin: 10mm; }
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
ul { list-style-type: "\2013\0020"; }
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
@media screen { body { padding: 10mm 0; background: #d8cdb4; } .page { width: 210mm; min-height: 297mm; padding: 16mm 18mm; box-shadow: 0 2mm 8mm rgba(0, 0, 0, 0.3); } }
'@

$handwrittenCss = @'
* { margin: 0; padding: 0; box-sizing: border-box; }
@page { size: A4; margin: 10mm; }
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
@media screen { body { padding: 10mm 0; background: #d8cdb4; } .page { width: 210mm; min-height: 297mm; padding: 18mm 20mm; box-shadow: 0 2mm 8mm rgba(0, 0, 0, 0.3); } }
'@

$referenceCss = @'
* { margin: 0; padding: 0; box-sizing: border-box; }
@page { size: A4; margin: 15mm; }
html, body { background: #fff; }
body {
  font-family: Georgia, "Times New Roman", serif;
  color: #1a1a1a;
  font-size: 11pt;
  line-height: 1.4;
}
.sheet { max-width: 190mm; margin: 0 auto; padding: 10mm 6mm; }
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
@media screen { body { padding: 10mm; } }
'@

# When `copies` > 1, the single instance is repeated in a `columns`-wide grid on the page so
# the sheet can be printed once and cut into several identical copies. Neighboring copies share
# a single dashed cut line (border-right/border-bottom on every cell, with gap: 0 so the lines
# touch) instead of each cell drawing its own independent box - this is what makes interior cut
# lines cross into a "+" wherever a row division meets a column division, rather than reading as
# a frame around each copy. The last column/row strips its own trailing border via nth-child so
# the grid isn't closed off on the outer edges (the paper edge already marks that boundary).
# Cell padding is 10mm and (for document/handwritten) @page margin is also 10mm, so in print the
# text sits exactly 1cm from every cut line and 1cm from the paper edge - the same margin on every
# side. The outer .page.copies padding is screen-only: on screen @page margin doesn't apply, so the
# screen mockup needs its own 1cm inset to match; in print that inset would double up with @page's
# margin, so it's omitted there and @page alone provides the paper-edge margin. Cut color matches
# each style's existing dashed-line tone.
function Add-CopiesGridCss([string]$css, [string]$topClass, [string]$cutColor, [int]$columns) {
    return $css + @"

@media screen { .$topClass.copies { padding: 10mm; } }
.copies-grid { display: grid; grid-template-columns: repeat($columns, 1fr); gap: 0; }
.copy-cell { padding: 10mm; border-right: 1pt dashed $cutColor; border-bottom: 1pt dashed $cutColor; break-inside: avoid; page-break-inside: avoid; }
.copy-cell:nth-child(${columns}n) { border-right: none; }
.copy-cell:nth-last-child(-n+$columns) { border-bottom: none; }
"@
}

function Get-CardWrapper([string]$style, [bool]$usesMermaid, [int]$copies, [int]$columns) {
    $wrap = $null
    switch ($style) {
        'document' {
            $wrap = [PSCustomObject]@{
                FontLinks = "  <link rel=`"preconnect`" href=`"https://fonts.googleapis.com`">`n  <link rel=`"preconnect`" href=`"https://fonts.gstatic.com`" crossorigin>`n  <link href=`"https://fonts.googleapis.com/css2?family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&display=swap`" rel=`"stylesheet`">"
                Css       = $documentCss
                ExtraHead = ''
                Open      = '<div class="page">'
                Close     = '</div>'
                TopClass  = 'page'
                CutColor  = '#8a7a5f'
            }
        }
        'handwritten' {
            $wrap = [PSCustomObject]@{
                FontLinks = "  <link rel=`"preconnect`" href=`"https://fonts.googleapis.com`">`n  <link rel=`"preconnect`" href=`"https://fonts.gstatic.com`" crossorigin>`n  <link href=`"https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap`" rel=`"stylesheet`">"
                Css       = $handwrittenCss
                ExtraHead = ''
                Open      = '<div class="page">'
                Close     = '</div>'
                TopClass  = 'page'
                CutColor  = '#8a7a5f'
            }
        }
        'reference' {
            $mermaidScript = ''
            if ($usesMermaid) {
                $mermaidScript = "  <script src=`"https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js`"></script>`n  <script>mermaid.initialize({ startOnLoad: true });</script>"
            }
            $wrap = [PSCustomObject]@{
                FontLinks = ''
                Css       = $referenceCss
                ExtraHead = $mermaidScript
                Open      = '<div class="sheet">'
                Close     = '</div>'
                TopClass  = 'sheet'
                CutColor  = '#999'
            }
        }
    }

    if ($copies -gt 1) {
        $wrap.Css  = Add-CopiesGridCss $wrap.Css $wrap.TopClass $wrap.CutColor $columns
        $wrap.Open = $wrap.Open -replace '(class=")(\w+)"', "`$1`$2 copies`""
    }
    return $wrap
}

# Determine which characters are currently inverted by reading Игроки.md
$igrokiText = Get-Content (Join-Path $root 'Игроки.md') -Raw -Encoding UTF8
$activeInversions = [System.Collections.Generic.List[PSCustomObject]]::new()
foreach ($cfg in $charConfig) {
    if ((Get-CurrentGender $cfg $igrokiText) -ne $cfg.DefaultGender) {
        $activeInversions.Add($cfg)
    }
}

$generated = [System.Collections.Generic.List[string]]::new()
$skipped   = [System.Collections.Generic.List[string]]::new()

$sourceFiles = Get-ChildItem -Path $root -Filter "*.md" -Recurse |
    Where-Object {
        $rel = $_.FullName.Substring($root.Length)
        $rel -notmatch "\\public\\" -and
        $rel -notmatch "\\черновики\\" -and
        $rel -notmatch "\\.claude\\"
    }

$tagPattern          = '(?m)^CARD_BEGIN\(([^,]+),\s*([^,]+),\s*([^,\)]+)(?:,\s*(\d+))?(?:,\s*(\d+))?\)([\s\S]*?)^CARD_END'
$noStylePattern       = '(?m)^CARD_BEGIN\(([^,]+),\s*([^,\)]+)\)'
$legacyPattern        = '(?m)^CARD_BEGIN\(([^,\)]+)\)'

foreach ($file in $sourceFiles) {
    $text = Get-Content $file.FullName -Raw -Encoding UTF8
    if (-not $text) { continue }

    foreach ($m in [regex]::Matches($text, $tagPattern)) {
        $name    = $m.Groups[1].Value.Trim()
        $dir     = $m.Groups[2].Value.Trim().TrimEnd('/').TrimEnd('\')
        $style   = $m.Groups[3].Value.Trim()
        $copies  = if ($m.Groups[4].Success) { [int]$m.Groups[4].Value } else { 1 }
        $columns = if ($m.Groups[5].Success) { [int]$m.Groups[5].Value } else { 2 }
        $body    = $m.Groups[6].Value -replace '^[\r\n]+', '' -replace '[\r\n]+$', ''

        if ($filterName -and $name -ne $filterName) { continue }

        if ($validStyles -notcontains $style) {
            $skipped.Add("$($file.Name): CARD_BEGIN($name) – неизвестный стиль `"$style`" (нужен document/handwritten/reference), пропущено")
            continue
        }

        $origName = $name

        # Resolve GENDER_RULE/GENDER_END branches first; the winning text is protected
        # from the blind surname substitution below via opaque placeholders.
        $gr = Resolve-GenderRules $body $charConfig $igrokiText
        $body = $gr.Text
        $placeholders = $gr.Placeholders

        # Apply gender substitutions for characters whose gender is inverted this run
        foreach ($cfg in $activeInversions) {
            # Surname declension – applied to body and filename
            foreach ($pair in $cfg.SurnameRegex) {
                $body = $body -replace $pair[0], $pair[1]
                $name = $name -replace $pair[0], $pair[1]
            }
            # Pronoun/verb forms – applied only to the character's own card
            if ($cfg.CardKey -and ($name -match [regex]::Escape($cfg.CardKey))) {
                foreach ($pair in $cfg.PrimaryRegex) {
                    $body = $body -replace $pair[0], $pair[1]
                }
            }
        }

        # Restore GENDER_RULE-resolved text, untouched by the substitution pass above
        for ($i = 0; $i -lt $placeholders.Count; $i++) {
            $body = $body.Replace("@@GR${i}@@", $placeholders[$i])
        }

        $conv = ConvertTo-CardHtmlBody $body
        $wrap = Get-CardWrapper $style $conv.UsesMermaid $copies $columns

        $innerHtml = $conv.Html
        if ($copies -gt 1) {
            $cells = 1..$copies | ForEach-Object { "<div class=`"copy-cell`">`n$($conv.Html)`n</div>" }
            $innerHtml = "<div class=`"copies-grid`">`n$($cells -join "`n")`n</div>"
        }

        $titleText = $name -replace '_', ' '
        # Origin marker – first line of every generated file (see инструкции_по_генерации.md)
        $originComment = '<!-- generated from `' + $file.Name + '` CARD "' + $origName + '" -->'

        $fullHtml = @"
$originComment
<!DOCTYPE html>
<html lang="ru">

<head>
  <meta charset="utf-8">
  <title>$titleText</title>
$($wrap.FontLinks)
  <style>
$($wrap.Css)
  </style>
$($wrap.ExtraHead)
</head>

<body>
  $($wrap.Open)
$innerHtml
  $($wrap.Close)
</body>

</html>
"@

        $outDir = Join-Path $root $dir
        if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

        $outFile = Join-Path $outDir "$name.html"
        $utf8noBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($outFile, $fullHtml, $utf8noBom)
        $generated.Add($outFile.Substring($root.Length + 1))

        # Remove stale files: old .md output from before the HTML switch, and the old-named
        # file if gender substitution changed the name this run.
        foreach ($staleName in @($origName, $name) | Select-Object -Unique) {
            foreach ($ext in @('.md', '.html')) {
                $stale = Join-Path $outDir "$staleName$ext"
                if ($stale -ne $outFile -and (Test-Path $stale)) { [System.IO.File]::Delete($stale) }
            }
        }
    }

    foreach ($m in [regex]::Matches($text, $noStylePattern)) {
        $skipped.Add("$($file.Name): CARD_BEGIN($($m.Groups[1].Value.Trim())) – нет стиля (третьим аргументом нужен document/handwritten/reference), пропущено")
    }

    foreach ($m in [regex]::Matches($text, $legacyPattern)) {
        $skipped.Add("$($file.Name): CARD_BEGIN($($m.Groups[1].Value.Trim())) – нет пути назначения и стиля, пропущено")
    }
}

if ($generated.Count) { "Сгенерированы:"; $generated | ForEach-Object { "  $_" } }
if ($skipped.Count)   { ""; "Пропущены:"; $skipped | ForEach-Object { "  $_" } }
if (-not $generated.Count -and -not $skipped.Count) { "Карточки не найдены." }
```

3. Report the generated file list to the user. If files already existed they were overwritten with the current source content — that is the expected behaviour.

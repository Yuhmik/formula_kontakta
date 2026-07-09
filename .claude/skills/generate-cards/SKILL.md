---
name: generate-cards
description: Regenerate card files from CARD_BEGIN/CARD_END blocks in source .md files. Use whenever the user types /generate-cards, mentions regenerating or updating cards, or has just edited a CARD_BEGIN block and needs the output file refreshed. Optionally accepts a card name to update only that one card.
---

Extract all `CARD_BEGIN(Name, path/) … CARD_END` blocks from source .md files and write each card to `path/Name.md`.

## Invocation

- `/generate-cards` — regenerate all cards
- `/generate-cards <CardName>` — regenerate only the named card (e.g. `/generate-cards Контакт`)

## Steps

1. Extract the optional card name filter from the user's invocation (empty string if not given).

2. Run this PowerShell script from the project root directory:

```powershell
$filterName = ""  # set to card name if user specified one, otherwise leave empty

$root = (Get-Location).Path

# ── Gender-inversion config ──────────────────────────────────────────────────
# Full list of characters whose gender can be inverted between runs.
# DefaultGender = gender used in source files (Персонажи.md, Пришельцы.md, etc.)
# IgrokiKey     = key column value in Игроки.md (matches the row for gender lookup)
# CardKey       = substring matched against card Name to identify character's own card
# SurnameRegex  = [pattern, replacement] pairs applied to ALL cards (surname declension).
#                 List compound forms (longest) before simple \b forms to prevent cascade.
# PrimaryRegex  = [pattern, replacement] pairs applied ONLY to the character's own card
#                 (pronoun/verb substitution; too generic to apply globally).
# Update this table when character genders change or new invertible characters are added.
$charConfig = @(
    # ── Горихвостов-Чаадаевский (default М → can become Ж) ──────────────────
    [PSCustomObject]@{
        IgrokiKey     = 'Горихвостова-Чаадаевская'
        DefaultGender = 'М'
        CardKey       = 'Горихвостов'
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
        IgrokiKey     = 'Строганов-ст'
        DefaultGender = 'М'
        CardKey       = 'Строганов_ст'
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
        IgrokiKey     = 'Строганов-мл'
        DefaultGender = 'М'
        CardKey       = 'Строганов_мл'
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
        IgrokiKey     = 'Раскольниченко'
        DefaultGender = 'М'
        CardKey       = 'Раскольниченко'
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
        IgrokiKey     = 'Валемонте'
        DefaultGender = 'М'
        CardKey       = 'Валемонте'
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
        IgrokiKey     = 'Ласневский'
        DefaultGender = 'Ж'
        CardKey       = 'Ласневск'
        # Adjective-type surname: nom.Ж Ласневская → nom.М Ласневский;
        # oblique Ж forms (Ласневской, Ласневскую) → М genitive Ласневского.
        SurnameRegex  = @(
            ,@('Ласневскую', 'Ласневского')
            ,@('Ласневской', 'Ласневского')
            ,@('Ласневская', 'Ласневский')
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

# Determine which characters are currently inverted by reading Игроки.md
$igrokiText = Get-Content (Join-Path $root 'Игроки.md') -Raw -Encoding UTF8
$activeInversions = [System.Collections.Generic.List[PSCustomObject]]::new()
foreach ($cfg in $charConfig) {
    $escaped  = [regex]::Escape($cfg.IgrokiKey)
    $rowMatch = [regex]::Match($igrokiText, "^\|\s*$escaped\s*\|\s*([МЖ]?)\s*\|", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    $currentGender = if ($rowMatch.Success) { $rowMatch.Groups[1].Value } else { '' }
    if ($currentGender -and $currentGender -ne $cfg.DefaultGender) {
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

$tagPattern    = '(?m)^CARD_BEGIN\((\w+),\s*([^)]+)\)([\s\S]*?)^CARD_END'
$legacyPattern = '(?m)^CARD_BEGIN\((\w+)\s*\)'

foreach ($file in $sourceFiles) {
    $text = Get-Content $file.FullName -Raw -Encoding UTF8
    if (-not $text) { continue }

    foreach ($m in [regex]::Matches($text, $tagPattern)) {
        $name = $m.Groups[1].Value.Trim()
        $dir  = $m.Groups[2].Value.Trim().TrimEnd('/').TrimEnd('\')
        $body = $m.Groups[3].Value -replace '^[\r\n]+','' -replace '[\r\n]+$',''

        # Convert first **bold** line to H1 heading
        $m2 = ([regex]'(?m)^\*\*(.+)\*\*').Match($body)
        if ($m2.Success) {
            $body = $body.Substring(0, $m2.Index) + '# ' + $m2.Groups[1].Value + $body.Substring($m2.Index + $m2.Length)
        }

        if ($filterName -and $name -ne $filterName) { continue }

        $origName = $name

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

        # Origin marker – first line of every generated file (see инструкции_по_генерации.md)
        $hdr = '<!-- generated from `' + $file.Name + '` CARD "' + $origName + '" -->'
        $nl  = if ($body -match "`r`n") { "`r`n" } else { "`n" }
        $body = $hdr + $nl + $nl + $body

        $outDir = Join-Path $root $dir
        if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

        $outFile = Join-Path $outDir "$name.md"
        $utf8noBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($outFile, $body, $utf8noBom)
        $generated.Add($outFile.Substring($root.Length + 1))

        # Remove stale file if the name changed due to gender substitution
        if ($name -ne $origName) {
            $oldFile = Join-Path $outDir "$origName.md"
            if (Test-Path $oldFile) { [System.IO.File]::Delete($oldFile) }
        }
    }

    foreach ($m in [regex]::Matches($text, $legacyPattern)) {
        $skipped.Add("$($file.Name): CARD_BEGIN($($m.Groups[1].Value)) – нет пути назначения, пропущено")
    }
}

if ($generated.Count) { "Сгенерированы:"; $generated | ForEach-Object { "  $_" } }
if ($skipped.Count)   { ""; "Пропущены:"; $skipped | ForEach-Object { "  $_" } }
if (-not $generated.Count -and -not $skipped.Count) { "Карточки не найдены." }
```

3. Report the generated file list to the user. If files already existed they were overwritten with the current source content — that is the expected behaviour.

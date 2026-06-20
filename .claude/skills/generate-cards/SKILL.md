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
        $body = ([regex]'(?m)^\*\*(.+)\*\*').Replace($body, '# $1', 1)

        if ($filterName -and $name -ne $filterName) { continue }

        $outDir = Join-Path $root $dir
        if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

        $outFile = Join-Path $outDir "$name.md"
        $utf8noBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($outFile, $body, $utf8noBom)
        $generated.Add($outFile.Substring($root.Length + 1))
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

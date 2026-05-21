# Bijoy/ANSI Bengali Font to Unicode Converter

Create a Unicode Bengali font from a legacy Bijoy/ANSI Bengali font.

This tool is useful when you have an old Bengali font that draws Bengali
letters from ANSI/Latin codepoints, and you want a new `.ttf` that works with
real Bengali Unicode text.

The script uses a Unicode Bengali font as a template for the Unicode cmap and
Bengali shaping tables, then copies the matching outlines from the ANSI font
into those Unicode glyph slots.

## Why I Made This

Unicode fonts are used everywhere every day. But certain Bengali fonts that are
widely used, like SutonnyMJ, are still encoded using the old ASCII character
map, also known as ANSI or Windows-1252. I could not find a tool that
automatically converts ANSI Bengali fonts to Unicode, and it became a pain in
the ass to write Bengali using the deprecated version. So I made a Python
script that automatically converts it.

## What This Does

- Reads a legacy Bijoy/ANSI source font, for example `LegacyBijoyFont.ttf`.
- Reads a Unicode Bengali template font, for example `UnicodeTemplateFont.ttf`.
- Uses a built-in Bijoy/ANSI mapping table for common letters, marks, digits,
  and conjuncts.
- Copies and scales glyph outlines from the ANSI font into the Unicode font.
- Keeps the template font's Unicode cmap, GSUB, and GPOS shaping tables.
- Writes a new Unicode `.ttf` and a CSV report showing what was copied,
  skipped, or needs review.


## Important Font License Note

This repository is intended to publish the converter code.

Do not upload anyfont files unless you have the legal right to redistribute them. Many fonts are
copyrighted even when they are easy to download online. I will not be responsible for the illegal use of this script. Idc actually lol.

## Requirements

- Python 3.10 or newer
- `fonttools`
- `bijoytounicode`

## Install From GitHub

Clone the repository:

```bash
git clone https://github.com/TasnimulHasan0/Bijoy-to-Unicode-Font-Builder
cd Bijoy-to-Unicode-Font-Builder
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows PowerShell, this also works:

```powershell
python -m pip install -r requirements.txt
```

If you do not want to install packages globally, install them into a local
`.deps` folder:

```powershell
python -m pip install --target .\.deps -r requirements.txt
```

The script automatically loads packages from `.deps` when run from the project
folder.

## Prepare Your Font Files

You need two font files:

1. A legacy Bijoy/ANSI Bengali font.
2. A Unicode Bengali template font.

Keep those font files somewhere on your computer, for example:

```text
/path/to/LegacyBijoyFont.ttf
/path/to/UnicodeTemplateFont.ttf
```

You do not need to put the font files inside this repository. If you do place
fonts in the repository folder for local testing, do not commit them unless you
have redistribution rights.

## Quick Start

Run the script from inside the cloned repository.

Windows PowerShell:

```powershell
python .\make_bijoy_unicode_font.py `
  --ansi-font "/path/to/LegacyBijoyFont.ttf" `
  --unicode-template "/path/to/UnicodeTemplateFont.ttf" `
  --output "./ConvertedUnicodeFont.ttf" `
  --report "./mapping-report.csv"
```

macOS or Linux:

```bash
python make_bijoy_unicode_font.py \
  --ansi-font "/path/to/LegacyBijoyFont.ttf" \
  --unicode-template "/path/to/UnicodeTemplateFont.ttf" \
  --output "./ConvertedUnicodeFont.ttf" \
  --report "./mapping-report.csv"
```

Use your real local font paths in place of `/path/to/LegacyBijoyFont.ttf` and
`/path/to/UnicodeTemplateFont.ttf`.

You do not need to edit the Python script. Put your paths in the command after
`--ansi-font`, `--unicode-template`, `--output`, and `--report`.

## Command Options

### `--ansi-font`

Path to the old legacy Bijoy/ANSI Bengali source font.

Example:

```text
--ansi-font "/path/to/LegacyBijoyFont.ttf"
```

### `--unicode-template`

Path to a Unicode Bengali font that already has a proper Unicode cmap and
Bengali shaping tables.

Example:

```text
--unicode-template "/path/to/UnicodeTemplateFont.ttf"
```

### `--output`

Path where the generated Unicode font should be written.

Example:

```text
--output "./ConvertedUnicodeFont.ttf"
```

### `--report`

Path where the mapping report CSV should be written.

Example:

```text
--report "./mapping-report.csv"
```

### `--mapping-csv`

Optional. Path to a custom mapping CSV for extra glyphs, alternate glyphs, or
font-specific corrections.

Example:

```text
--mapping-csv "./sample-mapping.csv"
```

## Output Files

The command creates:

- `ConvertedUnicodeFont.ttf`: the generated Unicode font
- `mapping-report.csv`: a report of copied, skipped, missing, or duplicate
  mappings

Open `mapping-report.csv` after every run and check rows where `status` is not
`copied`.

Common statuses:

- `copied`: the source glyph was copied into the target Unicode glyph
- `duplicate-skipped`: another ANSI code already filled that same Unicode glyph
- `missing-source`: the ANSI font does not contain that source codepoint
- `unresolved`: the script could not infer the target Unicode glyph
- `missing-target`: the Unicode template does not contain that target glyph

## Custom Mapping CSV

The built-in mapping covers common Bijoy/ANSI Bengali codes. Some fonts contain
custom alternates or uncommon conjuncts. Add them with a CSV file:

```csv
source,unicode,target_glyph
U+00B0,U+0995 U+09CD U+0995,bn_k_ka
Av,U+0986,bn_aa
```

Then run:

```powershell
python .\make_bijoy_unicode_font.py `
  --ansi-font "/path/to/LegacyBijoyFont.ttf" `
  --unicode-template "/path/to/UnicodeTemplateFont.ttf" `
  --output "./ConvertedUnicodeFont.ttf" `
  --report "./mapping-report.csv" `
  --mapping-csv "./sample-mapping.csv"
```

CSV columns:

- `source`: source ANSI/Bijoy character or codepoints
- `unicode`: Unicode Bengali character sequence or codepoints
- `target_glyph`: optional template glyph name, useful for alternates

Accepted codepoint formats:

- `U+00B0`
- `0x00B0`
- `U+0995 U+09CD U+0995`
- normal text such as `Av`

## Repository Files

Recommended files to keep in the GitHub repository:

- `README.md`
- `LICENSE`
- `requirements.txt`
- `make_bijoy_unicode_font.py`
- `sample-mapping.csv`
- `.gitignore`

Files that should usually stay local:

- `.deps/`
- `__pycache__/`
- source font files
- Unicode template font files
- generated font files
- generated reports

## Publishing Your Own Copy on GitHub

If you want to publish your own repository:

```bash
git init
git add .gitignore LICENSE README.md requirements.txt make_bijoy_unicode_font.py sample-mapping.csv
git commit -m "Add Bijoy ANSI Bengali font converter"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
git push -u origin main
```

Replace `YOUR-USERNAME` and `YOUR-REPO-NAME` with your actual GitHub username
and repository name.

## Troubleshooting

### Missing dependency

Install dependencies again:

```bash
python -m pip install -r requirements.txt
```

Or install into `.deps`:

```powershell
python -m pip install --target .\.deps -r requirements.txt
```

### Generated font has missing conjuncts

Check `mapping-report.csv`. If a row is `unresolved`, add a custom row in your
mapping CSV with a `target_glyph`.

### Output font shapes incorrectly

The generated font reuses shaping tables from the Unicode template. If the
template does not contain a needed Bengali ligature, mark position, or
alternate glyph, the output may need manual review in a font editor.

### People cannot see the converted font style

If text is Unicode, people can still read it using another Bengali fallback
font. To see the exact converted font style, the font must be installed,
embedded in a document, or loaded as a webfont with permission from the font
license.

## Limitations

This is an automated first pass, not a complete professional font engineering
pipeline. Bengali font shaping is complex. The generated font may still need
manual review in a font editor, especially for anchors, marks, conjunct
positioning, and alternate glyphs.

## Credits

This project uses:

- [fontTools](https://github.com/fonttools/fonttools)
- [bijoytounicode](https://pypi.org/project/bijoytounicode/)




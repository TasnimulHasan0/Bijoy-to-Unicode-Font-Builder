#!/usr/bin/env python
"""
Build a Unicode Bengali font from a Bijoy/ANSI-encoded source font.

The output font keeps the Unicode cmap, GSUB, and GPOS tables from a Unicode
template font, then copies outlines and metrics from the ANSI font into the
matching template glyphs.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LOCAL_DEPS = Path(__file__).resolve().parent / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

try:
    from fontTools.misc.transform import Transform
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependency: fonttools. Install with "
        "`python -m pip install -r requirements.txt`."
    ) from exc

try:
    from bijoytounicode import (
        CONVERSION_MAP,
        KAARS,
        POST_SYMBOLS_MAP,
        PRE_SYMBOLS_MAP,
        REFF,
    )
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependency: bijoytounicode. Install with "
        "`python -m pip install -r requirements.txt`."
    ) from exc


VIRAMA = "\u09cd"

# SolaimanLipi-style glyph-name abbreviations.
HALF_ABBR = {
    "ka": "k",
    "kha": "kh",
    "ga": "g",
    "gha": "gh",
    "nga": "ng",
    "ca": "c",
    "cha": "ch",
    "ja": "j",
    "jha": "jh",
    "nya": "ny",
    "tta": "tt",
    "ttha": "tth",
    "dda": "dd",
    "ddha": "ddh",
    "nna": "nn",
    "ta": "t",
    "tha": "th",
    "da": "d",
    "dha": "dh",
    "na": "n",
    "pa": "p",
    "pha": "ph",
    "ba": "b",
    "bha": "bh",
    "ma": "m",
    "ya": "y",
    "ra": "r",
    "la": "l",
    "sha": "sh",
    "ssa": "ss",
    "sa": "s",
    "ha": "h",
    "rra": "rr",
    "rha": "rh",
    "yya": "yy",
}

MARK_SUFFIX = {
    0x09BE: "aakaar",
    0x09BF: "ikaar",
    0x09C0: "iikaar",
    0x09C1: "ukaar",
    0x09C2: "uukaar",
    0x09C3: "rikaar",
    0x09C4: "rrikaar",
    0x09C7: "ekaar",
    0x09C8: "aikaar",
    0x09CB: "okaar",
    0x09CC: "aukaar",
    0x09D7: "aukaar",
}

# These entries describe glyph components that do not resolve from plain cmap
# lookup because a shaping engine normally reorders them before GSUB.
EXPLICIT_UNICODE_TARGETS = {
    "\u09b0\u09cd": "bn_reph",
    VIRAMA + "\u200c": "bn_hasanta",
    VIRAMA + "\u09ac": "bn_baphala",
    VIRAMA + "\u09b0": "bn_raphala",
    VIRAMA + "\u09af": "bn_yaphala",
    VIRAMA + "\u09a4\u09c1": "bn_below_t_ukaar",
}

# Bijoy text converters normally produce U+0986 from "Av" during a later
# cleanup pass. For a font, we need to synthesize that glyph explicitly.
EXTRA_SOURCE_MAP = {
    "Av": "\u0986",
}


@dataclass(frozen=True)
class MappingEntry:
    source_text: str
    unicode_text: str
    target_glyph: str | None = None
    origin: str = "builtin"


@dataclass
class MappingReport:
    status: str
    source_text: str
    unicode_text: str
    target_glyph: str
    origin: str
    note: str


def codepoints(text: str) -> str:
    return " ".join(f"U+{ord(ch):04X}" for ch in text)


def read_text_or_codepoints(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if "\\u" in value or "\\U" in value:
        return value.encode("utf-8").decode("unicode_escape")
    tokens = re.split(r"[\s,]+", value)
    if all(re.fullmatch(r"(?:U\+|0x)[0-9A-Fa-f]{2,6}", token) for token in tokens):
        return "".join(chr(int(token.replace("U+", "0x"), 16)) for token in tokens)
    return value


def builtin_entries() -> list[MappingEntry]:
    entries: list[MappingEntry] = []
    maps = [
        ("conversion", CONVERSION_MAP),
        ("pre-symbol", PRE_SYMBOLS_MAP),
        ("post-symbol", POST_SYMBOLS_MAP),
        ("reph", REFF),
        ("kaar", KAARS),
        ("extra", EXTRA_SOURCE_MAP),
    ]
    for origin, mapping in maps:
        for source_text, unicode_text in mapping.items():
            entries.append(MappingEntry(source_text, unicode_text, None, origin))
    return entries


def csv_entries(path: Path) -> list[MappingEntry]:
    entries: list[MappingEntry] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"source", "unicode"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            source_text = read_text_or_codepoints(row.get("source", ""))
            unicode_text = read_text_or_codepoints(row.get("unicode", ""))
            target_glyph = (row.get("target_glyph") or "").strip() or None
            if source_text and unicode_text:
                entries.append(MappingEntry(source_text, unicode_text, target_glyph, str(path)))
    return entries


def build_consonant_suffix_map(template_font: TTFont) -> dict[int, str]:
    cmap = template_font["cmap"].getBestCmap()
    consonants = list(range(0x0995, 0x09BA)) + [0x09DC, 0x09DD, 0x09DF, 0x09CE]
    suffixes: dict[int, str] = {}
    for codepoint in consonants:
        glyph_name = cmap.get(codepoint)
        if glyph_name and glyph_name.startswith("bn_"):
            suffixes[codepoint] = glyph_name[3:]
    return suffixes


def half_name(suffix: str) -> str:
    return "bn_half_" + suffix


def hasanta_name(suffix: str) -> str:
    return "bn_" + HALF_ABBR.get(suffix, suffix) + "_hasanta"


def cluster_candidates(components: list[str], marks: list[str]) -> list[str]:
    candidates: list[str] = []
    if not components:
        return candidates

    mark_suffixes = [MARK_SUFFIX.get(ord(mark), "") for mark in marks]
    mark_part = "_".join(part for part in mark_suffixes if part)
    if mark_part:
        candidates.append("bn_" + "_".join(HALF_ABBR.get(c, c) for c in components) + "_" + mark_part)

    if len(components) == 1:
        cluster = "bn_" + components[0]
    else:
        cluster = "bn_" + "_".join(
            [HALF_ABBR.get(c, c) for c in components[:-1]] + [components[-1]]
        )
    candidates.append(cluster)

    if mark_part:
        candidates.append(cluster + "_" + mark_part)
    return candidates


def parse_cluster(text: str, consonant_suffix: dict[int, str]) -> tuple[list[str], list[str], int]:
    chars = list(text)
    index = 0
    components: list[str] = []

    if index >= len(chars) or ord(chars[index]) not in consonant_suffix:
        return [], [], 0

    components.append(consonant_suffix[ord(chars[index])])
    index += 1
    while index + 1 < len(chars) and chars[index] == VIRAMA and ord(chars[index + 1]) in consonant_suffix:
        components.append(consonant_suffix[ord(chars[index + 1])])
        index += 2

    if index < len(chars) and chars[index] == VIRAMA and index + 1 == len(chars):
        return components, ["HASANTA"], index + 1

    marks: list[str] = []
    while index < len(chars) and ord(chars[index]) in MARK_SUFFIX:
        marks.append(chars[index])
        index += 1

    return components, marks, index


def resolve_target_glyph(
    unicode_text: str,
    template_font: TTFont,
    consonant_suffix: dict[int, str],
) -> str | None:
    glyph_order = set(template_font.getGlyphOrder())
    cmap = template_font["cmap"].getBestCmap()

    explicit = EXPLICIT_UNICODE_TARGETS.get(unicode_text)
    if explicit in glyph_order:
        return explicit

    if unicode_text.startswith(VIRAMA):
        rest = unicode_text[1:]
        if len(rest) == 1 and ord(rest) in consonant_suffix:
            candidate = half_name(consonant_suffix[ord(rest)])
            if candidate in glyph_order:
                return candidate
        return resolve_target_glyph(rest, template_font, consonant_suffix) if rest else None

    components, marks, end_index = parse_cluster(unicode_text, consonant_suffix)
    if components and end_index == len(unicode_text):
        if marks == ["HASANTA"]:
            if len(components) == 1:
                candidate = hasanta_name(components[0])
            else:
                candidate = cluster_candidates(components, [])[0] + "_hasanta"
            if candidate in glyph_order:
                return candidate
        else:
            for candidate in cluster_candidates(components, marks):
                if candidate in glyph_order:
                    return candidate

    if len(unicode_text) == 1:
        return cmap.get(ord(unicode_text))

    return None


def source_glyph_names(source_text: str, source_font: TTFont) -> list[str]:
    cmap = source_font["cmap"].getBestCmap()
    names: list[str] = []
    for char in source_text:
        glyph_name = cmap.get(ord(char))
        if not glyph_name:
            raise KeyError(f"source cmap has no glyph for {codepoints(char)}")
        names.append(glyph_name)
    return names


def copy_source_outline(
    source_font: TTFont,
    target_font: TTFont,
    source_text: str,
    target_glyph: str,
    scale: float,
) -> None:
    glyph_set = source_font.getGlyphSet()
    source_names = source_glyph_names(source_text, source_font)
    pen = TTGlyphPen(None)
    advance = 0.0
    left_side_bearing = 0

    for index, source_name in enumerate(source_names):
        glyph_pen = TransformPen(pen, Transform(scale, 0, 0, scale, advance, 0))
        glyph_set[source_name].draw(glyph_pen)
        source_advance, source_lsb = source_font["hmtx"].metrics[source_name]
        if index == 0:
            left_side_bearing = round(source_lsb * scale)
        advance += source_advance * scale

    target_font["glyf"][target_glyph] = pen.glyph()
    target_font["hmtx"].metrics[target_glyph] = (round(advance), left_side_bearing)


def set_font_names(font: TTFont, family_name: str) -> None:
    full_name = family_name
    subfamily = "Regular"
    postscript_name = re.sub(r"[^A-Za-z0-9]", "", family_name) or "ConvertedUnicodeFont"
    names = font["name"]
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        names.setName(family_name, 1, platform_id, encoding_id, language_id)
        names.setName(subfamily, 2, platform_id, encoding_id, language_id)
        names.setName(f"{family_name} {subfamily}", 3, platform_id, encoding_id, language_id)
        names.setName(full_name, 4, platform_id, encoding_id, language_id)
        names.setName("Version 1.000; generated by make_bijoy_unicode_font.py", 5, platform_id, encoding_id, language_id)
        names.setName(postscript_name, 6, platform_id, encoding_id, language_id)


def write_report(path: Path, rows: Iterable[MappingReport]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "status",
                "origin",
                "source",
                "source_codepoints",
                "unicode",
                "unicode_codepoints",
                "target_glyph",
                "note",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.status,
                    row.origin,
                    row.source_text,
                    codepoints(row.source_text),
                    row.unicode_text,
                    codepoints(row.unicode_text),
                    row.target_glyph,
                    row.note,
                ]
            )


def convert(args: argparse.Namespace) -> int:
    source_font = TTFont(args.ansi_font)
    target_font = TTFont(args.unicode_template)
    consonant_suffix = build_consonant_suffix_map(target_font)
    scale = target_font["head"].unitsPerEm / source_font["head"].unitsPerEm

    entries = builtin_entries()
    if args.mapping_csv:
        entries.extend(csv_entries(Path(args.mapping_csv)))

    reports: list[MappingReport] = []
    assigned_targets: dict[str, MappingEntry] = {}
    copied = 0

    for entry in entries:
        target_glyph = entry.target_glyph or resolve_target_glyph(
            entry.unicode_text, target_font, consonant_suffix
        )
        if not target_glyph:
            reports.append(
                MappingReport(
                    "unresolved",
                    entry.source_text,
                    entry.unicode_text,
                    "",
                    entry.origin,
                    "Could not infer target glyph. Add target_glyph in a CSV mapping.",
                )
            )
            continue
        if target_glyph not in target_font.getGlyphOrder():
            reports.append(
                MappingReport(
                    "missing-target",
                    entry.source_text,
                    entry.unicode_text,
                    target_glyph,
                    entry.origin,
                    "Target glyph is not present in the Unicode template font.",
                )
            )
            continue
        try:
            source_glyph_names(entry.source_text, source_font)
        except KeyError as exc:
            reports.append(
                MappingReport(
                    "missing-source",
                    entry.source_text,
                    entry.unicode_text,
                    target_glyph,
                    entry.origin,
                    str(exc),
                )
            )
            continue

        duplicate = assigned_targets.get(target_glyph)
        csv_override = args.mapping_csv and entry.origin == str(Path(args.mapping_csv))
        if duplicate and not (args.overwrite_duplicates or csv_override):
            reports.append(
                MappingReport(
                    "duplicate-skipped",
                    entry.source_text,
                    entry.unicode_text,
                    target_glyph,
                    entry.origin,
                    f"Already filled by {codepoints(duplicate.source_text)} from {duplicate.origin}.",
                )
            )
            continue

        copy_source_outline(source_font, target_font, entry.source_text, target_glyph, scale)
        assigned_targets[target_glyph] = entry
        copied += 1
        reports.append(
            MappingReport(
                "copied",
                entry.source_text,
                entry.unicode_text,
                target_glyph,
                entry.origin,
                "ok",
            )
        )

    if "DSIG" in target_font:
        del target_font["DSIG"]
    set_font_names(target_font, args.family_name)
    target_font.recalcBBoxes = True
    target_font.recalcTimestamp = True
    target_font.save(args.output)
    write_report(Path(args.report), reports)

    skipped = sum(1 for row in reports if row.status != "copied")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report}")
    print(f"Copied {copied} glyph mappings; {skipped} rows need review.")
    return 0 if copied else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a Bijoy/ANSI Bengali font into a Unicode font using a Unicode template."
    )
    parser.add_argument("--ansi-font", required=True, help="Path to the Bijoy/ANSI source font.")
    parser.add_argument("--unicode-template", required=True, help="Path to the Unicode Bengali template font.")
    parser.add_argument("--output", required=True, help="Path for the generated TTF.")
    parser.add_argument("--family-name", default="SutonnyMJ Unicode", help="Family name written into the generated font.")
    parser.add_argument("--report", default="mapping-report.csv", help="CSV report path.")
    parser.add_argument(
        "--mapping-csv",
        help="Optional CSV with columns source, unicode, and optional target_glyph.",
    )
    parser.add_argument(
        "--overwrite-duplicates",
        action="store_true",
        help="Let later mappings overwrite earlier mappings that target the same glyph.",
    )
    return parser


def main() -> int:
    return convert(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

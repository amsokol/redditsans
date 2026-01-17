#!/usr/bin/env python3
"""
Scale Reddit Mono font to make it appear larger at the same point size.

This script scales all glyphs and adjusts metrics to increase the apparent
size of the font. The default scale factor of 1.08 (8%) brings the x-height
ratio from ~51% to ~55%, matching popular monospace fonts like JetBrains Mono.

Usage:
    python scripts/scale-font.py [--scale FACTOR] [--input PATH] [--output PATH]

Examples:
    # Scale all mono fonts with default 8% increase
    python scripts/scale-font.py

    # Scale a specific font file
    python scripts/scale-font.py --input fonts/mono/ttf/RedditMono-Regular.ttf --output RedditMono-Regular-Scaled.ttf

    # Use a custom scale factor (10% larger)
    python scripts/scale-font.py --scale 1.10
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.transformPen import TransformPen
except ImportError:
    print("Error: fonttools is required. Install with: pip install fonttools")
    sys.exit(1)


def scale_glyph_ttf(glyph, glyf_table, scale_factor):
    """Scale a TrueType glyph (TTF format)."""
    if glyph.isComposite():
        # Scale composite glyph offsets
        for component in glyph.components:
            if hasattr(component, 'x'):
                component.x = int(component.x * scale_factor)
            if hasattr(component, 'y'):
                component.y = int(component.y * scale_factor)
    elif glyph.numberOfContours > 0:
        # Scale simple glyph coordinates
        coords = glyph.coordinates
        scaled_coords = [(int(x * scale_factor), int(y * scale_factor)) for x, y in coords]
        glyph.coordinates = type(coords)(scaled_coords)

    # Scale bounding box
    if hasattr(glyph, 'xMin') and glyph.numberOfContours != 0:
        glyph.xMin = int(glyph.xMin * scale_factor)
        glyph.yMin = int(glyph.yMin * scale_factor)
        glyph.xMax = int(glyph.xMax * scale_factor)
        glyph.yMax = int(glyph.yMax * scale_factor)


def scale_cff_glyphs(font, scale_factor):
    """Scale CFF/OTF glyphs."""
    if 'CFF ' not in font:
        return False

    cff = font['CFF ']
    top_dict = cff.cff.topDictIndex[0]
    char_strings = top_dict.CharStrings

    for glyph_name in char_strings.keys():
        cs = char_strings[glyph_name]
        # Create a new pen with scaling transformation
        pen = T2CharStringPen(width=None, glyphSet=char_strings)
        transform_pen = TransformPen(pen, (scale_factor, 0, 0, scale_factor, 0, 0))

        # Draw the glyph through the transform pen
        cs.draw(transform_pen)

        # Get the new charstring
        new_cs = pen.getCharString(private=top_dict.Private, globalSubrs=cff.cff.GlobalSubrs)
        char_strings[glyph_name] = new_cs

    return True


def scale_font(input_path, output_path, scale_factor=1.08, rename_from=None, rename_to=None):
    """
    Scale a font file by the given factor.

    Args:
        input_path: Path to the input font file
        output_path: Path for the output font file
        scale_factor: How much to scale (1.08 = 8% larger)
        rename_from: Original family name to replace (optional)
        rename_to: New family name (optional)
    """
    print(f"Loading font: {input_path}")
    font = TTFont(input_path)

    is_cff = 'CFF ' in font
    print(f"Font type: {'CFF/OTF' if is_cff else 'TrueType/TTF'}")
    print(f"Scale factor: {scale_factor} ({(scale_factor - 1) * 100:.1f}% increase)")

    # Rename font if requested
    if rename_from and rename_to:
        print(f"Renaming: {rename_from} → {rename_to}")
        rename_font(font, rename_from, rename_to)

    # Scale glyphs based on font type
    if is_cff:
        scale_cff_glyphs(font, scale_factor)
    else:
        # TrueType font
        glyf = font['glyf']
        for glyph_name in glyf.keys():
            glyph = glyf[glyph_name]
            if glyph.numberOfContours != 0:  # Skip empty glyphs
                scale_glyph_ttf(glyph, glyf, scale_factor)

    # Scale horizontal metrics (advance widths and left side bearings)
    hmtx = font['hmtx']
    for glyph_name in hmtx.metrics:
        width, lsb = hmtx.metrics[glyph_name]
        hmtx.metrics[glyph_name] = (int(width * scale_factor), int(lsb * scale_factor))

    # Scale vertical metrics if present
    if 'vmtx' in font:
        vmtx = font['vmtx']
        for glyph_name in vmtx.metrics:
            height, tsb = vmtx.metrics[glyph_name]
            vmtx.metrics[glyph_name] = (int(height * scale_factor), int(tsb * scale_factor))

    # Scale head table metrics
    head = font['head']
    head.xMin = int(head.xMin * scale_factor)
    head.yMin = int(head.yMin * scale_factor)
    head.xMax = int(head.xMax * scale_factor)
    head.yMax = int(head.yMax * scale_factor)

    # Scale hhea table (horizontal header)
    hhea = font['hhea']
    hhea.ascent = int(hhea.ascent * scale_factor)
    hhea.descent = int(hhea.descent * scale_factor)
    hhea.lineGap = int(hhea.lineGap * scale_factor)
    hhea.advanceWidthMax = int(hhea.advanceWidthMax * scale_factor)
    hhea.minLeftSideBearing = int(hhea.minLeftSideBearing * scale_factor)
    hhea.minRightSideBearing = int(hhea.minRightSideBearing * scale_factor)
    hhea.xMaxExtent = int(hhea.xMaxExtent * scale_factor)

    # Scale OS/2 table metrics
    if 'OS/2' in font:
        os2 = font['OS/2']
        os2.sTypoAscender = int(os2.sTypoAscender * scale_factor)
        os2.sTypoDescender = int(os2.sTypoDescender * scale_factor)
        os2.sTypoLineGap = int(os2.sTypoLineGap * scale_factor)
        os2.usWinAscent = int(os2.usWinAscent * scale_factor)
        os2.usWinDescent = int(os2.usWinDescent * scale_factor)
        os2.ySubscriptXSize = int(os2.ySubscriptXSize * scale_factor)
        os2.ySubscriptYSize = int(os2.ySubscriptYSize * scale_factor)
        os2.ySubscriptXOffset = int(os2.ySubscriptXOffset * scale_factor)
        os2.ySubscriptYOffset = int(os2.ySubscriptYOffset * scale_factor)
        os2.ySuperscriptXSize = int(os2.ySuperscriptXSize * scale_factor)
        os2.ySuperscriptYSize = int(os2.ySuperscriptYSize * scale_factor)
        os2.ySuperscriptXOffset = int(os2.ySuperscriptXOffset * scale_factor)
        os2.ySuperscriptYOffset = int(os2.ySuperscriptYOffset * scale_factor)
        os2.yStrikeoutSize = int(os2.yStrikeoutSize * scale_factor)
        os2.yStrikeoutPosition = int(os2.yStrikeoutPosition * scale_factor)
        os2.sxHeight = int(os2.sxHeight * scale_factor)
        os2.sCapHeight = int(os2.sCapHeight * scale_factor)
        os2.xAvgCharWidth = int(os2.xAvgCharWidth * scale_factor)

    # Scale vhea table if present (vertical header)
    if 'vhea' in font:
        vhea = font['vhea']
        vhea.ascent = int(vhea.ascent * scale_factor)
        vhea.descent = int(vhea.descent * scale_factor)
        vhea.lineGap = int(vhea.lineGap * scale_factor)
        vhea.advanceHeightMax = int(vhea.advanceHeightMax * scale_factor)
        vhea.minTopSideBearing = int(vhea.minTopSideBearing * scale_factor)
        vhea.minBottomSideBearing = int(vhea.minBottomSideBearing * scale_factor)
        vhea.yMaxExtent = int(vhea.yMaxExtent * scale_factor)

    # Scale post table metrics
    if 'post' in font:
        post = font['post']
        post.underlinePosition = int(post.underlinePosition * scale_factor)
        post.underlineThickness = int(post.underlineThickness * scale_factor)

    # Scale kern table if present (legacy kerning)
    if 'kern' in font:
        kern = font['kern']
        for table in kern.kernTables:
            if hasattr(table, 'kernTable'):
                for pair, value in list(table.kernTable.items()):
                    table.kernTable[pair] = int(value * scale_factor)

    # Scale GPOS table if present (OpenType kerning and positioning)
    if 'GPOS' in font:
        gpos = font['GPOS']
        scale_gpos_values(gpos.table, scale_factor)

    # Save the scaled font
    print(f"Saving scaled font to: {output_path}")
    font.save(output_path)
    print("Done!")

    return True


def scale_gpos_values(gpos_table, scale_factor):
    """Scale values in GPOS table (kerning, positioning, etc.)."""
    if not hasattr(gpos_table, 'LookupList') or gpos_table.LookupList is None:
        return

    for lookup in gpos_table.LookupList.Lookup:
        for subtable in lookup.SubTable:
            scale_gpos_subtable(subtable, scale_factor)


def scale_gpos_subtable(subtable, scale_factor):
    """Scale a GPOS subtable."""
    # Single adjustment (lookup type 1)
    if hasattr(subtable, 'SinglePos'):
        for record in subtable.SinglePos:
            scale_value_record(record, scale_factor)

    # Pair adjustment (lookup type 2) - kerning
    if hasattr(subtable, 'PairSet'):
        for pair_set in subtable.PairSet:
            if pair_set:
                for pair_value in pair_set.PairValueRecord:
                    if hasattr(pair_value, 'Value1') and pair_value.Value1:
                        scale_value_record(pair_value.Value1, scale_factor)
                    if hasattr(pair_value, 'Value2') and pair_value.Value2:
                        scale_value_record(pair_value.Value2, scale_factor)

    if hasattr(subtable, 'Class1Record'):
        for class1_record in subtable.Class1Record:
            for class2_record in class1_record.Class2Record:
                if hasattr(class2_record, 'Value1') and class2_record.Value1:
                    scale_value_record(class2_record.Value1, scale_factor)
                if hasattr(class2_record, 'Value2') and class2_record.Value2:
                    scale_value_record(class2_record.Value2, scale_factor)

    # Mark positioning
    if hasattr(subtable, 'BaseArray'):
        for base_record in subtable.BaseArray.BaseRecord:
            for anchor in base_record.BaseAnchor:
                if anchor:
                    scale_anchor(anchor, scale_factor)

    if hasattr(subtable, 'MarkArray'):
        for mark_record in subtable.MarkArray.MarkRecord:
            if mark_record.MarkAnchor:
                scale_anchor(mark_record.MarkAnchor, scale_factor)

    if hasattr(subtable, 'Mark2Array'):
        for mark2_record in subtable.Mark2Array.Mark2Record:
            for anchor in mark2_record.Mark2Anchor:
                if anchor:
                    scale_anchor(anchor, scale_factor)

    if hasattr(subtable, 'LigatureArray'):
        for lig_attach in subtable.LigatureArray.LigatureAttach:
            for component in lig_attach.ComponentRecord:
                for anchor in component.LigatureAnchor:
                    if anchor:
                        scale_anchor(anchor, scale_factor)


def scale_value_record(value_record, scale_factor):
    """Scale a GPOS ValueRecord."""
    if hasattr(value_record, 'XPlacement') and value_record.XPlacement:
        value_record.XPlacement = int(value_record.XPlacement * scale_factor)
    if hasattr(value_record, 'YPlacement') and value_record.YPlacement:
        value_record.YPlacement = int(value_record.YPlacement * scale_factor)
    if hasattr(value_record, 'XAdvance') and value_record.XAdvance:
        value_record.XAdvance = int(value_record.XAdvance * scale_factor)
    if hasattr(value_record, 'YAdvance') and value_record.YAdvance:
        value_record.YAdvance = int(value_record.YAdvance * scale_factor)


def scale_anchor(anchor, scale_factor):
    """Scale a GPOS Anchor."""
    if hasattr(anchor, 'XCoordinate'):
        anchor.XCoordinate = int(anchor.XCoordinate * scale_factor)
    if hasattr(anchor, 'YCoordinate'):
        anchor.YCoordinate = int(anchor.YCoordinate * scale_factor)


def rename_font(font, old_family, new_family):
    """
    Rename a font family.

    Args:
        font: TTFont object
        old_family: Original family name (e.g., "Reddit Mono")
        new_family: New family name (e.g., "RedditRadon Mono")
    """
    if 'name' not in font:
        return

    name_table = font['name']

    # Name IDs to update:
    # 1 = Family name
    # 3 = Unique identifier
    # 4 = Full name
    # 6 = PostScript name
    # 16 = Typographic Family name
    # 18 = Compatible Full (Mac only)

    for record in name_table.names:
        try:
            text = record.toUnicode()
        except:
            continue

        # Replace family name in the string
        if old_family in text:
            new_text = text.replace(old_family, new_family)
            name_table.setName(
                new_text,
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID
            )

        # Also handle no-space versions (for PostScript names)
        old_nospace = old_family.replace(" ", "")
        new_nospace = new_family.replace(" ", "")
        if old_nospace in text and old_family not in text:
            new_text = text.replace(old_nospace, new_nospace)
            name_table.setName(
                new_text,
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID
            )

    # Update CFF table if present
    if 'CFF ' in font:
        cff = font['CFF ']
        cff_font = cff.cff
        if hasattr(cff_font, 'fontNames'):
            for i, name in enumerate(cff_font.fontNames):
                old_nospace = old_family.replace(" ", "")
                new_nospace = new_family.replace(" ", "")
                if old_nospace in name:
                    cff_font.fontNames[i] = name.replace(old_nospace, new_nospace)

        top_dict = cff_font.topDictIndex[0]
        if hasattr(top_dict, 'FamilyName'):
            if old_family in top_dict.FamilyName:
                top_dict.FamilyName = top_dict.FamilyName.replace(old_family, new_family)
        if hasattr(top_dict, 'FullName'):
            if old_family in top_dict.FullName:
                top_dict.FullName = top_dict.FullName.replace(old_family, new_family)


def find_mono_fonts(fonts_dir):
    """Find all Reddit Mono font files."""
    mono_dir = Path(fonts_dir) / "mono"
    font_files = []

    if not mono_dir.exists():
        print(f"Warning: Mono fonts directory not found: {mono_dir}")
        return font_files

    # Find TTF files
    ttf_dir = mono_dir / "ttf"
    if ttf_dir.exists():
        font_files.extend(ttf_dir.glob("*.ttf"))

    # Find OTF files
    otf_dir = mono_dir / "otf"
    if otf_dir.exists():
        font_files.extend(otf_dir.glob("*.otf"))

    # Find variable fonts
    var_dir = mono_dir / "variable"
    if var_dir.exists():
        font_files.extend(var_dir.glob("*.ttf"))

    return sorted(font_files)


def main():
    parser = argparse.ArgumentParser(
        description="Scale Reddit Mono font to appear larger at the same point size.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--scale", "-s",
        type=float,
        default=1.08,
        help="Scale factor (default: 1.08 for 8%% increase)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input font file (if not specified, processes all mono fonts)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output font file (required if --input is specified)"
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="Suffix to add to output filename when processing multiple fonts (default: overwrite original)"
    )
    parser.add_argument(
        "--fonts-dir",
        type=str,
        default="fonts",
        help="Directory containing font files (default: fonts)"
    )
    parser.add_argument(
        "--rename",
        type=str,
        help="Rename font family (format: 'Old Name:New Name', e.g., 'Reddit Mono:RedditRadon Mono')"
    )

    args = parser.parse_args()

    # Parse rename argument
    rename_from = None
    rename_to = None
    if args.rename:
        if ':' not in args.rename:
            print("Error: --rename format must be 'Old Name:New Name'")
            sys.exit(1)
        rename_from, rename_to = args.rename.split(':', 1)
        print(f"Will rename: '{rename_from}' → '{rename_to}'")

    # Validate scale factor
    if args.scale <= 0:
        print("Error: Scale factor must be positive")
        sys.exit(1)

    if args.scale > 2.0:
        print("Warning: Scale factor > 2.0 may produce unexpected results")

    # Single file mode
    if args.input:
        if not args.output:
            print("Error: --output is required when using --input")
            sys.exit(1)

        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)

        scale_font(args.input, args.output, args.scale, rename_from, rename_to)
        return

    # Batch mode: process all mono fonts
    script_dir = Path(__file__).parent.parent
    fonts_dir = script_dir / args.fonts_dir

    font_files = find_mono_fonts(fonts_dir)

    if not font_files:
        print(f"No mono font files found in {fonts_dir / 'mono'}")
        print("Make sure you've built the fonts first with: make build")
        sys.exit(1)

    print(f"Found {len(font_files)} mono font files")
    print(f"Scale factor: {args.scale} ({(args.scale - 1) * 100:.1f}% increase)")
    print()

    for font_path in font_files:
        if args.suffix:
            output_path = font_path.parent / f"{font_path.stem}{args.suffix}{font_path.suffix}"
        else:
            output_path = font_path

        try:
            scale_font(str(font_path), str(output_path), args.scale, rename_from, rename_to)
        except Exception as e:
            print(f"Error processing {font_path}: {e}")
            continue

        print()

    print("All fonts processed!")


if __name__ == "__main__":
    main()

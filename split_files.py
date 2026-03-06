#!/usr/bin/env python3
"""Split large markdown files into smaller pages for Jekyll."""

import os
import re

# README.md splitting configuration
# basics: ch1-5 (lines 49-707), config: ch6-10 (lines 708-1289),
# advanced: ch11-17 (lines 1290-1925), team: ch18-24 (lines 1926-3855),
# expert: ch25-32 (lines 3856-end)

README_NAV = "[← トップ](/) | [基礎編](basics) | [設定編](config) | [応用編](advanced) | [チーム編](team) | [上級編](expert)"

README_SPLITS = [
    {
        "output": "guide/basics.md",
        "title": "Claude Code 活用ガイド - 基礎編（章1〜5）",
        "start": 49,  # line number (1-based) where content starts
        "end": 707,   # last line of this section
        "prev": None,
        "prev_label": None,
        "next": "config",
        "next_label": "設定編",
    },
    {
        "output": "guide/config.md",
        "title": "Claude Code 活用ガイド - 設定編（章6〜10）",
        "start": 708,
        "end": 1289,
        "prev": "basics",
        "prev_label": "基礎編",
        "next": "advanced",
        "next_label": "応用編",
    },
    {
        "output": "guide/advanced.md",
        "title": "Claude Code 活用ガイド - 応用編（章11〜17）",
        "start": 1290,
        "end": 1925,
        "prev": "config",
        "prev_label": "設定編",
        "next": "team",
        "next_label": "チーム編",
    },
    {
        "output": "guide/team.md",
        "title": "Claude Code 活用ガイド - チーム編（章18〜24）",
        "start": 1926,
        "end": 3855,
        "prev": "advanced",
        "prev_label": "応用編",
        "next": "expert",
        "next_label": "上級編",
    },
    {
        "output": "guide/expert.md",
        "title": "Claude Code 活用ガイド - 上級編（章25〜32）",
        "start": 3856,
        "end": None,  # to end of file
        "prev": "team",
        "prev_label": "チーム編",
        "next": None,
        "next_label": None,
    },
]

BUILD_NAV = "[← トップ](/) | [基礎編](foundations) | [機能編A](features) | [ファインチューニング](finetuning) | [機能編B](features2) | [運用編](operations) | [専門編](specialist)"

BUILD_SPLITS = [
    {
        "output": "build/foundations.md",
        "title": "ローカルLLM構築ガイド - 基礎・設計編（章1〜5）",
        "start": 44,
        "end": 1521,
        "prev": None,
        "prev_label": None,
        "next": "features",
        "next_label": "機能編A",
    },
    {
        "output": "build/features.md",
        "title": "ローカルLLM構築ガイド - 高度な機能編A（章6〜8）",
        "start": 1522,
        "end": 2395,
        "prev": "foundations",
        "prev_label": "基礎編",
        "next": "finetuning",
        "next_label": "ファインチューニング",
    },
    {
        "output": "build/finetuning.md",
        "title": "ローカルLLM構築ガイド - ファインチューニング（章9）",
        "start": 2396,
        "end": 4311,
        "prev": "features",
        "prev_label": "機能編A",
        "next": "features2",
        "next_label": "機能編B",
    },
    {
        "output": "build/features2.md",
        "title": "ローカルLLM構築ガイド - 高度な機能編B（章10〜11）",
        "start": 4312,
        "end": 5119,
        "prev": "finetuning",
        "prev_label": "ファインチューニング",
        "next": "operations",
        "next_label": "運用編",
    },
    {
        "output": "build/operations.md",
        "title": "ローカルLLM構築ガイド - 運用・最適化編（章12〜15）",
        "start": 5120,
        "end": 6036,
        "prev": "features2",
        "prev_label": "機能編B",
        "next": "specialist",
        "next_label": "専門編",
    },
    {
        "output": "build/specialist.md",
        "title": "ローカルLLM構築ガイド - 専門技術編（章16〜19 + 付録）",
        "start": 6037,
        "end": None,
        "prev": "operations",
        "prev_label": "運用編",
        "next": None,
        "next_label": None,
    },
]


def make_frontmatter(title):
    return f"""---
layout: default
title: "{title}"
---
"""


def make_top_nav(nav_str):
    return f"""{nav_str}

---

"""


def make_bottom_nav(prev_page, prev_label, next_page, next_label):
    parts = []
    if prev_page:
        parts.append(f"[← 前: {prev_label}]({prev_page})")
    if next_page:
        parts.append(f"[次: {next_label} →]({next_page})")
    return f"""
---

{' | '.join(parts)}
"""


def fix_liquid_templates(content):
    """Wrap ${{ }} patterns in {% raw %}{% endraw %} if not already wrapped."""
    # Find all occurrences of ${{ or ${ that look like GitHub Actions expressions
    # We need to be careful not to double-wrap
    # Strategy: find lines with ${{ that aren't already in raw blocks
    lines = content.split('\n')
    result_lines = []
    in_raw = False

    for line in lines:
        if '{%' in line and 'raw' in line:
            if '{% raw %}' in line:
                in_raw = True
            if '{% endraw %}' in line:
                in_raw = False
            result_lines.append(line)
        elif not in_raw and ('${{' in line or ('{{' in line and not line.strip().startswith('|'))):
            # Check if the line has GitHub Actions style expressions
            if '${{' in line:
                # Wrap ${{ ... }} patterns with raw/endraw tags
                RAW_OPEN = '{%' + ' raw %}'
                RAW_CLOSE = '{%' + ' endraw %}'
                fixed = re.sub(
                    r'\$\{\{([^}]*(?:\}[^}][^}]*)*)\}\}',
                    lambda m: RAW_OPEN + '${{' + m.group(1) + '}}' + RAW_CLOSE,
                    line
                )
                result_lines.append(fixed)
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)


def strip_outer_raw(content):
    """Remove {% raw %} at start and {% endraw %} at end of content."""
    # Remove leading {% raw %} with surrounding whitespace/newlines
    content = re.sub(r'^\s*\{%\s*raw\s*%\}\s*\n', '', content)
    # Remove trailing {% endraw %} with surrounding whitespace/newlines
    content = re.sub(r'\n\s*\{%\s*endraw\s*%\}\s*$', '', content)
    return content


def split_file(source_path, splits, nav_str, base_dir):
    """Read source file and create split output files."""
    print(f"Reading {source_path}...")
    with open(source_path, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()

    total_lines = len(all_lines)
    print(f"  Total lines: {total_lines}")

    # Create output directory
    os.makedirs(base_dir, exist_ok=True)

    for split in splits:
        output_path = os.path.join(os.path.dirname(source_path), split["output"])
        start_idx = split["start"] - 1  # convert to 0-based
        end_idx = split["end"] if split["end"] else total_lines  # end is exclusive

        # Extract content lines
        content_lines = all_lines[start_idx:end_idx]
        content = ''.join(content_lines)

        # Strip outer raw tags if present (we'll add inline ones)
        content = strip_outer_raw(content)

        # Fix Liquid template expressions
        content = fix_liquid_templates(content)

        # Build output
        output_parts = []
        output_parts.append(make_frontmatter(split["title"]))
        output_parts.append(make_top_nav(nav_str))
        output_parts.append(content.rstrip('\n'))
        output_parts.append(make_bottom_nav(
            split["prev"], split["prev_label"],
            split["next"], split["next_label"]
        ))

        output_content = '\n'.join(output_parts)

        # Write output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)

        line_count = output_content.count('\n')
        print(f"  Written {output_path} ({line_count} lines, src lines {split['start']}-{split['end'] or total_lines})")


def update_readme_frontmatter(source_path):
    """Remove Jekyll frontmatter from README.md so it stays as GitHub README."""
    print(f"\nUpdating {source_path} frontmatter...")
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove frontmatter (--- ... ---) at start of file
    content = re.sub(r'^---\n.*?---\n', '', content, flags=re.DOTALL)
    content = content.lstrip('\n')

    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Frontmatter removed from {source_path}")


if __name__ == "__main__":
    base_dir = "/home/neko/projects/claude-code-guide"

    print("=== Splitting README.md ===")
    split_file(
        source_path=os.path.join(base_dir, "README.md"),
        splits=README_SPLITS,
        nav_str=README_NAV,
        base_dir=os.path.join(base_dir, "guide"),
    )

    print("\n=== Splitting BUILD_YOUR_OWN.md ===")
    split_file(
        source_path=os.path.join(base_dir, "BUILD_YOUR_OWN.md"),
        splits=BUILD_SPLITS,
        nav_str=BUILD_NAV,
        base_dir=os.path.join(base_dir, "build"),
    )

    print("\nDone!")

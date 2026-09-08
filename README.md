# Canvas Course Assistant

A Codex skill that fetches and updates HKUST Canvas course content via Chrome, with smart caching so repeat invocations only fetch what's new.

## What it does

Given a Canvas course (by ID or by name), the skill:

1. Navigates to the course's modules, assignments, announcements, and syllabus
2. Compares against a local cache
3. Returns only what's **new or changed** since the last fetch
4. Saves the updated cache for next time

Designed for weekly course check-ins — quickly see what changed since you last looked.

## Install

This is a personal Codex skill. To install:

```bash
# Copy to your Codex skills directory
mkdir -p ~/.codex/skills
cp -R ./ ~/.codex/skills/canvas-course-assistant/
```

## Usage

In any Codex conversation:

```
$canvas-course-assistant PPOL2110
$canvas-course-assistant DASC2010
$canvas-course-assistant 73872
```

Or in natural language:

```
帮我看下 PPOL2110 有什么新的
刷新一下 DASC2010
canvas 课程 72116 有更新吗?
```

To force a full refresh (ignore cache): `强制刷新` or `--refresh`.

## How caching works

Cache location: `~/Documents/Codex/.canvas_course_cache/<course_id>.json`

Per section (syllabus, modules, assignments, announcements), the cache stores:
- For lists: `id`, `name`, key metadata (e.g., `due_at`, `points`)
- For syllabus: content hash + URL

A fetch only returns:
- **New** items (not in cache)
- **Changed** items (in cache but with different fields)
- **Removed** items (in cache but no longer on Canvas)

Unchanged items are reported by count, not relisted.

## Files

```
canvas-course-assistant/
├── SKILL.md                 # AI instructions (loaded by Codex)
├── agents/
│   └── openai.yaml          # UI metadata
├── scripts/
│   └── diff_cache.py        # Cache comparison logic
└── README.md                # This file
```

## Tested with

- HKUST Canvas (canvas.ust.hk) — 2026-27 Fall
- PPOL2110 (Science, Technology and Society in China)
- DASC2010 (Calculus for Data Analytics in Science)

---
name: canvas-course-assistant
description: "Fetch or update a HKUST Canvas course's content via Chrome, with smart caching. Use when the user wants to see what's new on a Canvas course (modules, assignments, announcements, syllabus) without re-fetching everything each time."
metadata:
  short-description: "Canvas 课程增量更新助手"
---

# Canvas Course Assistant

Fetch or update a HKUST Canvas course's content via Chrome, **with smart caching** so repeat invocations only fetch what's new.

## When to use this skill

Trigger when the user:
- Mentions a Canvas course by name or course ID (e.g., "PPOL2110", "DASC2010", "帮我看 canvas 上的 73872")
- Wants to know what's new on a course (announcements, modules, assignments)
- Wants to "check" / "update" / "reload" / "刷新" a Canvas course's content
- Wants the syllabus, modules, assignments, or announcements of a Canvas course

Do **not** use this skill for:
- Reading or analyzing a specific file the user already has
- Doing work on a single document that has already been fetched
- Cross-course comparisons (use the orchestrator thread instead)

## Core principle: **incremental fetch**

A first invocation fetches everything and saves a cache. Every subsequent invocation **compares against the cache** and only fetches sections that changed. The cache is keyed by Canvas course ID.

- **Cache location**: `~/Documents/Codex/.canvas_course_cache/<course_id>.json`
- **What's cached**: course title, syllabus URL + content hash, modules (id + name + url), assignments (id + name + due_at + points), announcements (id + title + posted_at)
- **What's "new"**: items in Canvas not in cache (truly new), or items in cache whose key fields differ (e.g., due date changed)
- **What's "unchanged"**: items in cache whose fields match (we report count, don't repeat details)

If the user asks for a **full refresh**, force-refetch every section regardless of cache.

## Workflow

1. **Identify the course**: parse the user's input
   - If they gave a Canvas course ID (e.g., `73872`), use it directly
   - If they gave a name (e.g., "PPOL2110"), navigate Chrome to `https://canvas.ust.hk/courses` and find the matching course ID from the All Courses list
   - If ambiguous, ask the user to confirm

2. **Read the cache** at `cache/<course_id>.json`. If absent, this is a fresh fetch — proceed with step 3 for every section.

3. **For each section** (Syllabus, Modules, Assignments, Announcements), decide what to fetch:
   - **Syllabus**: compare content hash from cache; only re-fetch if hash differs (use Playwright `domSnapshot()` text to compute hash)
   - **Modules**: re-fetch the modules page and diff items by `(id, name)`. Items whose `id` is new or whose `name` changed are "new/changed"
   - **Assignments**: re-fetch assignments list, diff by `(id, name, due_at, points)`. New/changed if any field differs
   - **Announcements**: re-fetch announcements list, diff by `(id, title, posted_at)`. New if not in cache

   Run the cache-diff logic via `scripts/diff_cache.py`.

4. **Update the cache** with the freshly fetched data for the sections you touched.

5. **Report** to the user:
   - For first-time fetches: full summary
   - For subsequent: brief "what's new since last fetch" + relevant new content
   - Format as Markdown with clear sections
   - Save the report to `~/Documents/Codex/<date>-<course>-canvas-report.md` so the user has a record

## Chrome navigation patterns

Use the in-app Chrome browser (via Codex MCP) to navigate Canvas. The user is already logged in to HKUST SSO — do **not** request credentials.

For each section, the typical Chrome URL pattern:
- Course home: `https://canvas.ust.hk/courses/<id>`
- Syllabus (PDF inline): `https://canvas.ust.hk/courses/<id>/assignments/syllabus` — Syllabus opens an embedded PDF viewer. Take a `domSnapshot()` and look for the DocViewer section to extract the PDF iframe URL.
- Modules: `https://canvas.ust.hk/courses/<id>/modules` — `domSnapshot()` contains module headings and item links
- Assignments: `https://canvas.ust.hk/courses/<id>/assignments` — Upcoming + Past assignments are listed in the snapshot
- Announcements: `https://canvas.ust.hk/courses/<id>/announcements`
- All Courses (for ID lookup): `https://canvas.ust.hk/courses` — table of courses with names and IDs

For each item link in the snapshot, the URL pattern is `/courses/<id>/modules/items/<item_id>` for modules or `/courses/<id>/assignments/<id>` for assignments. Use these URLs to construct entry points.

Tab management: prefer reusing a single tab across sections. If a tab is unresponsive, create a fresh one.

## Output format

After each invocation, give the user:

```
📊 <Course Code> · <Course Title> · <fetch status>

🆕 What's new since <last fetch>:
  + <item>
  ~ <changed item>: <what changed>

📂 Sections fetched this round:
  - Syllabus: <new | unchanged | N changes>
  - Modules: <new | unchanged | +N items>
  - Assignments: <new | unchanged | +N / ~N>
  - Announcements: <N new>

📋 Full report saved to: <path>
```

For a fresh fetch (no cache), show the full overview and write it to a markdown file as well.

## Cache management

To force a full refresh, the user can say "强制刷新" / "full refresh" / "重新抓". To wipe the cache for a course, delete `cache/<course_id>.json`. To wipe all caches, delete `cache/` entirely.

Cache files are JSON, human-readable, and safe to inspect.

## What this skill does **not** do

- It does not download files (videos, PDFs). It only extracts URLs and metadata.
- It does not parse the contents of files (Slides PDFs, etc.) — that's the next stage, after this skill runs.
- It does not make any submissions or modifications on Canvas — read-only.
- It does not handle login. The user must already be authenticated.


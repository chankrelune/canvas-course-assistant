#!/usr/bin/env python3
"""
diff_cache.py — Compare newly fetched Canvas course data against cache.

Subcommands:
    diff    <course_id> <section> --input <json> [--refresh]
            Compare new data against cache. Print JSON diff report.
    save    <course_id> <section> --input <json>
            Save new data as cache (overwrites section).
    inspect <course_id>
            Show what's currently in the cache for the course.

Sections: syllabus, modules, assignments, announcements

Examples:
    python diff_cache.py diff 73872 modules --input fresh.json
    python diff_cache.py save 73872 modules --input fresh.json
    python diff_cache.py inspect 73872
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone


SKILL_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = Path.home() / "Documents" / "Codex" / ".canvas_course_cache"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cache(course_id: str) -> dict:
    cache_file = CACHE_DIR / f"{course_id}.json"
    if not cache_file.exists():
        return {
            "course_id": course_id,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "sections": {},
        }
    try:
        with cache_file.open() as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: cache corrupted for {course_id}: {e}", file=sys.stderr)
        return {
            "course_id": course_id,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "sections": {},
        }


def save_cache_to_disk(course_id: str, cache_data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{course_id}.json"
    cache_data["updated_at"] = now_iso()
    with cache_file.open("w") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)


def diff_items_by_keys(cached_items, new_items, track_keys):
    cached_by_id = {i["id"]: i for i in (cached_items or []) if "id" in i}
    new_by_id = {i["id"]: i for i in (new_items or []) if "id" in i}
    new_only, changed, removed, unchanged = [], [], [], 0
    for new_id, new_item in new_by_id.items():
        if new_id not in cached_by_id:
            new_only.append(new_item)
        else:
            cached_item = cached_by_id[new_id]
            diffs = {}
            for k in track_keys:
                if cached_item.get(k) != new_item.get(k):
                    diffs[k] = {"old": cached_item.get(k), "new": new_item.get(k)}
            if diffs:
                changed.append({"id": new_id, "name": new_item.get("name"), "changes": diffs})
            else:
                unchanged += 1
    for cached_id in cached_by_id:
        if cached_id not in new_by_id:
            removed.append(cached_by_id[cached_id])
    return new_only, changed, removed, unchanged


def diff_section(course_id, section, new_data, refresh=False):
    cache = load_cache(course_id)
    cached_section = cache.get("sections", {}).get(section, {})
    cached_items = cached_section.get("items", [])

    is_first_fetch = (not cached_items) and (not refresh)

    if section == "syllabus":
        # Single object comparison
        if is_first_fetch:
            return {
                "course_id": course_id, "section": section, "is_first_fetch": True,
                "new_items": [new_data] if new_data else [],
                "changed_items": [], "removed_items": [], "unchanged_count": 0,
            }
        diffs = {}
        for k in ["content_hash", "url"]:
            if cached_section.get(k) != new_data.get(k):
                diffs[k] = {"old": cached_section.get(k), "new": new_data.get(k)}
        if diffs:
            return {
                "course_id": course_id, "section": section, "is_first_fetch": False,
                "new_items": [], "changed_items": [{"name": "syllabus", "changes": diffs}],
                "removed_items": [], "unchanged_count": 0,
            }
        return {
            "course_id": course_id, "section": section, "is_first_fetch": False,
            "new_items": [], "changed_items": [], "removed_items": [],
            "unchanged_count": 1,
        }

    track_keys = {
        "modules": ["name", "url", "module_name"],
        "assignments": ["name", "due_at", "points", "url"],
        "announcements": ["title", "posted_at", "url"],
    }[section]

    new_items = new_data.get("items", []) if isinstance(new_data, dict) else new_data
    new_only, changed, removed, unchanged = diff_items_by_keys(cached_items, new_items, track_keys)
    return {
        "course_id": course_id, "section": section, "is_first_fetch": is_first_fetch,
        "new_items": new_only, "changed_items": changed,
        "removed_items": removed, "unchanged_count": unchanged,
    }


def cmd_diff(args):
    if not args.input:
        print("ERROR: --input required", file=sys.stderr)
        return 1
    try:
        with open(args.input) as f:
            new_data = json.load(f)
    except Exception as e:
        print(f"ERROR reading input: {e}", file=sys.stderr)
        return 1
    report = diff_section(args.course_id, args.section, new_data, args.refresh)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def cmd_save(args):
    if not args.input:
        print("ERROR: --input required", file=sys.stderr)
        return 1
    try:
        with open(args.input) as f:
            payload = json.load(f)
    except Exception as e:
        print(f"ERROR reading input: {e}", file=sys.stderr)
        return 1
    cache = load_cache(args.course_id)
    if "course_name" in payload:
        cache["course_name"] = payload["course_name"]
    cache.setdefault("sections", {})
    section_data = payload.get("section_data", payload)
    section_data["fetched_at"] = now_iso()
    cache["sections"][args.section] = section_data
    save_cache_to_disk(args.course_id, cache)
    print(json.dumps({
        "saved": True,
        "course_id": args.course_id,
        "section": args.section,
        "cache_path": str(CACHE_DIR / f"{args.course_id}.json"),
    }, indent=2))
    return 0


def cmd_inspect(args):
    cache = load_cache(args.course_id)
    sections = cache.get("sections", {})
    if not sections:
        print(f"No cache found for course {args.course_id}")
        return 0
    print(json.dumps({
        "course_id": args.course_id,
        "course_name": cache.get("course_name"),
        "created_at": cache.get("created_at"),
        "updated_at": cache.get("updated_at"),
        "sections": {
            name: {
                "fetched_at": sec.get("fetched_at"),
                "item_count": len(sec.get("items", [])) if isinstance(sec.get("items"), list) else 1,
            }
            for name, sec in sections.items()
        },
    }, indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Canvas course cache helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_diff = sub.add_parser("diff", help="Compare new data vs cache")
    p_diff.add_argument("course_id")
    p_diff.add_argument("section", choices=["syllabus", "modules", "assignments", "announcements"])
    p_diff.add_argument("--input", required=True)
    p_diff.add_argument("--refresh", action="store_true")
    p_diff.set_defaults(func=cmd_diff)

    p_save = sub.add_parser("save", help="Save new data as cache")
    p_save.add_argument("course_id")
    p_save.add_argument("section", choices=["syllabus", "modules", "assignments", "announcements"])
    p_save.add_argument("--input", required=True)
    p_save.set_defaults(func=cmd_save)

    p_inspect = sub.add_parser("inspect", help="Show cache summary")
    p_inspect.add_argument("course_id")
    p_inspect.set_defaults(func=cmd_inspect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

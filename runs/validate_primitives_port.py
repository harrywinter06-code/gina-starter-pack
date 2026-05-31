#!/usr/bin/env python3
"""Faithful Python port of askgina/awesome-gina scripts/validate_primitives.rb.

Ruby is unavailable in this sandbox, so this reproduces the repo's CI gate
(.github/workflows/validate-primitives.yml) exactly. Self-tested: run against the
pristine clone it must reproduce "validation passed"; that confirms fidelity
before trusting its verdict on the merged (pack-added) tree.
"""
import re
import sys
import glob
import os
import yaml

VALID_TYPES = {"recipe", "strategy", "workflow"}
VALID_VISIBILITY = {"public", "unlisted", "private"}
SEMVER = re.compile(r"\A\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
SLUG = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TRIGGER_PATTERNS = [
    re.compile(r"-\s*Trigger:\s*Recurring schedule\s*`([^`]+)`\s*\(([^)]+)\)", re.I),
    re.compile(r"-\s*Trigger:\s*recurring schedule\s*`([^`]+)`\s*in\s*`([^`]+)`", re.I),
    re.compile(r"-\s*Trigger:\s*Recurring schedule\s*`([^`]+)`\s*in\s*`([^`]+)`", re.I),
    re.compile(r"-\s*Schedule(?: the workflow)?(?: for| at)?\s*`([^`]+)`\s*in\s*`([^`]+)`", re.I),
    re.compile(r"-\s*Live schedule target:\s*`([^`]+)`\s*\(([^)]+)\)", re.I),
]
CRON_FIELD = re.compile(r"\A\S+(?:\s+\S+){4,}\Z")
TZ = re.compile(r"\A(?:UTC|GMT|[A-Za-z_]+(?:/[A-Za-z0-9_+.-]+)+)\Z", re.I)


def primitive_files(root):
    files = (
        glob.glob(os.path.join(root, "recipes", "**", "*.md"), recursive=True)
        + glob.glob(os.path.join(root, "strategies", "**", "*.md"), recursive=True)
        + glob.glob(os.path.join(root, "workflows", "*", "README.md"))
    )
    return sorted(files)


def parse_frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    if not lines or lines[0].strip() != "---":
        return None, f"{path}: missing frontmatter start delimiter"
    closing = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = i
            break
    if closing is None:
        return None, f"{path}: missing frontmatter end delimiter"
    yaml_text = "".join(lines[1:closing])
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return None, f"{path}: invalid YAML frontmatter ({e})"
    if not isinstance(data, dict):
        return None, f"{path}: frontmatter is not a YAML object"
    return data, None


def array_of_strings(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def create_page_workflow_schedule(path):
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    for pat in TRIGGER_PATTERNS:
        m = pat.search(content)
        if not m:
            continue
        cron = (m.group(1) or "").strip()
        tz = (m.group(2) or "").strip()
        if CRON_FIELD.match(cron) and TZ.match(tz):
            return True
    return False


def main(root):
    errors = []
    entries = []
    for path in primitive_files(root):
        data, err = parse_frontmatter(path)
        if err:
            errors.append(err)
            continue
        rid = data.get("id")
        rtype = data.get("type")
        if not str(rid or "").strip():
            errors.append(f"{path}: missing required field `id`")
        elif not SLUG.match(rid):
            errors.append(f"{path}: `id` must be lowercase kebab-case")
        if rtype not in VALID_TYPES:
            errors.append(f"{path}: `type` must be one of {', '.join(sorted(VALID_TYPES))}")
        slug = data.get("slug")
        if not str(slug or "").strip():
            errors.append(f"{path}: missing required field `slug`")
        elif not SLUG.match(slug):
            errors.append(f"{path}: `slug` must be lowercase kebab-case")
        version = data.get("version")
        if not str(version or "").strip():
            errors.append(f"{path}: missing required field `version`")
        elif not SEMVER.match(version):
            errors.append(f"{path}: `version` must be semver")
        vis = data.get("visibility")
        if not str(vis or "").strip():
            errors.append(f"{path}: missing required field `visibility`")
        elif vis not in VALID_VISIBILITY:
            errors.append(f"{path}: `visibility` must be one of {', '.join(sorted(VALID_VISIBILITY))}")
        pub = data.get("publicUrl")
        if vis == "public" and (pub is None or not str(pub).strip()):
            errors.append(f"{path}: `publicUrl` is required when `visibility` is public")
        category = str(data.get("category") or "")
        if rtype == "recipe" and not category.startswith("recipes/"):
            errors.append(f"{path}: `category` must start with `recipes/`")
        elif rtype == "strategy" and not category.startswith("strategies/"):
            errors.append(f"{path}: `category` must start with `strategies/`")
        elif rtype == "workflow" and not category.startswith("workflows/"):
            errors.append(f"{path}: `category` must start with `workflows/`")
        relationships = data.get("relationships")
        if relationships is not None and not isinstance(relationships, dict):
            errors.append(f"{path}: `relationships` must be a mapping object")
        if rtype == "strategy":
            recipe_ids = (relationships or {}).get("recipeIds")
            if not array_of_strings(recipe_ids) or not recipe_ids:
                errors.append(f"{path}: strategy must declare non-empty `relationships.recipeIds`")
            wf_ids = (relationships or {}).get("workflowIds")
            if wf_ids is not None and not array_of_strings(wf_ids):
                errors.append(f"{path}: `relationships.workflowIds` must be an array of string ids")
        else:
            s_ids = (relationships or {}).get("strategyIds")
            if s_ids is not None and not array_of_strings(s_ids):
                errors.append(f"{path}: `relationships.strategyIds` must be an array of string ids")
        entries.append({"path": path, "data": data, "id": rid, "type": rtype})

    id_index = {}
    for e in entries:
        if not str(e["id"] or "").strip():
            continue
        if e["id"] in id_index:
            errors.append(f"duplicate id `{e['id']}` in {e['path']} and {id_index[e['id']]['path']}")
        else:
            id_index[e["id"]] = e

    for e in entries:
        rel = e["data"].get("relationships") or {}
        if e["type"] == "strategy":
            for rid in rel.get("recipeIds", []) or []:
                t = id_index.get(rid)
                if t is None:
                    errors.append(f"{e['path']}: strategy references missing recipe id `{rid}`")
                elif t["type"] != "recipe":
                    errors.append(f"{e['path']}: `{rid}` exists but is not a recipe")
            for wid in rel.get("workflowIds", []) or []:
                t = id_index.get(wid)
                if t is None:
                    errors.append(f"{e['path']}: strategy references missing workflow id `{wid}`")
                elif t["type"] != "workflow":
                    errors.append(f"{e['path']}: `{wid}` exists but is not a workflow")
                elif not create_page_workflow_schedule(t["path"]):
                    errors.append(
                        f"{t['path']}: strategy-linked workflow must declare a /create-compatible "
                        f"recurring schedule, e.g. - Trigger: recurring schedule `7 */2 * * *` in `Europe/London`."
                    )
        else:
            for sid in rel.get("strategyIds", []) or []:
                t = id_index.get(sid)
                if t is None:
                    errors.append(f"{e['path']}: references missing strategy id `{sid}`")
                elif t["type"] != "strategy":
                    errors.append(f"{e['path']}: `{sid}` exists but is not a strategy")

    if not errors:
        print(f"primitive metadata validation passed for {len(entries)} entries")
        return 0
    print("primitive metadata validation FAILED:")
    for err in errors:
        print(f"- {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))

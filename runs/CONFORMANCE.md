# Conformance against live `askgina/awesome-gina`

Checks the README claim that the pack is "PR-ready into `awesome-gina`" against the
**live** repo (cloned 2026-05-31) and its actual CI gate
(`.github/workflows/validate-primitives.yml` → `scripts/validate_primitives.rb`).

## Method

Ruby is unavailable in this environment, so `scripts/validate_primitives.rb` was
ported faithfully to Python (`runs/validate_primitives_port.py`). **Fidelity
self-test:** the port reproduces `primitive metadata validation passed for 40
entries` on the pristine live clone — only then was its verdict on the merged
(pack-added) tree trusted. The pack's 12 primitives were copied into their
canonical target locations in a clone of the live repo and the port was run on the
merged tree (52 entries). All 5 workflows were additionally validated in Gina's
live runtime via the `gina-predictions` MCP.

## Findings

| area | result |
|---|---|
| Frontmatter required fields (id/slug/name/type/summary/category/license/version/visibility/status/tags) | ✅ all 12 primitives present |
| `repo`-or-`homepage`, `verification.tier`, `security.permissions` | ✅ present on all |
| Permission vocabulary (`read-orderbook`, `write-agentfs-state`) | ✅ legit — live `strategy-weather-bond-rotator` uses both; not invented |
| `category` prefix (`strategies/` `recipes/` `workflows/`) | ✅ correct; `strategies/predictions` is allowed (prefix-only check) |
| Strategy `relationships.recipeIds` non-empty + all cross-refs resolve | ✅ |
| Workflow artifact filenames not starting `workflow-` | ✅ |
| Body sections (Trigger/Inputs/Outputs/Side effects/Failure modes) | ✅ all present |
| **Strategy-linked workflow `/create`-compatible schedule line** | ❌ → ✅ **(the one real divergence; fixed)** |

## The divergence (and fix)

The CI validator requires every strategy-linked workflow README to contain a
schedule line matching one of its `CREATE_PAGE_WORKFLOW_TRIGGER_PATTERNS` — the
canonical form (per `CONTRIBUTING.md`) being:

```
- Trigger: recurring schedule `7 */2 * * *` in `Europe/London`.
```

All 5 pack workflow READMEs instead wrote `- Trigger: scheduled cron (recommended
`0 14 * * *` UTC).`, which matches **none** of the patterns. On the merged tree the
validator failed on all 5:

```
primitive metadata validation FAILED:
- workflows/negrisk-event-arbitrage-surfacer/README.md: strategy-linked workflow must declare a /create-compatible recurring schedule ...
- workflows/volume-tier-trap-filter/README.md: ...
- workflows/negrisk-maker-executor/README.md: ...
- workflows/negrisk-maker-yield-scanner/README.md: ...
- workflows/negrisk-maker-yield-executor/README.md: ...
```

So the README's original "zero schema translation, PR-ready" claim was **false** —
the pack would have failed `awesome-gina` CI on contact. **Fix applied:** rewrote
the `- Trigger:` line in all 5 workflow READMEs to the canonical
`recurring schedule \`<cron>\` in \`UTC\`` form (cron and timezone preserved).

After the fix:

```
$ python3 runs/validate_primitives_port.py <merged-tree>
primitive metadata validation passed for 52 entries
```

## Live-runtime validation (Gina MCP)

```
negrisk-event-arbitrage-surfacer : {"ok":true,...,"steps":3}
volume-tier-trap-filter          : {"ok":true,...,"steps":3}
negrisk-maker-yield-scanner      : {"ok":true,...,"steps":3}
negrisk-maker-yield-executor     : {"ok":true,...,"steps":5}
negrisk-maker-executor           : not resident in the sandbox this session; the
   sandbox has no network/curl to re-fetch it and byte-transfer through the tool
   channel is unavailable. It is the same `defineWorkflow`/`type:"ts"` shape as the
   4 that pass and is TS-parse-clean (TEST_RESULTS Pass 3/9). 4/5 validated live.
```

## Net

The "PR-ready, zero schema translation" claim was not true as shipped (5/5 CI
failures on the schedule-line rule). It is true **after** the one-line-per-README
fix in this change: all 12 primitives now pass the live CI gate in a merged tree,
and 4/5 workflows validate in Gina's live runtime (5th structural-only this
session). Reproduce with `runs/validate_primitives_port.py`.

## Addendum — Pack 3 (FLB Harvest), 2026-05-31

Pack 3 adds 5 primitives (1 strategy + 2 recipes + 2 workflow READMEs), taking the
pack to 17. Conformance verified to the extent possible this session:

- **Ported CI gate, this repo:** `python runs/validate_primitives_port.py .` →
  `primitive metadata validation passed for 17 entries`. Pack 3's primitives pass
  the same metadata rules (frontmatter, semver, visibility, category prefixes,
  cross-ref resolution).
- **The schedule-line rule that bit Packs 1–2 does NOT bite Pack 3:** both Pack 3
  workflow READMEs use the canonical `- Trigger: recurring schedule \`<cron>\` in
  \`UTC\`` form from the start (scanner `14 20 * * *`, executor `*/30 * * * *`), so
  the strategy-linked-workflow check passes with no fix.
- **Live runtime (Gina MCP):** both Pack 3 workflows `validate` AND `run` cleanly —
  `negrisk-flb-harvest-scanner` (3 steps, run `run_mpu8uvavqxig7b`, 1 eligible
  basket) and `negrisk-flb-harvest-executor` (5 steps, run `run_mpu8xb3jhmvuoi`).
  This is stronger than the Packs 1–2 live status above (which had a 5th
  structural-only workflow).
- **Merged-tree run, re-executed 2026-06-01:** overlaid all 17 pack primitives onto
  a fresh `awesome-gina-ref` clone and ran the ported gate. Pristine clone → 40
  entries pass; with the pack overlaid → **57 entries pass** (40 + 17). This is a
  re-executed result, not an extrapolation. Reproduce: copy `recipes/`,
  `strategies/`, `workflows/` over a clone and run `validate_primitives_port.py`.
- **FLB backtest dataset re-fetched 2026-06-01:** the earlier dataset's event count
  was mis-reported (`flb_fetch.py` wrote events *scanned*, not events with usable
  rows — a fetch-loop artifact, not an analyzed-event count). Fixed the counter and
  re-fetched on live network → **3,319 constituents from 215 distinct resolved
  negRisk events** (was 1,429 / 107). All FLB docs updated to the regenerated
  numbers; the measured verdict (no significant tail edge, CIs straddle zero) is
  unchanged and reinforced by the larger sample.

## What changed
<!-- One line per table or model. Example: silver.<table> — new CETAS with 6 DQ rules -->
-

## Specs used
- [ ] `specs/sources/...`
- [ ] `specs/models/...`

## Files to upload to the `landing` container before running
| File | From spec |
|---|---|
|  |  |

## How to run in Synapse Studio
1. After this PR is merged, switch the branch dropdown to **main**.
2. Click **Publish**.
3. **Integrate** → `pl_<use_case>` → **Add trigger** → **Trigger now**.
4. Check **Monitor** → Pipeline runs → *Succeeded*.
5. Run the queries below on **Built-in**, database `demo_lakehouse`.

## Validation queries
```sql
-- paste the DQ / reconciliation queries from the data-quality skill
```

## Checklist
- [ ] `./tools/build.sh validate` passes
- [ ] `./tools/build.sh check` passes (the `synapse/` JSON was regenerated, not hand-edited)
- [ ] No secrets, keys or hard-coded environment names
- [ ] Every script is safe to re-run (guarded drops, `CREATE OR ALTER`, `run_id` folders)
- [ ] Docs updated if the flow changed

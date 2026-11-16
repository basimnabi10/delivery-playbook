# Delivery Hub update prompt

A ready-made set of instructions for the weekly update of one artefact. Fill in the placeholders in angle brackets and paste it into a session at your weekly slot. A scheduled run may use the same text, because it only drafts (see [Step 7](../onboarding/07-weekly-rhythm.md)).

| Placeholder | What to put |
| --- | --- |
| `<artefact>` | The Delivery Hub, or the name of another client-shared artefact from `shared_artefacts` in `project.yml` |
| `<week ending>` | The last day of the week, in the week rule's terms |

## The prompt

```
Update <artefact> for the week ending <week ending>. Draft only: do not
publish, merge, send or overwrite anything.

1. Read state.yml, registry.yml, project.yml, team.yml and project/internal/hub-operations/decisions.md.
   State the playbook version.
2. Carry over any corrections still pending from the last review. Check
   each one against the registry and the repos before you use it.
3. Read each source in the registry by its recorded method, titles and IDs
   first. Record the read depth in sources_checked. An unreadable source is
   a gap, never evidence that nothing happened. Refresh every copy listed in
   a manifest (new meetings with transcript and summary, Drive documents by
   declared id, bug-sheet tabs). Rewrite a file only when the source's hash
   changed, and record a failed read as a gap.
4. Counts come from scripts/count_prs.py, using rules.counting (merged pull
   requests per week for every repo in code.repos, the merged-PR definition
   and the week rule). Do not count yourself. If the script fails, say so
   and leave the counts unchanged.
5. Write proposals into _inbox/ with evidence, confidence and visibility, and
   label each change's environment: production, staging or internal-testing.
6. Switches: include the Hours page only if pages.hours.enabled is true, and
   the Sprints page only if sprints.used is true.
7. Build the preview with scripts/build.py (into out/preview/), then run
   scripts/check_render.py. Scan the page for every string in
   rules.never_on_client_pages and for any person marked
   introduced_to_client: false. Fix the data, never the HTML, and report each
   match.
8. Verify each client-visible claim against the registry and the repos, and
   each number against the script output. Run scripts/validate.py. If it
   fails, stop and report the errors: never chain it with ';'.
9. Write a review summary: what changed per release, new limitations, what
   was resolved, what could not be verified, and which environment the data
   came from.
10. Put the changes on a branch and open a pull request with
    scripts/sync.py. Never write to main. Then stop and wait. Accepting
    proposals, publishing and merging need the person's approval in a
    session.
```

Back to [Step 7](../onboarding/07-weekly-rhythm.md).

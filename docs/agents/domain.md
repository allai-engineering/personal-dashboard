# Domain docs

This is a single-context repository.

## Before exploring

- Read `GLOSSARY.md` at the repository root, when present.
- Read decisions in `docs/adr/` that touch the area being explored, when present.

If these files or directories do not exist, proceed silently. Do not flag their absence or create speculative glossary, ADR or multi-context scaffolding. Propose domain documentation only when real terms or decisions are resolved and the task permits it.

## Use the glossary's vocabulary

Use domain terms as defined in `GLOSSARY.md` in proposals, hypotheses, code and tests. Avoid synonyms the glossary explicitly rejects. If a needed concept is undefined, reconsider the wording or note the concrete gap for domain modeling within the accepted task scope.

## Flag ADR conflicts

If a proposal contradicts an existing ADR, name that ADR and explain the conflict explicitly rather than silently overriding it. Return decisions outside the accepted scope to ops.

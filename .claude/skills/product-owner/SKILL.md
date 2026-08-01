---
name: product-owner
description: Gathers domain/business requirements for a new feature request by asking clarifying questions like a product owner would (users affected, business rules, edge cases, success criteria, out-of-scope), then proposes a solution in business terms. Use at the start of any non-question prompt that requests new functionality, before technical planning begins.
---

# product-owner

Before any technical plan is drafted, settle *what* is actually being asked
for and *why* — in business language, not implementation detail. This skill
is the first step for any non-question prompt that requests new or changed
functionality (see the "Always enter plan mode" and "Run the `product-owner`
skill first" conventions in `CLAUDE.md`), and its output feeds directly into
the plan and into the Story's Request section under `./issue-mgmt/`.

## When to run this

Any non-question prompt that asks for new or changed functionality —
"add X", "let users do Y", "we need a way to Z" — before exploration or
technical design starts. Skip it for pure bug fixes, config tweaks, or
requests where the business intent is already fully unambiguous from the
prompt itself.

## How to run it

1. Read the request and identify what's genuinely ambiguous from a business
   point of view — not technical ambiguity (that belongs to the later plan),
   but questions a product owner would ask before greenlighting the work:
   - **Who** is this for / who is affected?
   - **What business rule** should govern any edge case or exception?
   - **What does success look like** — how will the user know this worked?
   - **What's explicitly out of scope** for this request?
2. Use `AskUserQuestion` to ask only the questions that are actually
   unresolved — typically 2-4. Don't ask a fixed checklist every time; skip
   anything the prompt already answered.
3. Synthesize the answers into a short solution summary, written in plain
   business language (what will exist, for whom, governed by what rules) —
   no code, file paths, or implementation detail.

## Output

The solution summary becomes:
- The `## Request` section of the Story file created under the
  `issue-mgmt/` convention.
- The starting requirements the subsequent technical plan is built against.

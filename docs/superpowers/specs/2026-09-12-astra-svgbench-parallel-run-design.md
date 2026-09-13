# Astra SVGBench Parallel Run Design

## Objective

Generate the existing seven-prompt SVG series with `gpt-6-astra` in Codex.
Use reasoning effort `medium` for comparison with the `gpt-5.6-sol` arm.

## Scope

The run uses SVGBench questions 0, 4, 5, 6, 7, 12, and 13.
Each question produces four files in this order: `v1`, `v2`, `v3`, and `animated`.
The run produces 28 SVG files.

Store the files under:

```text
bench/harness-matrix/logs/codex/gpt-6-astra/
```

Use the same filename slugs as the `gpt-5.6-sol` arm.

## Agent model

Use seven independent agents.
Assign one SVGBench question to each agent.
Run at most three child agents concurrently because the root agent occupies one of four available slots.
Use three waves with sizes 3, 3, and 1.

Every child agent uses:

- Model: `gpt-6-astra`
- Reasoning effort: `medium`
- Isolated context: `fork_turns: none`
- One exact output directory
- One exact prompt from `questions.json`

Agents must not inspect existing SVG artifacts, SVG reports, renders, scores, or verdicts.
Agents may read `AGENTS.md` and the assigned question entry.

## Artifact contract

Each agent writes four self-contained SVG files.
Each file must parse as XML and must not use external resources.
The animated file must contain SVG animation or CSS animation.

Each agent creates `v1` first.
The agent then creates `v2` and `v3` as intentional revisions.
The agent creates `animated` from its best static composition.

Agents edit only their four assigned files.
The root agent owns all shared metadata and reports.

## Coordination and failure handling

The root agent dispatches the next agent when a slot becomes available.
The root agent records the result from every child agent.
One failed prompt does not cancel completed prompts.

The root agent permits one repair attempt for an invalid or missing artifact.
The repair agent receives only the failed prompt and validation error.
The root agent stops new repair work when estimated use reaches 350 Codex credits.
The Codex interface does not expose exact per-run credits, so this limit is operational rather than enforceable.

## Validation

The root agent verifies these conditions before updating shared results:

1. The output directory contains exactly 28 expected SVG files.
2. Every file parses as XML.
3. Every root element is `svg`.
4. No file references an external HTTP resource.
5. Every animated take contains animation markup or CSS keyframes.
6. Git reports no child changes outside the assigned output directory.

## Integration

After validation, update the pair record at:

```text
bench/harness-matrix/results/codex/gpt-6-astra.md
```

Add the pair to `results/svgbench/participants.json`.
Regenerate `results/svgbench/manifest.json` with the existing evaluator.
Do not create judge verdicts during generation.
Mark all Astra artifacts as unscored until a separate judge run exists.

Regenerate the artifact report and SVGBench gallery with existing repository tools.
Preserve unrelated working-tree changes.

## Acceptance criteria

- The repository contains 28 Astra SVG artifacts with the expected names.
- All 28 artifacts pass structural validation.
- The pair record states model, effort, procedure, artifact count, and scoring status.
- Participant and manifest metadata identify `codex/gpt-6-astra`.
- Reports show Astra artifacts as unscored.
- Existing repository tests pass.

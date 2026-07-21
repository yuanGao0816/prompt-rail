# Optimization techniques — the move set

When you DIAGNOSE a failure, you pick a fix from here. Each technique names the failure it targets, the edit, and the side effect to watch for in the diff. Pick **one** per iteration.

## 1. Instruction placement & cache-friendliness
**Targets:** drifting compliance, ignored rules, slow/expensive runs.
Put stable instructions (role, rules, format) at the **top**; put runtime variables (`{{chat_history}}`, `{{content}}`) at the **bottom**. Models weight early and late tokens most, and stable-prefix layout lets prompt caches reuse the head across calls. A common win is re-laying-out an existing prompt so instructions come first and variables last — same content, better cache reuse, often better compliance.
**Side effect to watch:** moving a rule next to the variable it governs sometimes helps more than keeping all rules at top. If a format rule keeps getting dropped, try co-locating it with the input.

## 2. Positive framing over negative
**Targets:** the model doing the exact thing you told it not to do.
"Write every action with the user as the subject" beats "don't drop the user as the subject." Negations make the model represent the forbidden behavior, and a stack of *don'ts* reads as a checklist it half-follows. Convert prohibitions into the positive instruction that makes the prohibition unnecessary.
**Side effect:** some constraints are genuinely negative (forbidden words). Keep those as one crisp rule, not five.

## 3. Few-shot exemplars (especially contrastive)
**Targets:** format breakage, tone misses, "I described the quality but it still won't do it."
One good example outperforms three paragraphs of description. For subtle qualities use a **contrastive pair**: a �*bad* example labeled with *why*, then the ✓ *good* rewrite. For anti-repetition, show two consecutive turns that correctly vary opener/action/beat.
**Side effect:** exemplars are sticky — the model copies their surface (names, specific phrasings). Use placeholder-y content, or it'll parrot your example's specifics into real outputs. Watch the diff for leaked exemplar tokens.

## 4. Decomposition / step ordering
**Targets:** multi-requirement outputs where one requirement always loses.
Give the model an explicit order of operations: "First identify the target language. Then write the reply. Then verify it's ≤45 words and trim if not." Naming a self-check step late in the prompt catches length/format drift the model would otherwise commit.
**Side effect:** too many steps bloat the prompt and can leak as visible "Step 1..." scaffolding into output. Keep steps internal and few.

## 5. Constraint anchoring (budgets near the exit)
**Targets:** length drift, count drift (too many/few replies or sentences).
Put the hard budget as one of the **last** things the model reads before generating: "Output: 1–3 sentences, ≤45 words, plain text." Late placement = freshest constraint at generation time. Pair with a `max_words`/`line_count_max` assert so you measure it. Length and reply-count budgets are the classic case for this move.
**Side effect:** an aggressive cap can truncate genuinely-needed content and tank a coherence judge score. Watch the judge dimension when you tighten a budget.

## 6. Anti-repetition rules
**Targets:** reusing the previous turn's opener, action, emotion, or sentence shape.
**One** rule that names the *axes* of variation, anchored to recent history: "Vary from the previous assistant turn on all of: opening words, the physical action, the emotional beat, and sentence structure." Feed the prior turn in via `vars` so the rule has something to diff against.
**Side effect:** the classic trap — piling on *avoid repeating* sentences crowds out persona instructions and flattens voice (this is the `v2`-reverted example in SKILL.md). One sharp rule + one contrastive exemplar beats five nagging sentences. Always keep a persona regression-guard case.

## 7. Persona / subject anchoring
**Targets:** identity confusion — the model acts or speaks *for the user*, or swaps who does what.
State the contract once, precisely: who is the first-person speaker, who actions attribute to, how the other party is referred to (nickname → name → pronoun). Persona prompts often need several iterations on this single axis. The winning forms are *short explicit contracts*, not long explanations.
**Side effect:** a rigid reference rule can make narration stilted. Check a fluency/naturalness judge line when you tighten persona rules.

## 8. Structural rewrite (the escape hatch)
**Targets:** two+ failed local patches; the frame itself is wrong.
Stop patching lines. Re-draft the prompt's skeleton: reorder major sections, merge redundant rules, cut instructions that aren't earning their tokens, re-establish the role. Treat the rewrite as a single hypothesis ("the structure, not any one rule, was the problem") and measure it against the same suite like any other iteration. This is a bigger swing — only after local edits stall.

## 9. Subtraction (delete, don't add)
**Targets:** low judge scores on a *long* prompt; flattened voice; rules that contradict or crowd each other.
Techniques 1–7 all *add* tokens, and that bias is how prompts bloat into screen-filling rule-piles that score worse than a tight version. Deletion is a first-class hypothesis: cut the lowest-value rule, a redundant restatement, or a whole section, and measure. Long prompts that underperform are often *over*-specified — competing instructions the model can't satisfy at once. "Remove the three overlapping length rules, keep one" is a legitimate, testable edit. Shorter is the default to return toward, not just a cleanup afterthought.
**Side effect:** you can cut a rule that was silently load-bearing — a previously-passing case regresses. That's exactly what the diff catches; revert and cut something else. The regression *tells you* which rule was actually earning its tokens.

## 10. Built-in feedback loop over more instructions
**Targets:** format/length/count drift you keep trying to fix with yet another rule.
Instead of adding a fourth instruction, give the model a way to *check itself*: a final self-verify step ("before responding, confirm output is valid JSON and ≤45 words; if not, fix it"), or a required format that makes violations self-evident. A loop the model can run beats a rule it has to remember — this is the same principle the whole skill runs on, applied inside the prompt. Prefer it when three+ rules already target the same drift and it persists.
**Side effect:** a verbose self-check can leak as visible "checking..." scaffolding into output. Keep the instruction to verify *silently*; add a `not_contains`/`not_regex` assert to catch leaked scaffolding.

---

## Choosing which to try
1. Read the lowest-scoring case's **actual output** (not the prompt).
2. Name the failure in one phrase.
3. Map it to the row above whose **Targets** matches.
4. State it as cause → edit → expected per-case effect in `LOG.md`.
5. Make only that edit; measure; check the **side effect** column in the diff.

When the prompt is already long and the failing dimension is judge-subjective, reach for **#9 (subtraction)** before adding anything — techniques 1–7 bias toward growth, and that bias is how a prompt rots. If three rules already target the same drift, reach for **#10 (feedback loop)** instead of a fourth rule.

The discipline isn't knowing these techniques — the model already half-knows them. It's applying exactly one at a time and letting the suite, not taste, decide whether it stays.

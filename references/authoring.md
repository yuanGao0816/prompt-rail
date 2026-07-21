# Authoring — writing v0 from scratch

This is the **AUTHORING** half of the skill: how to draft the first version (`v0.md`)
when there's no existing prompt. It is not a separate workflow — once `v0` exists you
enter the same FRAME → BASELINE → ITERATE loop. A draft you don't then measure is just
a vibe; authoring's job is to produce the *smallest credible v0* the loop can sharpen.

The cardinal mistake is over-writing the first draft: a screen-filling prompt that
specifies every detail, then "optimizing" it by adding more. Good authoring starts
small and leans on feedback, not on exhaustive instruction.

## The four authoring principles

### 1. Short beats long — start at the minimum, earn every line
A two-sentence prompt usually beats a screen-filling one. Begin with the smallest
prompt that could plausibly work, measure it, and add only what a *failed case*
justifies. If your draft is more than ~5 lines of instruction, suspect that half of it
either (a) restates what the model already knows, or (b) belongs in a persistent-context
file (a style guide, a schema doc) rather than inline in every call.

Why: long prompts dilute the instructions that matter, cost tokens on every invocation,
and create rules that contradict each other as they accumulate. The loop *adds* precision
where the suite proves it's needed — so the draft doesn't have to pre-empt every failure.
This flips the usual instinct: don't write defensively, write minimally and let
measured failures pull in each addition.

### 2. A feedback loop beats detailed instructions
If the model can *verify its own output* — re-read it against a checklist, validate JSON,
count words, compare to the prior turn — give it that loop instead of spelling out every
step. "Write the reply, then check it's ≤45 words and trim if not" outperforms three
sentences trying to pre-control length. For prompts driving an agent that can run things,
"run the tests and iterate until they pass" beats a step-by-step procedure.

Why: instructions are open-loop — the model either follows them or doesn't, with no
correction. A verification step closes the loop so the model catches its own misses.
This is the same principle the *skill itself* runs on (eval suite = your feedback loop);
here you're embedding a smaller version of it inside the prompt.

### 3. Point at a starting place, don't re-describe it
When the prompt operates on something the model can inspect — a code file, an existing
implementation, a reference example — point to it ("follow the structure of the existing
v3 reply", "match how X is done") instead of re-describing it in prose. Re-description
drifts from the real thing, goes stale, and bloats the prompt.

Why: a pointer stays accurate because it *is* the source; prose about the source is a
lossy copy that rots. For production templates this maps to **few-shot exemplars** — show
one real (placeholder-ized) example rather than describe the format in a paragraph.

### 4. "Make a plan first" — two layers, don't confuse them
There are **two different "plans"** in prompt work, and they live at different layers:

**(a) The authoring plan — applies to *every* prompt, templates included.** Before you write
*any* v0, you align on requirements, align on the rules the output must obey, and turn both
into the **eval suite** — which *is* the plan, made concrete and approvable. This is the
FRAME → RULES → PLAN sequence in `SKILL.md`. A single-shot reply template needs
this just as much as a coding agent does: "what counts as a good reply, and which rules
must it never break" is exactly the alignment you do before drafting. The eval suite is
where that alignment becomes testable. Never skip it on the grounds that "it's just a
template."

**(b) The in-prompt plan step — applies *only* to agentic / multi-step task prompts.**
This is a *line inside the prompt itself*: *"Before you act, make a plan and run it by me
for approval."* It converts a one-shot generation into a checkpoint — cheap to redirect
before work happens, expensive after. It belongs in prompts that *drive a model to do
non-trivial work* (write code, refactor, execute a multi-step task). It does **not** belong
in a single-shot production template — a chat-reply generator shouldn't emit a "here's my
plan" preamble; that would leak planning scaffolding into the reply. So: for an agent
instruction, put this line in; for a reply template, leave it out.

The mistake to avoid is collapsing these — "templates don't need planning" is **false**
for layer (a) and **true** only for layer (b). Every prompt gets the authoring plan; only
agentic prompts get the in-prompt plan step.

## Drafting procedure

1. **Write the role + task in 1–2 sentences.** Who the model is, what it produces. No
   more yet.
2. **Add only the hard constraints you already know** (format, length, forbidden things)
   — as positive instructions, placed where the model reads them last before generating.
   See `optimization-techniques.md` #1 and #5.
3. **Add one feedback/self-check step** if the output has a verifiable property.
4. **Add at most one exemplar** if the format or tone is subtle — placeholder-ized so the
   model can't parrot its specifics.
5. **Stop.** Save as `prompts/v0.md`. Everything else is a *hypothesis for the loop*, not
   a thing to pre-write. Go to BASELINE.

If you catch yourself adding a rule "just in case," don't — write the eval case that would
catch its absence instead. That case either fires (then the rule is earned) or it doesn't
(then the rule was never needed). This is the discipline that keeps v0 short.

## Authoring vs iteration — same loop, two entry points

```
AUTHORING:  FRAME → draft minimal v0 ─┐
                                      ├→ BASELINE → [ DIAGNOSE → … → KEEP/REVERT ]* → CONVERGE
OPTIMIZING: FRAME → existing v0 ───────┘
```

The only difference is where `v0` comes from. Authoring's principles (short, feedback,
pointer, plan-first) govern the *draft*; the iteration move-set
(`optimization-techniques.md`) governs *each subsequent edit*. They're the two halves of
one skill, not two skills — because an unmeasured draft is exactly the failure mode this
skill exists to replace.

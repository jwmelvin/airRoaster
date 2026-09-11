# state-history — index of the investigation records

> **This file is an index, not a record.** The roast-by-roast reasoning behind
> the Artisan cascade PID — measurements, refits, operator questions and the
> answers they produced, including the ones later overturned — lives in three
> effort-scoped files. Nothing else belongs here.
>
> Companion to [state-current.md](state-current.md) (what is active now),
> [state-plan.md](state-plan.md) (what is planned, and the specifications in
> force) and [state-archive.md](state-archive.md) (completed firmware work and
> the F-numbered review findings).

**Each file is chronological, oldest first, and later sections correct earlier
ones.** A finding in a history file is current only if nothing below it says
otherwise; the settled conclusions live in state-plan.md, not here. Sections
still *in force* — the `.aset` specifications, the step-9 design, the ruled-out
list — are in state-plan.md and referenced from the history as
`state-plan.md § …`.

| file | effort | span | what it closed |
|---|---|---|---|
| [state-history-cascade.md](state-history-cascade.md) | commissioning the cascade, and identifying the plant | roasts **40-49**, 2026-09-02 → 09-06 | the loop tracks to +0.40 degC; `Kp` 3.0 / `Ki` 0.07 / the lookahead switch settled; `feedforward()` measured; the controller stopped being the limiting error |
| [state-history-charge.md](state-history-charge.md) | the charge state, the dip model, and authoring the background | the charge-thermal test and roasts **50-56**, 2026-09-06 → 09-07 | `k = 0.1056` over a 37 degC span; `h_fus` under ~1 J/g; the dip model refitted; the SV floor at 100; a background passing all four checks |
| [state-history-residual.md](state-history-residual.md) | the −2.9 degC residual, and measuring the machine on the bench | phase 0, roast **57**, two archive re-readings, Phase A (roasts **58-59**), 2026-09-08 → 09-10 | the FC temperature is a property of the lot; the ramp was never fitted; the preheat lever is dead; the fan step sized at `f = 0.18`. **Phase B is open** |

**Where to look for a given roast.** 40-49 → cascade. 50-56 → charge. 57-59 →
residual. Roasts 20 and 37/38 are pre-cascade runs re-read in 2026-09-08/09 and
are in *residual*, not the archive.

## How this got split

It was one file, `state-history.md`, split out of state-plan.md on 2026-09-06
when the plan had grown to 3,900 lines of which the greater part was superseded
narrative. By 2026-09-11 the history itself was 5,756 lines spanning three
distinct efforts, so it was split again along the two natural seams — the point
where the controller stopped being the limiting error and the work moved to the
reference curve, and the point where roast 56 exposed the 170 s residual. No
content was changed in the split.

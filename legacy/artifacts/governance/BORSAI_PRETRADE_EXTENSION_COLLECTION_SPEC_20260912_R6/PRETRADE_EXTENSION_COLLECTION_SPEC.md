# BORSAI — PRETRADE EXTENSION COLLECTION SPEC v2 (REVISION R6)

Task id: `BORSAI_COLLECTION_SPEC_R6_20260912_T21`
Scientific weight: `FROZEN_GATE`
Spec version string (written into every output row): `PRETRADE_EXT_COLLECTION_SPEC_V2`
Written: 2026-09-12, Europe/Istanbul.
Supersedes, for every validation run after this revision's tag is created:
`artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R5/`.
Predecessor chain: R1 (`PRETRADE_EXT_COLLECTION_SPEC_V1`, tag
`frozen/collection-spec-v1`) → R2 (tag `frozen/collection-spec-v2`) → R3 (tag
`frozen/collection-spec-r3`) → R4 (tag `frozen/collection-spec-r4`) → R5 (tag
`frozen/collection-spec-r5`, created 2026-09-12 10:57:54 +03) → this revision.

**The spec version string does not change.** R6 writes
`PRETRADE_EXT_COLLECTION_SPEC_V2` into every `B01`…`B16` output row, exactly as
R2, R3, R4 and R5 do. R6 adds no column, changes no column order, extends no
collector-facing enum and changes no collector-facing schema, so there is nothing
for a version string to distinguish: a batch collected under R2, R3, R4, R5 or R6
is byte-comparable by construction. The revision identifier `R6` names the
**document**; `V2` names the **schema**, and the schema is untouched. Introducing
a `V3` string would break §8 check 1's column-count resolution (24 for V1 rows, 26
for V2 rows) for no gain — R4's argument, unchanged, and R5's, unchanged.

**R6 nevertheless publishes its own `PRETRADE_EXTENSION_COLLECTION_SPEC.json`.**
That is not in tension with the paragraph above, and the reason is a provision of
this revision rather than a note: §R6.2. In one sentence, R6 adds a rule code to a
list the machine-readable file enumerates, and the standing ledger ruling makes
publishing a fresh JSON the consequence of that. R5 published none, correctly, and
its reasoning is preserved and distinguished rather than overturned.

**R6 is published as a full carry-forward revision, in the form R2, R3, R4 and R5
used.** The body below — `§R5`, `§R4`, `§R3`, `§R`, and `§0` through `§9` — is R5's
text, carried forward **byte-identically** except in the three places this revision
amends, each marked in place with `(R6, …)` and each declared in §R6.3. A reader
holding this file holds the whole specification in force and needs no second
document open beside it. The instrument is the one R1 §6.7 item 3 provides — a new
directory and a new tag, no predecessor edited.

**The three places the body is amended**, all of them the body expression of the
one decision §R6.1 states, none of them a new decision:

| | amendment | where in the body |
|---|---|---|
| **D1** | §8 check 8's offer-level non-duration clause gains the symmetrically-tagged conflict-family case and the new report-only rule code `CONFLICT_FAMILY_ROW_KEY_COLLISION`; the key itself, and the `FAIL` gate in every other case, are untouched | §8 check 8, including its severity summary table |
| **—** | §0.3's precedence chain sentence gains one link | §0.3 |
| **—** | §7.6 item 8's per-revision tag record gains one line | §7.6 item 8 |

The second and third are mechanical extensions of a list, of exactly the kind R5
made when it followed R4. They carry no decision.

**One further heading is disambiguated, and it is not an amendment of substance.**
R5's `## Appendix — provenance of this revision` names no revision in its own
heading, so carried into this document unlabelled it would read as R6's provenance
when its content is R5's. Its heading alone becomes `## Appendix (R5) — provenance
of the R5 revision`; not one word of its body changes. R6's own provenance appendix
is a separate section, immediately after §R6.5. Sections `§R5.1`…`§R5.7`, `§R4.1`…
`§R4.6`, `§R3.1`…`§R3.3` and `§R.1`…`§R.3` need no such treatment: each sits under a
heading that names its own revision, so every "this revision" inside them is
already scoped by the heading above it, exactly as R5 carried R4's.

**Precedence.** R4 §0.3's rule, extended by one link: **where R6 is silent, R5
governs; where R5 is silent, R4 governs; where R4 is silent, R3 governs; where R3
is silent, R2 governs; where R2 is silent, R1 governs.** No revision relaxes a
prohibition of the revision before it. R6 relaxes one severity, in one narrowly
defined case, and §R6.1 argues that case rather than assuming it; every other gate
R5 left standing, R6 leaves standing.

**Entry into force is unchanged and is not restated here.** R6 governs every
validation run after `frozen/collection-spec-r6` is created, and not before (§7.6,
and §R6.5). The tag is the operator's to create; measured at the time this file was
written, it did not exist, and the task that wrote this file did not create it.

**R1, R2, R3, R4 and R5 are unmodified and remain valid.** Not one byte of any
predecessor directory is touched by this revision. R2 remains the specification
`B01`, `B02`, `B03` and `B04` were validated under (R4 §R4.3); R5 remains the
specification in force from `frozen/collection-spec-r5` until R6 is tagged; and
every acceptance decision taken under any of them stands.

**Naming warning.** `R1`/`R2`/`R3`/`R4`/`R5`/`R6` are revisions of *this collection
specification*. They are a different namespace from the model versions
`V1`/`V1.5`/`V2`, and nothing here refers to, touches or unseals
`SEALED_V3_MARKET_REGIME_CANDIDATE` or any sealed `V3`/`V4` model item.

**Scope of this revision — one decision, and the file it obliges.**

| | change | §R6 | touches |
|---|---|---|---|
| **D1** | §8 check 8's offer-level non-duration key is **unchanged**. Where a colliding key group is, on every one of its rows, tagged into one and the same conflict group and carries a conflict-family `field_status`, the collision is reported under the new `CONFLICT_FAMILY_ROW_KEY_COLLISION` — informational, never gate-affecting. In every other case `DUPLICATE_ROW_KEY` remains a `FAIL` | §R6.1 | §8 check 8 only |
| **D2** | R6 publishes its own machine-readable specification file, because D1 adds a rule code to a list that file enumerates | §R6.2 | `PRETRADE_EXTENSION_COLLECTION_SPEC.json` only |

Nothing else changes. The full non-change declaration is §R6.3, the retroactive
posture is §R6.4, and the entry-into-force rule is §R6.5, which refers to R4 §7.6
and does not restate it. `COLLECTOR_INSTRUCTION.md` is carried into this directory
**byte-identically** from R5, sha256
`162d01f01b8642f9910b061a04d5b37a82d5b8e9791e390ee426b138e8821313` in both
directories: D1 is a validator severity rule and imposes no collector obligation
whatever, so the collector-facing document has nothing to reflect (§R6.3).

**Ordering claim.** R1's, R2's, R3's, R4's and R5's ordering claims are carried
forward unchanged and apply to every field they named. This revision adds no field,
so it makes no new field-selection claim. D1 changes the severity under which one
narrowly defined collision is reported; it adds no feature, no target and no
comparable. Outcome-read counter for this revision's authoring session:
`REALIZED_OUTCOME_READS = 0`. No D1/D3/D5/D10 return, no open/high/low/close, no
ceiling or drawdown value, no THB/THM file content and no value under
`artifacts/outcomes/`, `artifacts/predictions/` or `artifacts/live_forecast/` was
opened. D1's condition — symmetric tag plus conflict-family status — was fixed
before the option comparison of §R6.1 was read, and the measurement it rests on was
performed by a separate, earlier task that took no decision.

**A note on identifiers.** The `K11`, `K16`, `O1`, `O2`, `O5`, `O6`, `O11`, `A3`
citation caveat R5 carried applies unchanged and is not repeated here; see §R5's
own header treatment in the predecessor directory. R6 introduces no new identifier
of that kind. The one external artifact R6 cites,
`artifacts/derived/BORSAI_B07_CHECK8_CONFLICT_KEY_MEASURE_20260912_V1/`, is a
repository path that resolves.

---

## R6. What changed from R5

One decision, and the machine-readable file that decision obliges. The instrument
is R1 §6.7 item 3's, as for every revision before this one: a new directory and a
new tag, no predecessor edited.

The measurement this revision rests on is
`artifacts/derived/BORSAI_B07_CHECK8_CONFLICT_KEY_MEASURE_20260912_V1/B07_CHECK8_CONFLICT_KEY_MEASUREMENT_20260912.md`,
together with its reimplementation script `simulate_check8_options.py` in the same
directory. That note is `MEASUREMENT_ONLY`: it measured three options and
deliberately declined to rank or recommend one. The choice among them is taken
here, and the numbers below are **quoted from it rather than re-derived**, which is
the honest division of labour — a decision section that silently re-measured its
own evidence would be marking its own work.

### R6.1 §8 check 8 — a symmetrically tagged conflict family is reported, not gated (D1, binding)

**Defect (R4/R5).** §8 check 8's offer-level non-duration key is
`(ticker, field_name, scope_tag, source_url)`, and a repeat of it is
`DUPLICATE_ROW_KEY`, a `FAIL`. R4 replaced check 8 in full and left this key alone,
measuring 0 excess rows in 703 offer rows. R5 added an interpretive note (§R5.2, D4)
observing that because the key carries `source_url`, the same field recorded from
**two different documents** is two distinct keys and was never a duplicate.

`B07` produced the case neither revision reaches. Delivery rows 118 and 119 record
`ONRYT` `order_count` twice, from **one** document — the same `source_url` — under
the same `scope_tag`. The two rows are not a transcription accident. Both carry
`conflict_group_id = CG_ONRYT_ORDER_01`, and both carry
`field_status = SEMANTIC_DIFFERENCE`. That is the collector doing precisely what
§4.1, §4.2 and the conflict rules oblige: one document stating the same field under
two different semantics, both readings recorded, neither discarded, the pair tied
together by a shared group id. Check 7, conflict integrity, is satisfied by exactly
this shape. Check 8 then fails the batch for it.

The contradiction is the same *kind* R4 D2 resolved for duration rows, and it is
worth naming as such rather than treating as new: one provision of this
specification obliges the collector to write two rows, and another provision
obliges the validator to reject a batch containing them. R5's D4 does not dispose
of it. D4's fix condition is a *different* `source_url` per row; the measurement
checked ONRYT directly and both rows carry the same one
(`https://www.kap.org.tr/tr/api/file/download/4028328d8f3f7793018faa1eee3f409c`),
which is the shape D4 explicitly calls "one document recorded twice".

**The measurement.** The note reimplemented check 8's routing from the committed
code and verified the reimplementation against ground truth before using it: over
`B01`–`B07` the baseline reproduces `DUPLICATE_ROW_KEY = 0` for `B01`–`B06` and
`= 1` for `B07`, **7 of 7 batches MATCH**, against the committed reports for `B05`,
`B06` and `B07` and, for `B01`–`B04` — which have no committed report that ran
check 8 at all, every such report predating the task that first implemented it — a
read-only re-run of the unmodified `scripts/validation/validate_batch.py` written
outside the repository.

Conflict-family rows in the delivered data, offer file:

| batch | conflict-family rows | offer rows |
|---|---:|---:|
| `B01` | 0 | 133 |
| `B02` | 0 | 140 |
| `B03` | 0 | 128 |
| `B04` | 0 | 145 |
| `B05` | 0 | 139 |
| `B06` | 0 | 135 |
| `B07` | **2** | 137 |

Zero in the demand-category file of every batch. Across all seven delivered
batches, 35 tickers and 957 offer rows, **the `ONRYT` `order_count` pair is the only
conflict-family case that exists at all**, in either file. One group,
`CG_ONRYT_ORDER_01`, of size 2. `SEMANTIC_DIFFERENCE` is the only conflict-family
`field_status` that occurs anywhere in `B01`–`B07`; `SOURCES_CONFLICT` and
`SCOPE_DIFFERENCE` occur in no delivered batch.

**N = 1.** This revision states that in its own text so that a later reader cannot
mistake it for a measured rate. Every claim below about how often this case arises
is a claim about a single observation. It is not a frequency, it is not a base rate,
and no proportion is computed from it. What *is* measured over the full seven
batches is the counterfactual behaviour of the three options, which the note
computed on real data for every batch rather than reasoning about.

**The three options, and why each was rejected.**

*Option (a) — add `conflict_group_id` to the key.* Rejected on two independent
grounds, both measured.

First, it does not work. `ONRYT`'s two rows already carry the **identical**
`conflict_group_id`, so appending that column produces the same key tuple for both
and does not split them. Measured across all seven batches, option (a) is identical
to the baseline everywhere, `B07` included: it still raises 1. **The option does not
separate the pair that prompted this revision.** That alone disposes of it.

Second, and more seriously, it makes a `FAIL` gate weaker in a way that is silent.
The note's masking Test 2 constructs a genuine duplicate — the same row transcribed
twice, `field_status = VALUE_RECORDED` on both, no semantic-difference claim — with
`conflict_group_id` present on one row and `NOT_APPLICABLE` on the other. Under the
baseline it is caught. Under option (a) the two rows carry different fifth key
elements, the key splits a real duplicate into two singleton groups, and **nothing
fires: not a `FAIL`, not a report, nothing at all**. An option whose safety depends
on a collector applying a tag symmetrically, where no frozen text requires that
symmetry, and whose failure mode is silence rather than a report, is not a
tightening. Masking Test 1, where the tag is symmetric, is caught by option (a) —
which is exactly the point: the vulnerability is in the asymmetric case, and the one
real case in the data is symmetric, so the delivered data does not exercise it.

*Option (b) — exclude conflict-family rows from the key.* Rejected. It fixes the
`ONRYT` case, taking `B07` from 1 to 0. It does so by removing every row carrying
`SOURCES_CONFLICT`, `SCOPE_DIFFERENCE` or `SEMANTIC_DIFFERENCE` from check 8's
non-duration key **entirely, for every field, on every batch** — not merely for
pairs that check 7 has separately established as one conflict group. Those rows
become invisible to check 8: not reported, not counted, absent. And the exclusion
rests on a single collector-written `field_status` value. A collector who writes
`SEMANTIC_DIFFERENCE` on two genuinely duplicated rows removes them from a `FAIL`
gate with one cell. Resting a gate on one unverified free choice, and disappearing
the rows rather than reporting them, is a worse trade than the one D1 accepts.

*Option (c) — demote the offer-level non-duration key to report-only.* Rejected as
far too wide. It changes no grouping at all; the detection is identical to the
baseline on every batch and only the severity moves. But it moves that severity for
**every** non-duration collision on every batch, discriminating neither by
`field_status` nor by `conflict_group_id`. The gate R4 measured at 0 excess in 703
offer rows, and which is the only thing standing between the offer file and one
document recorded twice, would stop being a gate for all fields at once. The case at
hand is one narrowly describable shape. Removing the gate everywhere to accommodate
it is not proportionate.

**The change.** The key is **unchanged**:
`(ticker, field_name, scope_tag, source_url)`. What changes is the severity of one
narrowly defined case, and nothing else.

For a key group of **more than one row**, where **all** of the following hold:

1. every row in the group carries a `conflict_group_id` other than
   `NOT_APPLICABLE` — a row whose `conflict_group_id` is absent, empty or
   `NOT_APPLICABLE` fails this condition for the whole group;
2. those `conflict_group_id` values are **all identical**; and
3. every row in the group carries a `field_status` drawn from the conflict family
   — `SOURCES_CONFLICT`, `SCOPE_DIFFERENCE` or `SEMANTIC_DIFFERENCE`;

the collision is reported under the new rule code
`CONFLICT_FAMILY_ROW_KEY_COLLISION` — **report-only, informational, never
gate-affecting** — naming the ticker, the field, the shared key, the shared
`conflict_group_id`, and each colliding row's `field_status`, `normalized_value` and
`page_or_section`, so a reader can see at once whether a genuine conflict family or
a duplicated row is in front of them.

In **every other case**, `DUPLICATE_ROW_KEY` remains a `FAIL` and the gate applies
exactly as R4 wrote it and R5 left it. That explicitly includes a group where the
tag is present on some rows and `NOT_APPLICABLE`, empty or absent on others: such a
group is **not** a conflict family for this purpose and **is** a `FAIL`. The
asymmetric case option (a) would have silently split is the case this rule most
deliberately keeps inside the gate.

The three conditions are conjunctive and none is redundant. Condition 1 without
condition 2 would admit a group whose rows belong to *different* conflict sets, which
is not one family. Condition 2 without condition 1 would be satisfied vacuously by a
group of rows all carrying `NOT_APPLICABLE`, which is every ordinary duplicate.
Condition 3 without conditions 1 and 2 is option (b), rejected above. Requiring all
three is what makes the demotion narrow: it fires only where the collector has both
declared a conflict-family reading **and** tied the rows together, symmetrically,
into one group — the shape check 7 independently verifies.

The rule code is deliberately not named "duplicate", for the reason R4 gave when it
named `DURATION_ROW_KEY_COLLISION`: the rows it reports are not duplicates, and a
code that called them one would re-import into the report text the contradiction the
rule exists to remove.

**(a) What stays a gate and what does not, per file.** Reproduced in full so that
this subsection can be read without R4's beside it. Only the first row's severity
column changes against R4; the other three are R4's, unchanged.

| file | key | R6 severity |
|---|---|---|
| offer-level, rows whose `field_name` is **not** §2.1 #15/#16/#17 | `(ticker, field_name, scope_tag, source_url)` | **`FAIL` gate — key unchanged, and unchanged in every case except one.** `DUPLICATE_ROW_KEY`. Where the colliding group satisfies all three conditions above, and only there, `CONFLICT_FAMILY_ROW_KEY_COLLISION`, report-only |
| offer-level, rows whose `field_name` **is** §2.1 #15/#16/#17 | `(ticker, field_name, scope_tag, duration_start_reference, undertaking_scope, source_url)` | **report-only** — `DURATION_ROW_KEY_COLLISION`, informational, never gate-affecting. **R4 D2, untouched by R6** |
| demand-category | `(ticker, normalized_category, source_category_label, source_url)` | **`FAIL` gate — unchanged. Untouched by R6.** Measured 0 excess |
| §5.6 cell-status register | `(ticker, normalized_category, source_category_label, field_name)` | **`FAIL` gate — unchanged. Untouched by R6.** Measured 0 excess. Load-bearing for §5.6 binding rule 1 ("two rows for one cell is a `FAIL` (§8 check 8)"), preserved intact by leaving it alone |

**(b) The residual, stated plainly.** A collector who symmetrically tags two
genuinely duplicated rows as one conflict group, and marks both with a
conflict-family `field_status`, is **reported, not gated**. That row pair passes.
This is the price of D1 and it is not hidden: it is written here, it is in the
`DECISION_LEDGER.csv` row for this decision, and the report that names it is the
only thing that will bring it to a reader's attention.

It is the same class of residual R4 D2 accepted for duration rows — "a genuine
duplicate duration row is now reported and not gated" — and it is accepted for the
same reason: the alternative is failing batches for row patterns this specification
elsewhere requires. It is also **narrower** than R4 D2's residual in one respect
worth recording. R4 D2 demoted an entire clause covering all rows of three fields.
D1 demotes only groups that clear three simultaneous conditions, on fields that are
otherwise fully gated, and check 7 independently verifies the very tagging the
demotion depends on.

Measured exposure: **0**. Across `B01`–`B07` no genuine duplicate of any shape was
found by the baseline other than the `ONRYT` pair, which is not one. But the
measurement's own warning is adopted here rather than paraphrased away — a zero
fitted to seven batches is exactly the kind of number that looks decisive until the
eighth.

**(c) What this rule is not evidence for.** N = 1. One conflict group, one ticker,
one field, one batch. This revision claims no rate, no proportion and no
expectation about how often conflict families will appear in `B08`…`B16`. It claims
only that the shape is legitimate, that check 7 already blesses it, that check 8
currently fails it, and that the three-condition demotion is the narrowest available
instrument for that. If the shape turns out to be common, the deferred fix below
becomes correspondingly more urgent, not less.

**(d) The deferred structural fix, in the spirit of R4 §R4.2(c).** The correct
long-term resolution does not infer a row's status from a collector-assigned
identifier at all. It puts the distinction **in the schema**: a typed discriminator
on conflicting rows — a declared, validated column stating what distinguishes this
row from its twin — so that check 8's key can separate a genuine conflict family from
a duplicate structurally, and the offer-level key can go back to being a `FAIL` gate
with no severity exception in it.

R6 does **not** implement it, and records what it would cost, so that the next
genuine schema revision does not have to rediscover the list:

- a new offer-level column, the 27th, and therefore the first column change since
  R1;
- a third arm in §8 check 1's column-count resolution, which today resolves 24 for
  V1 rows and 26 for V2 rows;
- a new `spec_version` string, and therefore a fork of the §7.4 item 4 merge key —
  the fork R3's `CHANGELOG_R2_TO_R3.md` §4 argues against;
- a genuine reissue of `COLLECTOR_INSTRUCTION.md` imposing a new collector
  obligation, which R5's D5 reissue was explicitly not;
- and a documented coexistence rule, or a back-fill, for the rows already delivered
  under V2 across `B01`–`B07`.

That is a schema revision and it must be decided as one. It shares this reservation
with R4 §R4.2(c)'s typed undertaking identifier, and the two should be decided
together rather than consuming two schema revisions for one column change each.

**(e) An absence found while drafting, recorded and not filled.** The measurement's
step 1d searched the frozen texts for a definition of "free text" and for a column
type on `conflict_group_id`. This revision re-ran that search rather than repeating
the claim, and the finding holds, with one refinement the original wording
understates.

Confirmed: **no frozen text defines "free text".** The phrase occurs ten times in
this document's carried body and four times in R4's JSON, every time descriptively —
about `sector`, about `page_or_section`, about `verbatim_source_phrase`, about a
category label — and never as a rule that could classify a column not already
discussed. Confirmed: **`conflict_group_id` carries no declared type.** The JSON's
`field_dictionary.offer_level_fields` types all 22 data fields, and
`conflict_group_id` is not among them; it appears in the machine-readable file only
as a bare column name in the column lists, exactly like `source_url` and `notes`,
and unlike `field_status`, which column 20 explicitly annotates as a §1.6 enum.

The refinement: it is not true that *no* column-type vocabulary exists anywhere. The
JSON does carry a `type` on each of those 22 data fields, drawn from
`boolean`, `date`, `decimal`, `enum`, `integer`, `string`. What does not exist is
any definition of "free text" and any type at all for the collection-audit columns,
`conflict_group_id` among them. The distinction matters because D1's condition 1
tests that column's value, and there is no declared format it can be tested against.

R6 **does not invent a taxonomy** to fill this. Inventing one here would be a schema
act performed under a severity revision, which is the thing §R6.3 forbids. The
absence is recorded as a finding, it is a reason the deferred fix in (d) is the right
shape, and it is left open.

### R6.2 R6 publishes its own machine-readable specification file (D2, binding)

R5 published no `PRETRADE_EXTENSION_COLLECTION_SPEC.json`, and the ledger records
why, in the row for `BORSAI_D1_POINT_IN_TIME_GATE_20260912_V1`, at file-line 80 of
`artifacts/governance/DECISION_LEDGER.csv`, status `KAPALI`:

> R5 dizininde JSON yoktur ve tag atildiktan sonra eklenemez; R5 hicbir sutun sira
> enum veya sema degisikligi yapmadigini kendi metninde beyan ettigi icin validator
> R4'un JSON'unu mesru olarak kullanir; enum veya sutun degistiren ilk revizyon
> kendi JSON'unu yayimlamak zorundadir.

The last clause is the operative one: the first revision that changes an enum or a
column must publish its own JSON. R6 is that revision, and the following are
provisions of this revision.

1. **The ruling applies to R6.** D1 adds `CONFLICT_FAMILY_ROW_KEY_COLLISION` to
   `check_8_rule_codes`, a closed map the machine-readable file enumerates and which
   today holds exactly two entries, `DUPLICATE_ROW_KEY` and
   `DURATION_ROW_KEY_COLLISION`. Adding a member to an enumerated machine-readable
   list is the case the ruling names. R6 therefore publishes its own JSON in this
   directory, and R4's ceases to be the machine-readable form of the specification
   in force once R6 is tagged.

2. **Why the question was close, and why closeness did not decide it.** The
   rule-code maps are declarative. The committed validator emits its rule-code
   strings as literals in `scripts/validation/validate_batch.py` and reads the JSON
   for schema, enum and sentinel data, not for rule-code severities. Had R6
   published no JSON, the divergence between the governing text and the
   machine-readable file would therefore have been **documentary, not
   behavioural**: no validation run would have behaved differently. That is recorded
   as the reason the question was genuinely close. It is **not** recorded as a reason
   to waive the ruling. A `FROZEN_GATE` artifact whose machine-readable half states
   that check 8 has two rule codes while its governing half states three is wrong
   whether or not any program currently reads the wrong half, and the ruling exists
   precisely so that the answer does not turn on the current shape of the code.

3. **R6's JSON declares the same `spec_version` string as R4's**,
   `PRETRADE_EXT_COLLECTION_SPEC_V2`. It is not forked, because R6 changes no
   column, no column order, no schema and no collector-facing enum. The rule-code
   map is a validator-facing register of report vocabulary, not a collector-facing
   enum: no collector writes a rule code into any cell of any output file, and no
   output row's content differs by one byte between R5 and R6.

4. **Consequently R4's JSON and R6's JSON must never be loaded together.** They
   declare the same `spec_version`, and `build_spec_registry` in the committed
   validator raises on the second of two specs declaring one version, which the CLI
   reports as `BLOCKED` and exits 2. This is not a defect to be worked around; it is
   the routing invariant doing its job. **Every validation run positioned after
   R6's tag loads R1 + R6.** Runs positioned before it load R1 + R4, as today. R2's
   and R3's JSONs declare the same string and have always been mutually exclusive
   with R4's in the same way; R6 adds one more member to that set and no new
   mechanism.

5. **Prior validation reports produced under R1 + R4 remain valid as historical
   records and are not re-run because of this revision.** A report is a record of
   what a validator concluded under the revision then in force, and R4 §7.6 makes
   that revision a function of the tag at the moment of the run. Nothing in R6
   reaches backwards into a completed run. §R6.4 states the retroactive posture in
   full.

### R6.3 What this revision does not do

R6 changes **exactly one thing** in the specification's rules: the severity under
which one narrowly defined check-8 collision is reported. It publishes one file it
would not otherwise have published, for the reason §R6.2 gives.

Specifically, and bindingly, R6 does **not** change:

| | § |
|---|---|
| The `spec_version` string, `PRETRADE_EXT_COLLECTION_SPEC_V2`, written into every output row | §5.1, §5.3 |
| Any column, in either file or the register. Offer columns 26, demand-category 31, register 9 | §5.3, §5.5, §5.6 |
| Any column order | §5.3, §5.5, §5.6 |
| Every collector-facing enum — inherited and the specification's own. R6 extends none and introduces none. `CONFLICT_FAMILY_ROW_KEY_COLLISION` is a validator report code, not a member of any enum a collector may write | §1.6 |
| `field_status`'s allowed values, including the three conflict-family members D1's condition 3 tests. D1 **reads** them; it does not add, remove or redefine one | §1.6 |
| `scope_tag`'s six allowed values and its mandatory/`NOT_APPLICABLE` map | §2.1 |
| `conflict_group_id`'s definition, its format, or the absence of a declared format. D1 tests only whether the value is `NOT_APPLICABLE` and whether two values are equal | §5.3 |
| Check 8's **keys**. All four are exactly R4's | §8 check 8 |
| Check 8's other three severities. The demand-category and register `FAIL` gates and the duration report-only clause are untouched | §8 check 8 |
| Check 7, conflict integrity, whose obligations D1 relies on and does not alter | §8 check 7 |
| Every other §8 check — check 11's R4 definition and check 12's R3 definition included | §8 |
| Any §9 standing prohibition. R6 adds none and weakens none | §9 |
| Any collector obligation whatever. `COLLECTOR_INSTRUCTION.md` is carried byte-identically from R5 | §R6.1, and the header |
| R5's D1 point-in-time restriction, D4 note and D5 reissue, all carried forward intact | §R5.1, §R5.2, §R5.3 |
| R4 §7.6's entry-into-force mechanism, which §R6.5 refers to and does not restate | §7.6 |

**No delivered byte changes.** No row of any delivered batch is rewritten,
re-tagged, re-scoped or deleted by this revision. R4 §R4.5 items 3 and 4 and §7.6
item 6 apply unchanged.

**R6 does not resolve B07-2, and `B07` remains `FAIL` until B07-2 is separately
decided.** B07's validation raised two violations. This revision addresses one of
them, B07-1, the `ONRYT` `order_count` `DUPLICATE_ROW_KEY`. The other, B07-2 — the
`HRKET` `demand_share_pct` percentage-base reconstruction mismatch measured in
`BORSAI_B07_HRKET_PCT_MEASURE_20260912_V1` — is untouched here, is not reached by
anything in D1, and remains `ACIK`. **`B07` is not accepted by this revision.** No
part of this document should be read as accepting it, and no acceptance row for
`B07` accompanies it in the ledger.

**Work this revision explicitly leaves outside itself.** Each is a separate,
separately-authorized task. R6 neither performs nor pre-judges any of them.

1. **Implementing D1 in `scripts/validation/validate_batch.py`.** R6 changes no
   script. Until a separate task implements the new rule code, the committed
   validator and this specification disagree about check 8: the code will raise
   `DUPLICATE_ROW_KEY` as a `FAIL` on a group R6 makes report-only. That disagreement
   is stated here, is recorded in the ledger as `ACIK`, and is not a licence to treat
   `B07-1` as passing before the code is changed and the tag exists.
2. **The deferred structural fix of §R6.1(d)**, and R4 §R4.2(c)'s typed undertaking
   identifier with it.
3. **B07-2, and `B07`'s acceptance decision.**
4. **R4 §R4.6's M1–M3 measurement** and **R5 §R5.6's point-in-time register**, both
   ordered by their own revisions and neither performed nor closed here.

### R6.4 Retroactive application (binding)

1. **R6 applies to validation from the moment its tag is created**, per §R6.5 and
   R4 §7.6. It does not apply to any batch validated before that moment.
2. **No delivered byte is rewritten.** R4 §R4.5 item 2, applied again and not
   weakened.
3. **No completed validation run is re-run because of this revision, and no report
   is amended.** A rule applied correctly under the revision then in force stays
   applied. Reports produced under R1 + R4 stand as historical records (§R6.2 item
   5).
4. **No acceptance decision is reopened.** `B01`–`B06` are unaffected in fact as
   well as in rule: the measurement computed all three options against the baseline
   on every batch and all agree at 0 excess for `B01`–`B06`. Only `B07`, which is
   not accepted, differs across the options.
5. **`B07` is not retroactively rescued.** Its committed `FAIL` report stands as the
   record of what the validator concluded on the day it ran, under R5. Whether
   `B07-1` is discharged is a question for a re-run performed after R6's tag exists
   and after the validator implements D1, and B07-2 is unaffected either way.
6. **Nothing here touches an outcome, a prediction or a model artifact.** Every
   statement in this revision concerns a validation rule, a report severity and a
   machine-readable file.

### R6.5 Entry into force

R6 does not restate the entry-into-force mechanism. It **refers** to R4 §7.6, which
is binding on every revision including this one, and adds nothing to it.

Applied to this revision, and in §7.6 item 5's required form: **R6 governs every
validation run after the `frozen/collection-spec-r6` tag is created.** Not from a
batch number, not from this file's write date, not from the commit that adds it.
Before that tag, R5 governs, and a run in that window is correct under R5.

The tag is created by the operator. The task that wrote this revision did not create
it and was forbidden from creating it. Measured at the time this file was written,
`frozen/collection-spec-r6` was absent from the repository. Until it exists, this
document is a published but un-enacted revision, and R5 is the specification in
force.

---

## Appendix — provenance of this revision

Written on 2026-09-12 by `BORSAI_COLLECTION_SPEC_R6_20260912_T21`, which read
`artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260912_R5/PRETRADE_EXTENSION_COLLECTION_SPEC.md`
(sha256 `054d08c1c2697704d6f9561810d4bee89e78987ec36a418b1303c7da2fa8ad76`, 2885
lines) and wrote it into this file with the three amendments §R6 declares, plus this
revision's own header block, its own `§R6` section and this appendix, and plus the
one heading disambiguation the header block names.

The machine-readable file in this directory is a full carry-forward of
`artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260909_R4/PRETRADE_EXTENSION_COLLECTION_SPEC.json`
(sha256 `6b90f135daa2a7026b51fee144dda094a4d4d2fe8d36042195de08a5754fa133`, 1664
lines) with exactly three changes: this revision's identifiers, the supersedes and
predecessor block repointed to R5, and `check_8_rule_codes` gaining
`CONFLICT_FAMILY_ROW_KEY_COLLISION`. R5's directory carries no JSON, so R4's is the
only available predecessor, which is itself an instance of §R6.2's point.

`COLLECTOR_INSTRUCTION.md` is byte-identical to R5's issue, sha256
`162d01f01b8642f9910b061a04d5b37a82d5b8e9791e390ee426b138e8821313` in both
directories, verified by comparison after copying.

The decision this revision takes was measured by
`BORSAI_B07_CHECK8_CONFLICT_KEY_MEASURE_20260912_V1`, a separate `MEASUREMENT_ONLY`
task that ranked nothing. The numbers in §R6.1 are quoted from its note; the step 1d
finding in §R6.1(e) was independently re-verified here and is reported with the one
refinement that re-verification produced. One judgment recorded in that note did
**not** survive: it concluded that none of the three options "would trigger the
ledger's standing 'first revision that changes an enum or column must publish its own
JSON' rule". That was measured against the options as severity mappings. Introducing
a *named* rule code to carry the demotion, which is what D1 does, adds a member to
the JSON's `check_8_rule_codes`, and §R6.2 records why the ruling therefore applies.
The note's conclusion is superseded on that one point and stands on every other.

No predecessor directory was modified. No tag was created. No script was written or
modified. No collected byte was written or altered. `REALIZED_OUTCOME_READS = 0`.

---

## R5. What changed from R4

Three changes, argued independently, published as one revision because they share
one instrument (R1 §6.7 item 3: a new directory, a new tag). None is a premise of
another: D1 is a source rule, D4 is an interpretation of an unchanged validation
key, and D5 is the reissue of a collector-facing document. Each carries its own
ledger row, so a later reader can accept or reject any one of them without
reference to the other two.

### R5.1 A live company record is a retrieval-time record (D1, binding)

**The defect.** §2.1 #19 `sector_kap_code` and #20 `sector_kap_label`, and the
collector instruction's field 23 `company_name`, are collected from the company
record page of the disclosure platform (`KAP_COMPANY_RECORD`, §3.3). That page is
live. It shows the issuer's sector code, sector label and legal name **as they
stand on the day it is opened** — after any sector reclassification, any renaming,
any market transfer that happened since listing. R1's `scope_tag` vocabulary
already anticipated the distinction by offering `AS_OF_LISTING` and
`AS_OF_RETRIEVAL` on #19 and #20, and the collector instruction already told the
collector to choose "according to which the record you opened actually
represents". What neither said is the thing that decides the choice: *a live page
can only ever represent the moment it was retrieved.* Left to judgement, a
collector reading a current sector code off a current page can write
`AS_OF_LISTING` in good faith and record a fact that post-dates the listing. For
a cohort whose entire purpose is pre-first-trade evidence, that is a
point-in-time defect, and R5 closes it by rule rather than by expecting better
judgement.

**The rule. Five provisions, all binding.**

1. **A value whose source is `KAP_COMPANY_RECORD` may carry exactly one
   `scope_tag`: `AS_OF_RETRIEVAL`.** This holds on #19, #20 and on field 23
   wherever that field's row is scope-tagged at all. It is not a preference and
   not a default to be overridden by argument about how unlikely a change is.

2. **`AS_OF_LISTING` may be written only from a document published on or before
   the ticker's `first_trading_date`** — the izahname / sermaye piyasası aracı
   notu, the tasarruf sahiplerine satış duyurusu, the Borsa İstanbul kotasyon or
   "payların işlem görmeye başlaması" notice, or the disclosure-platform
   notification of that time. The test is the document's **publication date**,
   under §4.6 and §1.7 unchanged: an internal signature date is never substituted
   for it, and a later republication is never evidence that the content was
   available earlier.

3. **One exception — the newly listed issuer.** If the retrieval date is on or
   before the ticker's `first_trading_date`, the company record page *is* a
   point-in-time record of the listing state, because no post-listing interval
   exists for it to have drifted across. On such a row `AS_OF_LISTING` is correct,
   and the retrieval moment is recorded on the row in the existing column 18
   `retrieval_timestamp_istanbul` — which is already mandatory on every row, so
   the exception adds no column and changes no schema. The threshold is exactly
   this comparison — retrieval date versus first trading date — and it was fixed
   before any count of affected rows was measured (O11).

4. **Retroactive application, bounded.** Not one delivered byte changes (R4 §R4.5
   item 2): no row is edited, no row is deleted, no batch is re-collected and no
   acceptance decision is reopened (R4 §R4.5 items 3 and 4, §7.6 item 6). Rows in
   `B03` and `B04` that carry `AS_OF_LISTING` on #19, #20 or field 23 while naming
   `KAP_COMPANY_RECORD` as their source are **`POINT_IN_TIME_UNVERIFIED`**. That
   marking is a *derived observation about* delivered rows, never a value *in*
   them:

   - it lives only in a derived register under `artifacts/derived/`, never under
     `inputs/`, which holds delivered collection bytes and is written by the
     collector alone (R4 §R4.6, same rule);
   - `POINT_IN_TIME_UNVERIFIED` is **not** added to `field_status` or to any other
     vocabulary. §1.6's rule stands untouched: an inherited enum is reused
     verbatim and never extended. `field_status` is inherited, and R5 extends
     nothing;
   - it changes no verdict, no status, no acceptance and no report already
     committed. Corrections are published beside reports, additively, never inside
     them (R4 §R4.5 item 4).

   **Producing that register is not this revision's work.** It is ordered as a
   separate mechanical task in §R5.6.

5. **This document states no count.** How many rows the marking reaches is a
   measurement, and a measurement belongs to the task that performs it, on the
   delivered bytes, with its own provenance. No row count, no ticker list and no
   proportion is written into this text, so that no later reader can mistake a
   drafting-time assertion for a measured one.

**What D1 does not do.** It does not change #19's, #20's or field 23's meaning,
name, unit, primary document family or absence encoding. It does not forbid the
company record as a source — it is still the primary document for those fields
(§3.3) — it fixes what scope a value taken from it may claim. It does not require
any collector to find a listing-era sector document that does not exist: where no
document published on or before `first_trading_date` states the field, the row is
what it always was, an `AS_OF_RETRIEVAL` value or, after a real search, a
`DATA_NOT_FOUND` with a non-empty `search_scope` (§4.4). And it introduces no
inference: a collector never reasons backward from a current sector code to a
listing-date one.

### R5.2 §8 check 8 — what the offer-file key does and does not catch (D4, interpretive)

R4 replaced check 8 in full and left the offer-level non-duration key as
`(ticker, field_name, scope_tag, source_url)`, a `FAIL` gate, "unchanged from
R2/R3 in key, meaning and severity". That remains true and R5 changes none of it.

The note this revision adds, and it is a **reading correction, not a rule**:

> Because the offer-file duplicate key carries `source_url`, two rows recording
> the **same field of the same ticker under the same scope from two different
> documents** are **not** a duplicate and were never one. They are two distinct
> keys, and they are exactly what §3.4 asks the collector to produce: each source
> recorded as its own row, agreement established downstream by the validation
> script comparing rows, never by the collector picking one and discarding the
> other. A check-8 reader who sees the same `field_name` twice for one ticker and
> reaches for `DUPLICATE_ROW_KEY` has misread the key: the rule fires only when
> the `source_url` is also the same, which is one document recorded twice.

Nothing follows from this note operationally. **No severity changes. No rule code
changes. No key changes. No gate is added, removed, widened or narrowed.** The
three `FAIL` keys (offer non-duration, demand-category, cell-status register) and
the one report-only code (`DURATION_ROW_KEY_COLLISION`, offer §2.1 #15/#16/#17)
stand exactly as R4's severity summary prints them. The note exists because check
8 is titled "Duplicates" and the title invites the misreading — R4 said as much
about the duration clause ("It is not called a duplicate, because it is not one")
and D4 completes the same thought for the multi-source case.

### R5.3 `COLLECTOR_INSTRUCTION.md` is reissued (D5)

R4 explicitly did **not** reissue the collector instruction. R5 does, as the R5
issue, published beside this file in this same directory. The reissue is the full
text of the instruction in force under R4 with exactly the changes listed below,
and it adds no column, no field, no enum member and no new obligation to search.

| | change | where in the instruction |
|---|---|---|
| a | §0 is emitted in `<BATCH_ID>` / `<BATCH_TICKERS>` placeholder form; no fixed batch id is left written into the document, and the stray standalone character measured in a delivered instantiation is not present | §0 |
| b | `undertaking_scope` carries, verbatim and in the source's own words, not only the bound party but the **kind of restriction** where the source states one | §4.1a item 3, §7.16 |
| c | where none of §4.1a item 6's branches covers a case, `duration_start_reference` stays `NOT_SPECIFIED`, the row's `field_status` becomes `SPEC_EDGE_CASE_UNRESOLVED`, the verbatim sentence is written, and the case is raised in the work note | §4.1a item 6, §10 |
| d | D1's prohibition and its one exception, in collector language | §2 (new item 11), §4.1a `scope_tag` obligations |
| e | an already-delivered batch is never re-collected | §0 |
| f | the outcome-firewall confirmation line in the work note | §11 item 4 — **already present, not restated** |

**Neither (b) nor (c) extends a closed vocabulary, and this is the reason they are
safe.** §7.16 `undertaking_scope` is explicitly *not* a closed vocabulary: it
takes the source's own wording, with one reserved value, `SCOPE_NOT_SPECIFIED`.
Asking for the restriction's kind alongside the bound party asks for more of the
source's own sentence, not for a new value, and the collector still does not
parse, translate, classify or structure it. §7.15 `duration_start_reference` *is*
closed, at six members, and (c) extends it by nothing: it directs the collector to
the member that already covers an unanchored duration, `NOT_SPECIFIED`, and moves
the unresolved case into `field_status`, whose `SPEC_EDGE_CASE_UNRESOLVED` member
is inherited and already exists (§1.6). This is R4 §R4.2(c)'s discipline applied
again: an unresolved case is recorded and escalated, never improvised into a sixth
answer.

**(f) is verified, not assumed.** The work-note obligation in §11 item 4 already
requires "an explicit line confirming that no post-listing price, return or
trading data was read, recorded or used". It was measured present in the
instruction in force and is therefore carried forward untouched. R5 does not
restate it, and the absence of a change here is not an absence of the obligation.

**(e) is stated in the instruction itself, not only here.** No collector is asked
by this reissue to re-open a document, re-read a source or re-record a row of any
batch already delivered. The same bytes that satisfied R2, R3 and R4 satisfy R5.

### R5.4 What this revision does not do

R5 changes **exactly three things**: which evidence may bear `AS_OF_LISTING`
(D1), how §8 check 8's offer-file key is to be read (D4, interpretive), and the
text of the collector instruction (D5). One is a source rule, one is a comment,
one is a collector-facing reissue that adds no column.

Specifically, and bindingly, R5 does **not** change:

| Unchanged | Where |
|---|---|
| The spec version string `PRETRADE_EXT_COLLECTION_SPEC_V2` | header, §5.3 col. 24, §7.4 |
| Offer-level column **count (26)** and column **order**, and every column meaning | §5.3 |
| Demand-category column count (31) and order; cell-status register (9) and order | §5.5, §5.6 |
| Every enum list — inherited and the specification's own. R5 extends none and introduces none. `POINT_IN_TIME_UNVERIFIED` is a derived marker, not a `field_status` member (§R5.1 item 4) | §1.6 |
| The 22 offer-level field names and the 15 demand-category data fields, their meanings, units and primary document families | §2.1, §2.2 |
| `scope_tag`'s six allowed values, and its mandatory/`NOT_APPLICABLE` map across fields | §2.1 |
| §2.1.1 in full — one row per undertaking, never convert a unit, a stated zero is a real zero | §2.1.1 |
| f3 semantics and every total-demand column | §2.3 |
| The source tiers, the document families and §3.4 multi-source recording | §3 |
| The conflict, absence and timestamp rules | §4 |
| Every §8 check — including check 8's keys, severities and rule codes (§R5.2 is a note), check 11's R4 definition, and check 12's R3 definition | §8 |
| The calibration set, method, blindness rule and acceptance gates | §6 |
| The **frozen batch table** and the batch protocol | §7.2, §7.3 |
| R4 §7.6's entry-into-force mechanism, which §R5.7 refers to and does not restate | §7.6 |
| Every standing prohibition | §9 |
| Any target definition, feature set, fold protocol, preprocessing step, training-eligibility rule, decision rule, gate threshold, preregistration, benchmark or scientific primitive | outside this document |

**Work this revision explicitly leaves outside itself.** Each of the following is
a separate, separately-authorized **mechanical** task. R5 neither performs nor
authorizes any of them, and no reader should treat their absence here as a
finding:

1. **Coding §8 checks 6, 7 and 10.** Still unwritten; §8 remains a requirement
   list, and §0.2 remains true — the validation runner is a separate, later,
   explicitly-gated task.
2. **`K11`, `K16` and `O6` scope reporting.** Orchestrator-side items, carried
   open; R5 takes no position on their content and closes none of them.
3. **R4 §R4.6's M1–M3 measurement** — the report-only check-11 re-run and the
   mutation harness. R4 itself defines that measurement as a "separate,
   separately-authorized mechanical task" and orders it; R5 neither performs it
   nor changes its terms, its metrics, its pass condition or its output location.
4. **The point-in-time register of §R5.6.** Ordered here, performed elsewhere.

**R4 §R4.2(c)'s deferred structural fix stays deferred.** A typed undertaking
identifier — an `undertaking_ordinal`, or the source's clause identifier as a
typed field — would restore a correct `FAIL` gate on the duration rows. It needs a
new column, a new `spec_version` and a genuinely reissued schema. R5 reissues the
collector instruction **without** adding a column and **without** changing
`spec_version`, so it does not implement that fix, does not begin it, and does not
consume the revision slot R4 reserved for it.

### R5.5 Retroactive application (binding)

1. **R5 applies to validation from the moment its tag is created**, per §R5.7 and
   R4 §7.6. It does not apply to any batch validated before that moment.
2. **`B00_codex_r2`, `B01`, `B02`, `B03` and `B04` collected data does not
   change.** Not one row, not one cell, not one byte. Their sha256 values stand.
   R4 §R4.5 item 2, applied again and not weakened.
3. **No acceptance decision is reopened**, by D1, by D4 or by the register of
   §R5.6. A rule applied correctly under the revision then in force stays applied
   (§7.6 item 6).
4. **No validation report, work note or delivery is deleted, amended or
   reissued.** Corrections are published beside them, additively, never inside
   them.
5. **No row already delivered is re-scope-tagged.** D1 binds collection from its
   tag onward; for delivered rows its only consequence is the derived,
   report-only marking of §R5.1 item 4, which is an observation recorded outside
   `inputs/` and not an edit.
6. **This is not an outcome read.** Collection is a pre-trade phase. Every
   statement in this revision concerns source documents, scope tags, a validation
   key and the text of an instruction. `REALIZED_OUTCOME_READS = 0`.

### R5.6 Ordered task — the point-in-time register (binding)

A derived register of the rows described in §R5.1 item 4 is **ordered**.
Implementation is a separate, separately-authorized mechanical task; this document
orders it, fixes its scope, its output location and its prohibitions, and does
**not** perform it and does **not** state its result. It is a measurement, and
measurements admit nothing (§0.2): it produces no verdict, changes no status and
reopens no acceptance.

**Scope.** The delivered offer-level files of `B03` and `B04`. The selection is
mechanical and carries no judgement: a row qualifies when its `field_name` is
`sector_kap_code`, `sector_kap_label` or `company_name`, its `scope_tag` is
`AS_OF_LISTING`, and its `source_document_type` is `KAP_COMPANY_RECORD`.

**What it records, per qualifying row.** The batch id, ticker, field name,
`source_url`, `source_publication_date`, `retrieval_timestamp_istanbul`, the
`first_trading_date` the repository already holds for that ticker, and the marking
`POINT_IN_TIME_UNVERIFIED` — or, where the retrieval moment is on or before the
first trading date, the §R5.1 item 3 exception, in which case the row is recorded
as **satisfying** the rule and is not marked. It records the sha256 of every
delivery file it reads, so a later reader can verify that no delivery was altered.
It emits `REALIZED_OUTCOME_READS = 0` exactly as any other validator invocation.

**What it must not do.** It must not write under `inputs/`. It must not edit,
re-tag or delete a delivered row. It must not add `POINT_IN_TIME_UNVERIFIED` to
`field_status` or to any other vocabulary. It must not reopen an acceptance, alter
a committed report, or emit a `FAIL`. It must not read any post-listing price,
return, OHLCV row, ceiling event or drawdown for any ticker in scope (§0.4).

**Where it is written.**

```
artifacts/derived/point_in_time_register/
  B03/  B04/                                   # one register file per batch
  POINT_IN_TIME_REGISTER.md                    # the human-readable summary
```

This mirrors the existing `artifacts/derived/check12_revalidation/`,
`artifacts/derived/duration_days/` and `artifacts/derived/check11_revalidation/`
conventions. `inputs/` holds delivered collection bytes and is written by the
collector alone; a derived measurement never enters it.

**The count belongs to that task.** This document deliberately states no row
count, no ticker list and no proportion (§R5.1 item 5). The task measures it on
the bytes and writes it with its own provenance.

### R5.7 Entry into force

R5 does not restate the entry-into-force mechanism. It **refers** to R4 §7.6,
which is binding on every revision including this one, and adds nothing to it.

Applied to this revision, and in §7.6 item 5's required form: **R5 governs every
validation run after the `frozen/collection-spec-r5` tag is created.** Not from a
batch number. Not from this directory's date. Not from the commit that publishes
this text — publishing is not enacting (§7.6 item 2), and between this commit and
that tag, R4 governs and a run in that window is correct under R4.

The tag is created by the operator. The task that wrote this revision did not
create it, did not request it and does not assume it exists: measured at authoring
time, `frozen/collection-spec-r5` was absent from the repository. Until it exists,
this document is a published but un-enacted revision, and R4 is the specification
in force.


---

## Appendix (R5) — provenance of the R5 revision

Read while drafting, all read-only:
`artifacts/governance/BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260909_R4/PRETRADE_EXTENSION_COLLECTION_SPEC.md`
(sha256 `d1c15231fc89a1c2513c843bac9b95e5fd6cb62247a1579bace8614fe845c167`),
`artifacts/governance/spec_clarify_r1/COLLECTOR_INSTRUCTION.md`
(sha256 `d922a819b0bbaed538dcf0755fa7e631a969d9d73c0e68b7c90e94c4fb8d3875`, the
instruction in force under R4, which R4 §R4.4 records as not reissued), and
`artifacts/governance/DECISION_LEDGER.csv`
(sha256 `37cdd4e7295deab2f6968cbe19261a95f8aabbf047fb0a2cf77446e1965a08fc`
before this revision's eleven appended rows).

No file under `inputs/`, `scripts/`, `src/`, `tests/`, `config/`,
`artifacts/predictions/`, `artifacts/live_forecast/` or `artifacts/ipo_master/`
was modified. No delivered batch file was modified. `REALIZED_OUTCOME_READS = 0`.

Re-issued as a full carry-forward revision on 2026-09-12 by
`BORSAI_COLLECTION_SPEC_R5_CARRYFORWARD_20260912_T16`, which read R4 (sha256
`d1c15231fc89a1c2513c843bac9b95e5fd6cb62247a1579bace8614fe845c167`) and the delta
text it replaces (sha256
`b4d5d18cef5bdbb0af43ee8d05808dcec3b6373e80a3fa83d53e0d173f5d5b1a`), took no new
decision, and wrote R4's body into this file with the three amendments §R5 already
declared. `COLLECTOR_INSTRUCTION.md` in this directory was not touched by that
re-issue. `REALIZED_OUTCOME_READS = 0`.

---

## R4. What changed from R3

This section is the revision's own summary. `CHANGELOG_R3_TO_R4.md` carries the
full rationale, the rejected alternatives, the measurement tables and the
line-level difference. R3's own summary of the R2 → R3 revision follows
immediately below, carried forward unchanged, and every `§R3.1` / `§R3.2` /
`§R3.3` cross-reference elsewhere in this document still resolves to it — with
the single amendment §R4.3 makes to `§R3.3` item 1, marked in place.

Three changes, argued independently, published as one revision because they share
one instrument (R1 §6.7 item 3: a new directory, a new tag). Neither of the two
rule changes is a premise of the other, and the effect rule is a premise of
neither.

### R4.1 §8 check 11 — the percentage branch is replaced by base reconstruction (D1)

**Defect (R2/R3).** §8 check 11 compares, per aggregate/leaf family, the **sum of
the printed leaf values** against the **printed aggregate value**, and it applies
that one comparison to all nine of the demand-category numeric fields — six
additive (`applicant_count`, `allocated_investor_count`, `order_count`,
`planned_allocation_shares`, `demand_nominal`, `distributed_nominal`) and three
percentages (`planned_allocation_pct`, `demand_share_pct`, `distributed_pct`).

For the additive fields the comparison is the one the source asserts, and it
holds: **24 comparisons evaluated over `B00_codex_r2`…`B04`, 0 divergences.**

For the percentage fields the comparison is one **the source never asserts**. A
printed percentage is `round(part ÷ whole × 100)` at the cell's own precision;
the source rounds each cell independently and claims nothing about the sum of the
rounded parts. Check 11 evaluates `round(a) + round(b)` against `round(a + b)`,
which are different quantities whenever the two fractional remainders carry past
half an ulp. **13 percentage comparisons evaluated, 4 divergences, every one of
them exactly one unit in the last place** — the maximum a single rounding step can
produce — and every one reproducible from the delivered bytes. `B03` EKOS, the
worked case, at the `Toplam` row's `distributed_nominal` base of 60,000,000 and
the cells' own 4-dp precision:

```
leaf 1  116,488 / 60,000,000 × 100 = 0.1941466…  → 0.1941   (printed 0.1941)
leaf 2       19 / 60,000,000 × 100 = 0.0000316…  → 0.0000   (printed 0.0000)
agg    116,507 / 60,000,000 × 100 = 0.1941783…  → 0.1942   (printed 0.1942)

sum of printed leaves      = 0.1941 + 0.0000 = 0.1941   ← what check 11 compares
round(sum of exact leaves) = round(0.1941783…) = 0.1942  ← what the source printed
```

So the check's percentage branch fires on an arithmetic identity failure that is
guaranteed by construction and is not a data defect. It fired four times in five
batches (`B00_codex_r2` ALBTN, `B01` MHRGY, `B02` MARBL, `B03` EKOS) and was
disposed of three times with the same rationale before the fourth occurrence was
recorded at all. `DECISION_LEDGER.csv`'s third-waiver rule was therefore already
satisfied on the count alone. A gate whose every firing is correctly labelled
harmless stops being read, and R3 §R3.1 already stated that principle when it
closed the same failure mode on check 12.

**What R3 said, and what is new.** R3 §R3.1 declares under "Why check 11 is not
touched" that `AGGREGATE_LEAF_DIVERGENCE` "**is** source-side rounding … That
label was correct, the check is behaving as designed." Nothing here contradicts
that: the label was correct and the check is behaving as designed. This revision
acts on evidence R3 did not have — the third and fourth instances, the 4/13
percentage-versus-0/24 additive split, the per-cell reconstruction over the whole
delivered surface, and the coverage measurement below. A correct label on a
finding is not a reason to keep a comparison the source does not make.

**Change.** Check 11 splits into two branches. The full replacement text is §8
check 11; nothing else in §8 is touched by this change.

| | R2/R3 check 11 | R4 check 11 |
|---|---|---|
| additive fields (6) | leaf sum vs. printed aggregate, at the aggregate cell's precision | **unchanged**, same rule code `AGGREGATE_LEAF_DIVERGENCE`, still a violation |
| percentage fields (3) | sum of printed leaves vs. printed aggregate | each printed cell reconstructed from **its own nominal ÷ the ticker's percentage base**, at the cell's own printed precision; new rule code `PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH`, a violation |
| base absent or ambiguous | n/a | `uncheckable`, counted, **never "passed"** |
| own nominal not numeric | implicitly folded into a family sum | `uncheckable`, counted, **never "passed"** |

**(a) Where the nominal and the base live.** Both are columns of the same
demand-category row, from §2.2's 15 data fields and §5.5's 31-column file. The
pairing is the schema's own and is not invented here:

| percentage field | its nominal, same row | base row's nominal |
|---|---|---|
| `planned_allocation_pct` | `planned_allocation_shares` | `planned_allocation_shares` of the base row |
| `demand_share_pct` | `demand_nominal` | `demand_nominal` of the base row |
| `distributed_pct` | `distributed_nominal` | `distributed_nominal` of the base row |

The **percentage base row** for a `(batch_id, ticker, percentage field)` is the
row of that ticker for which, in **that** percentage field, `category_level =
AGGREGATE`, `is_aggregate = TRUE`, and the printed cell parses as a plain decimal
equal to `100` at its own precision. It is the row the source itself designates as
the whole, by printing the whole. The rule **never reads a category label**:
across `B00_codex_r2`…`B04` every base row happens to be labelled `Toplam` or
`TOPLAM`, and keying on that string would make a `FAIL` gate depend on a free-text
transcription choice — the fragility
`BORSAI_DURATION_DERIVATION_1TO1_RULING_20260908_T11.md` §3.4 named and the reason
§R4.2's option (i) is rejected below. Measured over the five deliveries: **57 of
57** `(ticker, percentage field)` groups that contain any numeric percentage cell
have **exactly one** such row; 0 have none; 0 have more than one; all 57 are
`AGGREGATE` / `TRUE`.

**(b) What is compared with what, and is the rule the same for both branches?**
**Different, deliberately.** The additive branch compares **rows to rows** — a
sum of leaf cells against an aggregate cell — because that is an equality the
source asserts and the schema's `AGGREGATE`/`LEAF` nesting expresses. The
percentage branch compares **a cell to itself** — each printed percentage against
the quotient of its own nominal and the base nominal — because that, and only
that, is what a printed percentage claims. The percentage branch no longer uses
the family relation at all: it needs no `source_parent_label`, and it therefore
evaluates every ticker, including the ones whose leaves declare no parent.

**(c) When the nominal or the base is `DATA_NOT_FOUND`.** The cell is
`uncheckable`. It is counted in the coverage breakdown and it is **never reported
as a pass and never as a divergence**. Three buckets, mirroring R3 check 12's
treatment of a suppressed pairing:

- `no_unique_percentage_base` — zero or more than one base row for that
  `(ticker, percentage field)`: every percentage cell of that field for that
  ticker is uncheckable;
- `percentage_base_nominal_unusable` — the base row exists but its own nominal is
  not a plain decimal, or is zero: same consequence;
- `cell_nominal_not_numeric` — the base is usable but this row's own nominal is
  `DATA_NOT_FOUND`, `SOURCES_CONFLICT`, `NOT_APPLICABLE` or otherwise unparsable:
  this one cell is uncheckable.

This is R3 §1.4's ruling applied identically, and it is the honest degradation:
the check must not report a narrower surface as a cleaner one.

**Coverage, measured over the five delivered batches.** 245 numeric percentage
cells exist. 57 of them are base cells, which reconstruct to `100` by construction
and are reported separately rather than counted as checks. 1 is uncheckable
(`cell_nominal_not_numeric`). **187 cells are checked and 187 reproduce their
printed value exactly**, at each cell's own precision — 0 mismatches, in a run
that is not a fit: no tolerance, no threshold and no free parameter was chosen to
make it pass. (`BORSAI_SPEC_7_3_CHECKPOINT_20260909_T13.md` §3a reports "93 of 93"
for the same property; that figure is the `distributed_pct` subset — 118 checked
cells less 25 base cells. This revision measures all three percentage fields:
`distributed_pct` 93, `planned_allocation_pct` 47, `demand_share_pct` 47.)

**Discriminating power: what the two definitions can see.** Of the 245 numeric
percentage cells, R2/R3's percentage branch has **39** inside any comparison at
all — 13 family comparisons, each touching one aggregate cell and its leaves.
R4's percentage branch checks **244** of them, of which 187 non-trivially. The
gap is structural, not incidental: check 11's family requires a `LEAF` row that
names an `AGGREGATE` row's `source_category_label` in its own
`source_parent_label`, and **18 of the 25 tickers in `B00_codex_r2`…`B04` have no
such row** — their leaves carry `source_parent_label = DATA_NOT_FOUND`. For those
18 tickers R2/R3's check 11 evaluates **zero** comparisons on any field. R4's
percentage branch evaluates all of them.

**One cell of coverage is lost, and it is named.** `B00_codex_r2` ALBTN,
`Yurt Dışı Yatırımcı / - Kurumsal Yatırımcı`, prints `distributed_pct = 0.00`
while its `distributed_nominal` is `DATA_NOT_FOUND`. R2/R3 folded that cell into a
family sum that happened to match; R4 marks it `uncheckable`. That is the **only**
cell in 245 that moves from covered to uncheckable, it is the correct direction
(never "passed"), and it is reported rather than netted against the 206 newly
covered cells.

**(d) When R4's check 11 produces a `FAIL`.** Three directional conditions, each
stated as a defect the check must catch, each anchored in delivered bytes.

1. **A mistyped percentage cell.** `B03` AGROT, `Yurt İçi Kurumsal Yatırımcılar`:
   `demand_nominal = 648,991,222`, base (`TOPLAM`) `demand_nominal = 994,250,802`,
   printed `demand_share_pct = 65.27`. Reconstruction: 648,991,222 ÷ 994,250,802
   × 100 = 65.2745… → `65.27` → pass. Had the collector written `6.53`, or any
   other value, the reconstruction disagrees and the check raises
   `PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH`, a violation.
2. **A mistyped nominal, invisible to R2/R3.** Same cell, same ticker: had the
   collector dropped a digit and written `demand_nominal = 64,899,122` beside the
   printed `65.27`, the reconstruction is `6.53 ≠ 65.27` and R4 fires. **R2/R3
   cannot fire here at all**: AGROT's two `LEAF` rows carry
   `source_parent_label = DATA_NOT_FOUND`, no leaf names the `TOPLAM` aggregate as
   its parent, so check 11 forms no family and evaluates nothing for this ticker.
   This is measured, not hypothesised — AGROT is one of the 18.
3. **A mistyped base, and two compensating errors.** If a ticker's base nominal is
   wrong, every non-base cell of that ticker and field mismatches simultaneously —
   a ticker-wide firing pattern that is itself diagnostic of which cell is wrong.
   And two leaf percentage errors that cancel inside a family (`+0.0010` on one
   leaf, `−0.0010` on another) leave the family sum intact and are invisible to
   R2/R3; under R4 both cells fire independently.

A check that can never `FAIL` is not a gate. This one can, on all three
conditions, and §R4.6 orders that its power be demonstrated against deliberately
corrupted copies rather than asserted.

**(e) What becomes of the four recorded divergences.** Each was recomputed from
the delivered bytes under the new definition, individually:

| # | batch / ticker | family and field | R2/R3 | under R4 |
|---|---|---|---|---|
| 1 | `B00_codex_r2` ALBTN | `Yurt İçi Yatırımcı`, `distributed_pct` 99.84 vs. leaf sum 99.83 | divergence | **dissolves.** Base `Toplam` `distributed_nominal` = 70,000,000. 69,885,336 → 99.84 ✓; 66,094,850 → 94.42 ✓; 3,790,486 → 5.41 ✓. Separately, and in the *other* ALBTN family, the `- Kurumsal Yatırımcı` cell above becomes `uncheckable`. |
| 2 | `B01` MHRGY | `Yurt İçi Yatırımcı`, `distributed_pct` 99.82 vs. 99.81 | divergence | **dissolves.** Base = 207,000,000; all 7 MHRGY percentage cells reconstruct exactly. |
| 3 | `B02` MARBL | `Yurt İçi Yatırımcı`, `distributed_pct` 99.8037 vs. 99.8036 | divergence | **dissolves.** Base = 58,976,404; all 7 MARBL percentage cells reconstruct exactly. |
| 4 | `B03` EKOS | `Yurt Dışı Yatırımcılar`, `distributed_pct` 0.1942 vs. 0.1941 | divergence | **dissolves.** Base = 60,000,000; all 7 EKOS percentage cells reconstruct exactly (worked above). |

"Dissolves" is not "waived". None of the four is reclassified as an acceptable
defect. In each case a comparison the source never asserted is replaced by one it
does assert, and the delivered bytes satisfy the second exactly. The additive
comparison for the same four families is unchanged and remains clean: the leaf
`distributed_nominal` values sum to the aggregate with zero residue in all four.

**Why this is not a weakening.** It removes four false positives and adds 206
cells of evaluated surface; it makes a single mistyped percentage or nominal
catchable where the family check could only see an error that happened to break a
family sum; it keeps the additive branch, which is where a transcription error in
a count or a share quantity would actually show, exactly as it was; and it
degrades to `uncheckable`, never to `pass`, on every input it cannot evaluate.
R3 narrowed check 12's surface and gained power; R4 widens check 11's and gains
power. Both are the right way round for their respective defects.

**Catch-rate hypothesis, stated before implementation.** Measured catch rate of
the new percentage branch on delivered data: **0 in 187 checked cells**. Over
`B05`…`B16` it will evaluate roughly 450 further percentage cells; at a 0.5 %
collector transcription-error rate the expected yield is **1 to 2 catches**. Its
principal near-term value is the removal of an estimated 8 to 10 forecast false
firings and the 206-cell coverage gain, not a large detection yield. That estimate
is recorded here so it can be scored later rather than reconstructed favourably.

### R4.2 §8 check 8 — the duration clause becomes report-only (D2)

**Defect (R2/R3).** §8 check 8 states four uniqueness keys. Coded literally as
written, over the 1,334 delivered rows of `B00_codex_r2`…`B04`:

| key | file | duplicate excess rows | batches affected |
|---|---|---:|---|
| `(ticker, field_name, scope_tag, source_url)` | offer-level, non-duration | **0** | — |
| `(ticker, field_name, scope_tag, duration_start_reference, undertaking_scope, source_url)` | offer-level, §2.1 #15/#16/#17 | **11** | `B01` 1, `B02` 6, `B03` 0, `B04` 4 |
| `(ticker, normalized_category, source_category_label, source_url)` | demand-category | **0** | — |
| `(ticker, normalized_category, source_category_label, field_name)` | §5.6 register | **0** | — |

All 11 are on `shareholder_lockup_undertaking`. Every one is a row pattern
**§2.1.1 item 2 of this same specification declares correct**. `B01` DMRGD is the
plainest case: one document, one page (`s. 177, §27.3(c)`), one shareholder group,
one anchor (`FIRST_TRADING_DATE`) — and two undertakings, `1 YEARS` not to sell on
exchange and `180 DAYS` not to sell off exchange or transfer. §2.1.1 item 2 says
those are two rows and that they are "never merged, never summed, never reduced".
Check 8's duration key says the two rows share one key and are therefore a
forbidden duplicate. Both texts are frozen; they cannot both be satisfied.

Measured true-positive rate of the duration clause: **0 in 101 duration rows**. It
would `FAIL` 4 of 5 batches, and the contradiction currently blocks implementing
check 8 at all — none of its four keys is enforced today.

**Change.** The duration clause becomes a report-only observation; the other three
keys are unaffected. Full replacement text is §8 check 8.

**(a) What stays a gate and what does not, per file.**

| file | key | R4 severity |
|---|---|---|
| offer-level, rows whose `field_name` is **not** §2.1 #15/#16/#17 | `(ticker, field_name, scope_tag, source_url)` | **`FAIL` gate — unchanged.** `DUPLICATE_ROW_KEY`. Measured 0 excess in 703 offer rows. |
| offer-level, rows whose `field_name` **is** §2.1 #15/#16/#17 | `(ticker, field_name, scope_tag, duration_start_reference, undertaking_scope, source_url)` | **report-only** — `DURATION_ROW_KEY_COLLISION`, informational, never gate-affecting |
| demand-category | `(ticker, normalized_category, source_category_label, source_url)` | **`FAIL` gate — unchanged.** Measured 0 excess. |
| §5.6 cell-status register | `(ticker, normalized_category, source_category_label, field_name)` | **`FAIL` gate — unchanged.** Measured 0 excess. This gate is load-bearing for another provision: §5.6 binding rule 1's "two rows for one cell is a `FAIL` (§8 check 8)" is preserved intact by leaving it alone. |

The rule code is deliberately **not** named "duplicate": the rows it reports are
not duplicates, and a code that called them one would re-import the contradiction
into the report text.

The duration rows are not left unguarded. Two instruments already cover them and
neither is touched: the 1:1 row-preservation counter gate of
`BORSAI_DURATION_DERIVATION_1TO1_RULING_20260908_T11.md` (one output row per input
row; inequality is an error), which no key can weaken; and §8 check 15's existing
`MULTIPLE_UNDERTAKINGS` report item, which already surfaces exactly these rows as
informational and which §2.1.1 item 2 makes the correct treatment.

**(b) Does this resolve the §2.1.1 contradiction, or only make it harmless?**
**Both, in different parts — stated separately rather than blurred.**

*Resolved:* the conflict of **obligations** is genuinely gone. §2.1.1 item 2
obliges the collector to write two rows; the amended check 8 no longer obliges the
validator to reject a batch that contains them. A report asserts nothing about
correctness, so the two provisions can now both be satisfied by the same 11 rows.
That is a real resolution and not a semantic dodge.

*Not resolved:* two things survive, and pretending otherwise would be the easy
lie. First, a **descriptive infelicity** — check 8 is titled "Duplicates" and still
computes a key over rows that are not duplicates; the report will name a
"collision" that is, in every measured instance, correct recording. Second, and
materially, a **lost gate**: a genuine duplicate duration row — the same
undertaking transcribed twice from the same document — is now reported rather than
gated. Measured exposure in the delivered data: 0 in 101 duration rows, and the 11
observed collisions are all distinct-undertaking pairs, verified individually
against their `normalized_value`, `unit` and `verbatim_source_phrase`. That
residual is the price of this change. It is recorded here, not hidden, and it is
the reason (c) exists.

**(c) The deferred structural fix — recorded so the next schema revision does not
miss it.** The only correct resolution puts undertaking identity **in the schema**
instead of inferring it from prose: a typed undertaking identifier on §2.1
#15/#16/#17 — an `undertaking_ordinal` (integer, 1-based, per
`(ticker, field_name, source_url)`, assigned in source reading order), or the
source's clause identifier as a typed field. Added to the key, it makes the
duration clause a correct `FAIL` gate again, with no free text in it.

R4 does **not** implement it, because it is not a validation-rule change. It
requires, at minimum: a 27th offer-level column; a third arm in §8 check 1's
column-count resolution (today 24 for V1, 26 for V2); a new `spec_version` string
and therefore a fork of the §7.4 item 4 merge key — the fork R3
`CHANGELOG_R2_TO_R3.md` §4 argues against; a new collector obligation and hence
the first reissue of `COLLECTOR_INSTRUCTION.md` in the project's history; and a
back-fill or a documented coexistence rule for the 101 duration rows already
delivered under V2. That is a genuine schema revision, and it must be decided as
one.

**Forbidden as an interim substitute.** Extending the duration key with
`page_or_section`, `verbatim_source_phrase` or any other free-text column is
**not** adopted, even though `+ page_or_section + normalized_value + unit` was
measured to leave 0 residual collisions on all 101 rows. Two reasons, both
recorded in `BORSAI_SPEC_7_3_CHECKPOINT_20260909_T13.md` §5.3(i) and reservation
R3: it would make a `FAIL` gate depend on a collector's free-text transcription
choice — a collector writing `§27.3(b)` for both of one person's undertakings
fails the batch, one writing `(b)(1)` and `(b)(2)` passes — and the 0 is fitted to
101 rows across four batches, exactly the kind of number that looks decisive until
the fifth batch.

### R4.3 A revision takes effect at its tag, not at a batch number (D3)

**Defect (R3).** R3 §7.5 item 5 and §R3.3 item 1 bind R3's entry into force to a
**batch number**: "`B03` onward is validated under R3." `DECISION_LEDGER.csv`'s
corresponding `hukum` row says the same. In execution, neither `B03` nor `B04` was
validated under R3: both reports name R2 as acceptance authority and both give the
same ground — R3 was published but not tagged, and therefore not in force.

The repository's own timestamps show the executed practice was right and the
written provision was wrong:

| event | commit / ref | timestamp (Europe/Istanbul) |
|---|---|---|
| R3 directory published | `231c5ef` | 2026-09-08 16:41:54 |
| `B03` validated and accepted under R2 | `2cf9e66` | 2026-09-08 17:57:14 |
| `B04` validated and accepted under R2 | `425cfca` | 2026-09-08 21:20:38 |
| tag `frozen/collection-spec-r3` created | annotated tag | 2026-09-08 21:25:09 |

`B03` was validated 3 h 27 min before the tag existed, `B04` 4 min 31 s before it.
At the moment each validation ran, R3 was not in force under any reading that
requires a tag, and R2 was. Two provisions and one ledger row said otherwise, so
the question R3 §7.5 was explicitly written to make answerable — "which document
validated this batch?" — currently has two answers.

**Change — the effect rule, binding.** It is stated in full as **§7.6**, and in
summary here:

1. **A revision of this specification takes effect at the moment its annotated git
   tag is created, and not before.** Effect is bound to the tag. It is never bound
   to a batch number, a file date, a directory name or a commit that merely
   publishes the text.
2. **A batch is validated under the revision in force at the timestamp its
   validation runs**, and the batch's validation report and JSON record which
   revision that was, by name and by tag.
3. **Publishing is not enacting.** Between a revision's publication commit and its
   tag, the previous revision governs, and a validation run in that window is
   correct under the previous revision.
4. **No revision names a batch number as its effective boundary.** Where a revision
   must say what it applies to, it says "every validation run after this
   revision's tag".
5. **A completed batch is never re-validated because a later revision is tagged**,
   and no acceptance decision is reopened by one.

**Correction of R3 §7.5 item 5, carried in this document.** R3's directory is not
touched — R1 §6.7 item 3 forbids editing a published revision, and no byte under
`..._20260908_R3/` was written by this task. The correction therefore lives here,
and R4's own copies of §7.5 item 5 and §R3.3 item 1 carry it in place, marked:

> **R3 §7.5 item 5, as written:** "`B03` onward is validated under R3 (§R3.3 item
> 1)."
>
> **Corrected under §7.6:** *R3 governs every validation run after the creation of
> the tag `frozen/collection-spec-r3` (2026-09-08 21:25:09 +03). Validation runs
> before that moment — including `B03`'s and `B04`'s — were governed by R2.*

The same correction applies to §R3.3 item 1 and to the `DECISION_LEDGER.csv`
`hukum` row reading "R3 B03'ten itibaren dogrulamaya uygulanir"; that row is
closed by a new appended row, never edited, per the ledger's own superseding
convention.

**Retroactive effect — explicit.** **`B03`'s and `B04`'s validations and
acceptances are valid and are not reopened, re-run or re-verdicted.** They were
correct under the rule actually in force when they ran, and this revision makes
the written rule agree with them rather than the reverse. Their deliveries,
hashes, reports, JSONs and ledger acceptance rows stand unchanged. The measured
substantive consequence of the ambiguity is nil for `B03` — its delivered bytes
produce identical validator output under R2 and under R3 — and, for `B04`, R2 was
the stricter of the two readings, so applying it conceded nothing.

**R4's own effect.** R4 governs every validation run after the creation of its
own tag. Until that tag exists, **R3 governs**, and this document has no force
over any validation — including the measurement §R4.6 orders, which is report-only
by construction and changes no verdict either way. Suggested tag name:
`frozen/collection-spec-r4`. Tagging is the operator's action, not this task's.

### R4.4 What this revision does not do

R4 changes **exactly three things**: the definition of §8 check 11's percentage
branch, the severity of §8 check 8's duration clause, and the rule by which a
revision takes effect. Two are report-and-gate rules inside the deterministic
validator; one is a governance provision about this document's own force. None is
a schema, a field, an enum or an instruction to a collector.

Specifically, and bindingly, R4 does **not** change:

| Unchanged | Where |
|---|---|
| The spec version string `PRETRADE_EXT_COLLECTION_SPEC_V2` | header, §5.3 col. 24, §7.4 |
| Offer-level column **count (26)** and column **order**, and every column meaning | §5.3 |
| Demand-category column count (31) and order; cell-status register (9) and order | §5.5, §5.6 |
| Every enum list — inherited and this document's own. R4 extends none and reads none it did not already read | §1.6 |
| The 22 offer-level field names and the 15 demand-category data fields | §2.1, §2.2 |
| Every collector obligation, and `COLLECTOR_INSTRUCTION.md`, which is **not** reissued | §2.1.1, §4, §9 |
| §2.1.1 item 2 itself — two undertakings remain two rows; D2 changes the validator's response to them, never the recording rule | §2.1.1 |
| f3 semantics and every total-demand column | §2.3 |
| The source document hierarchy, the tiers and the document families | §3 |
| The conflict, absence and timestamp rules | §4 |
| The calibration set, method, blindness rule and acceptance gates | §6 |
| The **frozen batch table** and the batch protocol | §7.2, §7.3 |
| §8 check 12 — R3's filter-aware definition stands verbatim, every step, every rule code and every coverage bucket | §8 check 12 |
| §8 checks 1–7, 9, 10, 13–17, and the §8 report shape | §8 |
| Every standing prohibition | §9 |
| Any target definition, feature set, fold protocol, preprocessing step, training-eligibility rule, decision rule, gate threshold, preregistration, benchmark or scientific primitive | outside this document |

**The two carried-forward sentences that R4 does amend, declared rather than
buried.** R3 carried its predecessor's text forward verbatim; R4 does the same
with exactly two exceptions, both the same provision expressed twice, both
required by D3 and both marked in place in the text below:

1. **§7.5 item 5** — "`B03` onward is validated under R3" → the tag-based
   formulation of §7.6.
2. **§R3.3 item 1** — "R3 applies to validation from `B03` onward" → the same.

Leaving them unamended would have left this document asserting, in its own §7.5
and §R3.3, a rule its own §7.6 contradicts. R3's directory is untouched: both
sentences stand unedited there, and the amendment exists only in R4's copy.
A third mechanical edit, also declared: §0.3's precedence chain gains R4 — "where
R4 is silent, R3 governs" — exactly as R3's own §0.3 gained R3.

**Why three changes are safe to publish mid-collection.** All three are validation
and governance rules, not collection rules. Because the schema does not move, §8
check 1's column-count resolution is undisturbed and `spec_version` continues to
key every merge (§7.4 item 4). A batch already being collected is **not** affected:
the same bytes that satisfy R2 and R3 satisfy R4, no collector is asked to re-read
a document, re-open a source or re-code a row, and nothing collected is
invalidated. Collection still admits nothing (§0.2).

**On publishing three changes in one revision.** R3 held to a one-change
discipline and said so. R4 does not, and the reason is stated rather than assumed:
the three share one instrument (a new directory and a new tag), they are
independent in substance — none is a premise of another, and each is argued and
measured on its own evidence — and splitting them would produce three tags in one
day, which under D3's own rule would create three separate moments of entry into
force and three windows in which "which revision governs?" has a different answer.
Each change carries its own `§R4` subsection, its own measurement and its own
ledger row, so a later reader can accept or reject any one of them without
reference to the other two.

### R4.5 Retroactive application (binding)

1. **R4 applies to validation from the moment its tag is created**, per §7.6. It
   does not apply to any batch validated before that moment.
2. **`B00_codex_r2`, `B01`, `B02`, `B03` and `B04` collected data does not
   change.** Not one row, not one cell, not one byte. Their sha256 values stand.
3. **No acceptance decision is reopened.** `B01`'s and `B02`'s acceptances under
   R2, and `B03`'s and `B04`'s acceptances under R2 (§R4.3), stand. A later
   revision of a validation rule is not grounds to unwind a decision taken
   correctly under the rule then in force — R3 §R3.3 item 3's principle, applied
   again.
4. **No validation report is deleted, amended or reissued.** Every report under
   `artifacts/governance/task_reports/` and its JSON companion stands exactly as
   committed. Corrections are published beside them, additively, never inside them.
5. **The four recorded `AGGREGATE_LEAF_DIVERGENCE` findings are not retroactively
   erased.** They were correctly reported and correctly labelled under the rule
   then in force. §R4.1(e) records what the new definition produces on the same
   bytes; it does not rewrite what the old one produced.
6. **This is not an outcome read.** Collection is a pre-trade phase: there is no
   realized D1/D3/D5/D10 value, no price and no OHLCV row anywhere in a batch
   delivery (§0.4, §8 check 13). Every measurement in this revision compares
   numbers to numbers inside delivered CSVs, or reads commit and tag timestamps.
   `REALIZED_OUTCOME_READS = 0`.

### R4.6 Ordered measurement — report-only re-run and mutation harness (binding)

A report-only re-run of R4's check 11 over the five delivered batches is
**ordered**. Implementation is a separate, separately-authorized mechanical task;
this document orders the measurement, defines its metrics and fixes where it is
written, and does not perform it. It is a measurement and measurements admit
nothing (§0.2); it produces no verdict, changes no status and reopens no
acceptance.

**Scope.** `B00_codex_r2`, `B01`, `B02`, `B03`, `B04`, under both definitions —
`--check11-revision r2` and `--check11-revision r4`, the versioning pattern R3's
check 12 already established.

**Three metrics. "How many divergences disappeared" is only the first of them, and
alone it would be a self-serving number.**

- **M1 — dissolution.** For each of the four recorded `AGGREGATE_LEAF_DIVERGENCE`
  instances (`B00_codex_r2` ALBTN, `B01` MHRGY, `B02` MARBL, `B03` EKOS):
  `DISSOLVED` or `STANDS`, with the reconstruction arithmetic printed at full
  precision beside the printed cell.
- **M2 — coverage delta, both directions, itemised.** The count and the identity of
  every percentage cell that R2/R3 evaluated and R4 marks `uncheckable` (expected:
  exactly one, `B00_codex_r2` ALBTN `Yurt Dışı Yatırımcı / - Kurumsal Yatırımcı`
  `distributed_pct`), and the count of cells newly covered (expected: 206). The
  two are reported separately and are **never netted against each other**: a cell
  that stops being checked is a loss even in a run that gains 206.
- **M3 — catch-power preservation, demonstrated against deliberate corruption, not
  asserted.** The question is not how many findings vanished but whether the new
  definition still catches a real error the old one caught. Mutated copies of the
  delivered CSVs are generated — **one mutation per copy, written under
  `artifacts/derived/`, never under `inputs/`** — and each must produce the stated
  verdict:

  | # | mutation | R2/R3 check 11 | R4 check 11 must |
  |---|---|---|---|
  | 1 | `B03` EKOS leaf `distributed_pct` `0.1941` → `0.1841` | fires | **fire** (`PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH`) |
  | 2 | `B03` EKOS aggregate `distributed_pct` `99.8058` → `99.8085` | fires | **fire** |
  | 3 | `B03` AGROT `demand_nominal` `648991222` → `64899122` | silent — AGROT forms no family | **fire** |
  | 4 | `B01` MHRGY leaf `distributed_nominal` `30700` → `30070` | fires (additive branch) | **fire** (additive branch, unchanged) |
  | 5 | `B02` MARBL base `Toplam` `distributed_nominal` `58976404` → `58967404` | silent | **fire on every non-base `distributed_pct` cell of MARBL** |
  | 6 | `B03` EKOS two compensating leaf `distributed_pct` errors, `+0.0010` and `−0.0010` | silent — family sum preserved | **fire on both cells** |
  | 7 | `B01` DMRGD duration row duplicated exactly (a genuine duplicate) | `FAIL` under check 8 as written | **report** `DURATION_ROW_KEY_COLLISION` and **not** `FAIL` — this is D2's residual, measured rather than described |

  **Pass condition:** mutations 1–6 all fire under R4. Mutations 3, 5 and 6 are the
  cases R2/R3 misses and are the demonstration that the widening is real. Mutation
  7 records D2's cost. **Any mutation that R2/R3 catches and R4 misses is a capture
  regression and blocks the implementation** — it is reported, not waived, and the
  revision returns to the operator.

**Output location — under `artifacts/derived/`, never under `inputs/`:**

```
artifacts/derived/check11_revalidation/
  B00_codex_r2/  B00_codex_r2_check11_r4_recheck.json
                 B00_codex_r2_check11_r4_recheck.csv
  B01/  B02/  B03/  B04/        # same two files per batch
  mutation_harness/
    check11_r4_mutation_results.json     # one entry per mutation, both revisions
    mutants/                             # the corrupted copies, one per mutation
  CHECK11_R4_DIVERGENCE_RESOLUTION.md
```

This mirrors the existing `artifacts/derived/check12_revalidation/` and
`artifacts/derived/duration_days/` conventions. `inputs/` holds delivered
collection bytes and is written by the collector alone; neither a derived
measurement nor a mutant ever enters it.

The JSON carries, per batch: the pre-R4 and post-R4 rule-code counts, the check-11
coverage breakdown under both definitions with every bucket of §8 check 11 named,
the per-cell reconstruction table, and the **sha256 of every delivery file read** —
so a later reader can verify no delivery was altered to produce the improvement.
The CSV carries one row per evaluated percentage cell.
`CHECK11_R4_DIVERGENCE_RESOLUTION.md` states, per recorded divergence, `DISSOLVED`
or `STANDS` with the reason, reports M2 in both directions, and reproduces the M3
table with actual outcomes beside the required ones.

`REALIZED_OUTCOME_READS = 0` must be emitted by the re-run exactly as by any other
validator invocation.

---

## R3. What changed from R2

This section is the revision's own summary. `CHANGELOG_R2_TO_R3.md` carries the
full rationale, the rejected alternatives and the line-level difference. R2's own
summary of what it changed from R1 follows immediately below, carried forward
unchanged, and every `§R.1` / `§R.2` / `§R.3` cross-reference elsewhere in this
document still resolves to it.

### R3.1 §8 check 12 becomes `total_demand_filter_status`-aware

**Defect (R2).** §8 check 12 compares **both** demand-share numerators — §2.1 #1
`demand_shares_unfiltered` and #2 `demand_shares_filtered` — against the source's
published #4 `total_demand_multiple_value`, and consults §2.1 #5
`total_demand_filter_status` at no point. But #5 is precisely the field that
records **which** numerator the source divided by. Where a source states
"halka arzda toplam **filtre edilmemiş** veriler baz alındığında … satışa sunulan
adedin 4,4 katına denk gelen 75.075.992 pay" and the collector correctly records
#5 = `UNFILTERED`, the published 4,4 is a statement about #1 alone. Dividing #2 by
#3 and finding 4,3 is not a divergence between the source and the collector; it
is the arithmetic difference between two different numerators, one of which the
source never claimed to have used.

The consequence is not noise but a **systematic false positive**: the check fires
on every ticker whose source says `UNFILTERED` and whose collector recorded both
numerators. It fired on DOFER in `B01` (4.33 vs. 4.4) and, in the mirror-image
shape, on MARBL in `B02` (1.78 vs. 1.81, where the designated `UNFILTERED`
numerator was not published at all and only the filtered one was recorded). Both
were waived as "expected findings — source-side rounding", which was the wrong
label for a definitional difference and is corrected additively in
`artifacts/governance/BORSAI_LABEL_CORRECTION_20260908_T11.md`. A gate that
produces a predictable false positive teaches its readers to waive it, and a gate
that is routinely waived has stopped being a gate. That is the defect this
revision closes — not the arithmetic, which was always right.

**Change.** §8 check 12 reads #5 before comparing, compares only the numerator #5
designates, and reports the rest as coverage rather than as divergence. The full
replacement text is §8 check 12; nothing else in §8 is touched. Four new outcomes
are defined there, of which two are gate-affecting (`ARITHMETIC_CONSISTENCY_
DIVERGENCE`, retained and narrowed; `FILTER_STATUS_MULTIPLE_CONTRADICTION`, new)
and two are report-only (`ARITHMETIC_CONSISTENCY_NOT_COMPARABLE`,
`ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER`).

**Why this does not weaken the check.** R2's check 12 could not distinguish a
collector transcription error on the numerator the source used from a definitional
difference on a numerator the source did not use — both produced one rule code. R3
separates them, so a firing of `ARITHMETIC_CONSISTENCY_DIVERGENCE` is now
actionable by construction. And R3 **adds** a gate condition R2 had none for: a
`total_demand_filter_status` that contradicts the presence or absence of a
published multiple, which the C1 ruling
(`artifacts/governance/spec_clarify_r1/CLARIFICATION.md` §1) makes an internal
inconsistency. The check's evaluated surface narrows; its discriminating power
increases.

**Why check 11 is not touched.** The companion finding in both batches,
`AGGREGATE_LEAF_DIVERGENCE` (MHRGY 99.82 vs. 99.81, MARBL 99.8037 vs. 99.8036),
**is** source-side rounding: the aggregate percentage and the leaf percentages are
each rounded independently at the source, and the corresponding `demand_nominal`
figures sum exactly. That label was correct, the check is behaving as designed,
and R3 changes nothing in it.

### R3.2 What this revision does not do

R3 changes **exactly one thing**: the definition of §8 check 12. It is a
report-and-gate rule inside the deterministic validator. It is not a schema, not
a field, not an enum and not an instruction to a collector.

Specifically, and bindingly, R3 does **not** change:

| Unchanged | Where |
|---|---|
| The spec version string `PRETRADE_EXT_COLLECTION_SPEC_V2` | header, §5.3 col. 24, §7.4 |
| Offer-level column **count (26)**, column **order**, and every column meaning | §5.3 |
| Demand-category column count (31) and order; cell-status register (9) and order | §5.5, §5.6 |
| Every enum list — inherited and this document's own, `total_demand_filter_status` included, which R3 reads but does not extend | §1.6 |
| The 22 offer-level field names and the 15 demand-category data fields | §2.1, §2.2 |
| Every collector obligation, and `COLLECTOR_INSTRUCTION.md`, which is not reissued | §2.1.1, §4, §9 |
| f3 semantics and every total-demand column | §2.3 |
| The source hierarchy and document families | §3 |
| The conflict, absence and timestamp rules | §4 |
| The calibration set, method and acceptance gates | §6 |
| The frozen batch table and the batch protocol | §7.2, §7.3 |
| §8 checks 1–11 and 13–17, and the §8 report shape | §8 |
| Every standing prohibition | §9 |
| Any target definition, feature set, fold protocol, preprocessing step, training-eligibility rule, decision rule, gate threshold, preregistration, benchmark or scientific primitive | outside this document |

**Why one change is safe to publish mid-collection.** Check 12 is a validation
rule, not a collection rule. Because the schema does not move, §8 check 1's
column-count resolution (24 for a V1 row, 26 for a V2 row) is undisturbed and
`spec_version` continues to key every merge (§7.4 item 4). A batch already being
collected under R2 is therefore **not** affected: the same bytes that would have
satisfied R2 satisfy R3, and no collector is asked to re-read a document, re-open
a source or re-code a row. Nothing collected is invalidated. Collection still
admits nothing (§0.2).

### R3.3 Retroactive application (binding)

1. **[AMENDED BY R4 §7.6 — R3's published sentence, then the correction. R3's own
   directory is untouched.]** R3 §R3.3 item 1 as published reads: *"R3 applies to
   validation from `B03` onward. `B03` and every later batch is validated under
   R3's check 12."* Under §7.6 it is corrected to: **R3's check 12 governs every
   validation run after the creation of the tag `frozen/collection-spec-r3`.**
   `B03` and `B04` were validated before that tag existed and were therefore
   governed by R2 (§R4.3).
2. **`B01` and `B02` collected data does not change.** Not one row, not one cell,
   not one byte. Their sha256 values stand.
3. **`B01` and `B02` acceptance decisions are not reopened.** They were accepted
   under R2 with a recorded waiver; a later revision of a validation rule is not
   grounds to unwind a decision taken correctly under the rule then in force.
4. **No validation report is deleted, amended or reissued.**
   `BORSAI_B01_VALIDATE_20260907_V1`, `BORSAI_B01_REVALIDATE_20260907_V2`,
   `BORSAI_B01_REVALIDATE_20260907_V3` and `BORSAI_B02_VALIDATE_20260908_V1`, and
   their JSON companions, stand exactly as committed. The label correction they
   need is published beside them, additively, never inside them.
5. **A report-only re-run of the corrected check 12 over `B01` and `B02` is
   ordered.** Its single purpose is to measure how many of the four recorded
   divergence waivers — `B01` `AGGREGATE_LEAF_DIVERGENCE`, `B01`
   `ARITHMETIC_CONSISTENCY_DIVERGENCE`, `B02` `AGGREGATE_LEAF_DIVERGENCE`, `B02`
   `ARITHMETIC_CONSISTENCY_DIVERGENCE` — survive the corrected rule. Implementation
   is a separate, separately-authorized mechanical task; this document orders the
   measurement and fixes where it is written, and does not perform it.
6. **This is not an outcome read.** Collection is a pre-trade phase: there is no
   realized D1/D3/D5/D10 value, no price and no OHLCV row anywhere in a batch
   delivery (§0.4, §8 check 13). The re-run reads collected pre-trade fields and
   compares numbers to numbers inside one CSV. `REALIZED_OUTCOME_READS = 0` must
   be emitted by the re-run exactly as by any other validator invocation.
7. **Output location — under `artifacts/derived/`, never under `inputs/`:**

   ```
   artifacts/derived/check12_revalidation/
     B01/  B01_check12_r3_recheck.json
           B01_check12_r3_recheck.csv
     B02/  B02_check12_r3_recheck.json
           B02_check12_r3_recheck.csv
     CHECK12_R3_WAIVER_RESOLUTION.md
   ```

   This mirrors the existing `artifacts/derived/duration_days/B01|B02` convention.
   `inputs/` holds delivered collection bytes and is written by the collector
   alone; a derived measurement never enters it. The JSON carries, per batch, the
   pre-R3 and post-R3 rule-code counts, the §8 check 12 coverage breakdown under
   both definitions, and the sha256 of the delivery files it read — so a later
   reader can verify the delivery was not altered to produce the improvement. The
   CSV carries one row per evaluated triple. `CHECK12_R3_WAIVER_RESOLUTION.md`
   states, per waiver, `DISSOLVED` or `STANDS`, with the reason.
8. **The re-run changes no status.** It does not re-verdict `B01` or `B02`, does
   not write into `artifacts/governance/task_reports/`, does not touch
   `artifacts/ipo_master/`, and creates no `OFFICIAL_VERIFIED` or canonical
   value. Its output is a measurement, and measurements admit nothing (§0.2).

---

## R. What changed from R1 — R2's own summary, carried forward verbatim

This section is R2's summary of the R1 → R2 revision. It is reproduced here
unchanged, including its subsection numbering, so that every `§R.1` / `§R.2` /
`§R.3` cross-reference in this document continues to resolve. R3 adds nothing to
it and removes nothing from it; what R3 itself changed is §R3 above.

`CHANGELOG_R1_TO_R2.md` carries the full rationale, the rejected alternatives and
the line-level difference for the two changes described below; it lives in the R2
directory and is not reproduced here.

### R.1 Duration fields — the collector records, the script derives

**Defect (R1).** `price_stability_days`, `issuer_lockup_days` and
`shareholder_lockup_days` are named in days and typed integer, but sources state
these undertakings in years or months. Three consequences, observed in `B00` for
the two lock-up fields and structurally identical for the third:

- (a) the source's own unit could not be recorded — R1's `unit` vocabulary had
  `DAYS` but neither `YEARS` nor `MONTHS`;
- (b) converting to days is forbidden to the collector by §9 item 5, because the
  day count appears in no source (`BORSAI_SPEC_CLARIFY_20260906_T7`, verdict
  `BLOCKED` on exactly this point);
- (c) one scalar is not enough — a single document can carry two undertakings
  with different covered parties and different start references.

The collector's only correct move under R1 was `DATA_NOT_FOUND` +
`SPEC_EDGE_CASE_UNRESOLVED`, which is what it did, and which would have lost both
fields across all 79 rows.

**Change.** The pattern R1 already uses twice — the collector records what the
source states, a deterministic script assigns the derived value (§1.7 for
`publication_timing_status`, §2.3 item 5 for `total_demand_multiple_origin`) — is
extended to duration fields. It is extended, not reinvented; no new mechanism is
created.

1. `unit` gains `YEARS` and `MONTHS` (§5.3). `unit` is this document's own
   vocabulary, defined in R1 §5.3 and not inherited from
   `config/ipo_master_schema.toml` or `_v2.toml`, so no config file, canonical
   schema or frozen artifact is touched by the extension.
2. Three new collector-written offer-level fields replace the three demoted
   ones: `price_stability_undertaking`, `issuer_lockup_undertaking` and
   `shareholder_lockup_undertaking` (§2.1 #15, #16, #17). The magnitude goes in
   `normalized_value`, the source's own unit in `unit`, the printed text in
   `raw_value` and `verbatim_source_phrase`.
3. Two new offer-level columns, `duration_start_reference` and
   `undertaking_scope` (§5.3 columns 25 and 26), make two undertakings of the
   same type distinguishable rows rather than one flattened cell.
4. `price_stability_days`, `issuer_lockup_days` and `shareholder_lockup_days`
   become **script-derived** and are **never written by the collector** (§5.4,
   §9 item 11). They leave the collector's field list entirely.
5. The conversion constant is deliberately **not stated in this document**. It
   lives in the derivation script and is versioned there (§5.4.1). A
   specification that hardcoded a day-count convention would freeze a
   commercial convention as if it were arithmetic.

Offer-level collector field count is unchanged at 22: −3 demoted, +3 added.

`price_stability_days` was brought under the same pattern in
`BORSAI_COLLECTION_SPEC_R2_FINALIZE_20260906_T9A`, before R2 was tagged and
before any batch was collected under it. It is the **same defect in the same
shape** — a field named in days whose source may state months — and it is closed
by replicating the rule set above, not by designing a second one. See
`CHANGELOG_R1_TO_R2.md` §1.6.

### R.2 Demand-category cell status and search scope

**Defect (R1).** The 31-column demand-category CSV has no `search_scope` column,
while §4.4 requires a non-empty search scope on every `DATA_NOT_FOUND`; and it
carries one row-level `field_status` for 15 data fields that can genuinely differ
in status. Both gaps were already known and recorded as open items; the
measurement in `BORSAI_SPEC_CLARIFY_20260906_T7` found **every** category row of
the `B00` delivery affected, with more than one field driving it, so the exposure
is structural rather than marginal.

**Change.** A third per-batch file, the **demand-category cell-status register**
(§5.6), carries one row per data cell that is not a plainly recorded value. The
31-column demand-category CSV is **unchanged, column for column**, so its
comparability with the existing canonical demand-category file — and therefore
the calibration already performed against it — is untouched.

### R.3 What this revision does not do

It does not change: any target definition, feature set, fold protocol,
preprocessing step, training-eligibility rule, decision rule, gate threshold, or
any preregistration, benchmark or scientific primitive. It does not change f3
semantics (§2.3), the source hierarchy (§3), the conflict rules (§4), the
calibration gates (§6.6), the batch table (§7.2), or `order_count`'s in-scope
status. Collection still admits nothing (§0.2).

---

## 0. Scope, precedence, and what this document does NOT do

### 0.1 What it is

An executable collection instruction for the project orchestrator (ChatGPT), who
owns external web research under `CLAUDE.md` §4A. It specifies, for the **79
"thin" rows** of `HISTORICAL99_FROZEN_COHORT_V1`: which fields to collect, what
each field means, which document each comes from, what to do on conflict, what to
write when a field genuinely does not exist, the exact output schema, the
calibration set that measures collection reliability, and the batch plan.

### 0.2 What it is NOT

- It is **not** an authorization to modify any existing repository file.
- It is **not** a model, feature-set, preregistration or target change. Collecting
  a field admits it to **nothing**. Every field named here is, as of this
  document, either already-canonical or explicitly `NOT_A_V2_FEATURE` in the
  frozen V2 preregistration candidate. Admission of any collected field into any
  model requires a separate, later, explicitly-gated preregistration.
- It is **not** a promotion path. Nothing collected under this spec is
  `OFFICIAL_VERIFIED`, `CANONICAL`, `HISTORICAL99`, `TRUE_LIVE` or
  `PRODUCTION_AUTHORITY` by virtue of having been collected.
- It defines **no new code, no new capability, no new authorization mechanism, no
  new nonce or reservation object**. The validation runner described in §8 is a
  separate, later, explicitly-gated task. The duration-derivation step described
  in §5.4.1 is likewise a **requirement on a later, separately-authorized task**,
  not code written or authorized here, and not a licence for anything to run.
  Until those tasks exist this document is a binding *specification*, not a
  running system.

### 0.3 Precedence

Additive and subordinate. Where this document appears to conflict with any of the
following, the following governs and this document is the one that is wrong:

- `CLAUDE.md` — all sections, in particular §4 (official source priority), §4A
  (shadow / external evidence governance), §5 (FULL20 EOD source rule), §8
  (immutability), §10 (200/200 modeling gate), §12 (leakage), §22 (existing
  pipeline first), §24 (internet safety), §31 (failure rules).
- `config/ipo_master_schema.toml` and `config/ipo_master_schema_v2.toml`.
- `artifacts/ipo_master/ipo_demand_category_schema.md`.
- Any frozen preregistration, benchmark, analysis protocol or scientific
  primitive — in particular the frozen V1.5 f3 contract (§2.3 below).
- `artifacts/governance/BORSAI_PROSPECTIVE_SCORING_PROTOCOL_20260906_R1/`.

Identity of this revision is its git commit hash plus the annotated tag the
operator applies to it. No authority-hash manifest is maintained; the commit is
the identity. R1's identity — its own commit plus `frozen/collection-spec-v1` —
is unaffected and continues to identify the state `B00` was collected under, and
R2's identity likewise continues to identify the state `B01`, `B02`, `B03` and
`B04` were validated under (§7.6 item 8). A revision's tag is not merely part of
its identity: under §7.6 it is the moment the revision takes effect.

This revision is additionally subordinate to its predecessors in one direction: where R6 is silent, R5 governs, where R5 is silent, R4 governs, where R4 is silent, R3 governs, where R3 is silent, R2 governs, and where R2 is silent, R1 governs — because each revision carries its predecessor's text forward verbatim except in the places its own `§R` names (three places for R6, three for R5, three for R4, one for R3, two for R2). No revision relaxes a prohibition of the revision before it.

### 0.4 Outcome firewall, binding on the collector

The collector **must not** read, request, transcribe or reason about any
post-listing price or return for any ticker in scope: no D1/D3/D5/D10 value, no
open/high/low/close, no ceiling (`tavan`) event, no drawdown, no THB/THM content,
no `artifacts/outcomes/` value. Every field in §2 is, by construction, a
**pre-first-trade or offer-result** fact published before or at listing.

If a source document a collector opens also contains post-listing price data (a
broker page, a news article, a data terminal screen), only the offer-result
figures are transcribed; the price data is not recorded, not quoted in
`verbatim_source_phrase`, and not used to sanity-check anything.

---

## 1. Existing schema inventory (read from the repository, 2026-09-06)

This section is the factual base the rest of the document sits on. Nothing here
was invented; every count was read from the files named.

### 1.1 Cohort split: 79 thin vs 20 dense

`artifacts/ipo_master/historical99/HISTORICAL99_FROZEN_COHORT_V1/canonical/HISTORICAL99_FROZEN_COHORT_V1_canonical_membership.csv`
(99 rows, 15 columns) splits the cohort by `membership_source`:

| `membership_source` | rows | meaning |
|---|---|---|
| `CANONICAL20_PROTECTED_INPUT` | 20 | the FULL20 / batch-01..04 tickers, densely collected |
| `VERIFIED_FINAL_EXTERNAL_ACQUISITION_EVIDENCE` | 79 | the thin rows, in scope for this spec |

All 99 rows carry `historical_anchor = QUICK`,
`membership_gap_status = DEFERRED_RECONCILIATION`,
`canonical_status = HISTORICAL99_PRETRADE_CANONICAL_FROZEN`.

The 20 dense tickers (`first_trading_date` ascending): ATATR, EMPAE, GENKM,
SVGYO, LXGYO, MCARD, AAGYO, EKDMR, BETAE, ORZAX, GOLDA, EKIM, ISVEA, SSAAT,
SARAE, METEN, ALBTN, MASFN, KARCL, QUICK.

The 79 thin tickers are listed in §7.2, in frozen batch order.
Their `first_trading_date` range is 2023-09-22 … 2026-07-06.

### 1.2 Master schema

`config/ipo_master_schema.toml` → `master_fields`: **30 columns** (v1).
`config/ipo_master_schema_v2.toml` → `master_extension_fields`: **7 columns**
(`applicant_count`, `allocated_investor_count`, `order_count`,
`investor_count_semantic`, `total_demand_multiple_value`,
`total_demand_definition`, `total_demand_filter_status`).
30 + 7 = 37, which is the `v2_normalized_columns: 37` recorded in the existing
batch validation JSONs.

The frozen Historical99 canonical pretrade master carries **38 columns** — those
37 plus `total_demand_multiple_origin`, a Historical99-era provenance label.

### 1.3 Provenance schema

`config/ipo_master_schema.toml` → `provenance_fields`: **12 columns** —
`ticker, field_name, raw_value, normalized_value, source_priority, source_name,
source_url, source_publication_date, available_before_first_trade,
verification_status, conflict_status, notes`.

The Historical99 canonical provenance file is a different, cohort-level file
(22 columns, one row per ticker); it is **not** the per-field provenance shape and
is not extended by this spec.

### 1.4 Demand-category long-form schema

`config/ipo_master_schema_v2.toml` → `[ipo_master_v2.demand_category]`, documented
in `artifacts/ipo_master/ipo_demand_category_schema.md`:
`storage_model = LONG_FORM_ONE_SOURCE_CATEGORY_PER_ROW`, **22 fields**,
`source_category_label_rule = PRESERVE_VERBATIM`,
`no_cross_semantic_conversion = true`, `no_derived_missing_demand_multiple = true`,
`data_not_found_is_not_zero = true`.

Realized instance:
`artifacts/ipo_master/consolidated/ipo_master_20_demand_categories_canonical.csv`
— 81 rows across the 20 dense tickers, 24 columns (the 22 schema fields plus
`conflict_status` and `source_batch`); 70 `LEAF` / 11 `AGGREGATE`.

### 1.5 Filled/empty map — the definition of "thin"

Non-missing cell counts per pretrade-master column, dense group (n=20) vs thin
group (n=79). "Missing" means empty or a `DATA_NOT_FOUND*` sentinel.

| column | n20 | n79 | in scope here |
|---|---|---|---|
| ticker, first_trading_date, ipo_price, shares_offered, capital_increase_shares, existing_share_sale, post_ipo_share_capital, ipo_size_tl, free_float_pct, capital_increase_pct_of_offer, existing_sale_pct_of_offer | 20 | 79 | no — already complete |
| additional_sale_shares | 16 | 79 | no — see §2.5 |
| company_name | 20 | 51 | yes (identity completion only) |
| total_demand_multiple / total_demand_multiple_value | 19 | 78 | **no overwrite** — §2.3 |
| total_demand_definition, total_demand_filter_status, total_demand_multiple_origin | 20 | 79 | **no overwrite** — §2.3 |
| investor_count | 20 | 0 | legacy, not collected — §2.2 |
| applicant_count | 17 | 0 | **yes** |
| allocated_investor_count | 20 | 0 | **yes** |
| order_count | 2 | 0 | **yes** |
| investor_count_semantic | 20 | 0 (all `DATA_NOT_FOUND`) | **yes** |
| retail_demand_multiple | 16 | 0 | **yes**, via category long-form |
| domestic_institutional_demand_multiple | 17 | 0 | **yes**, via category long-form |
| foreign_institutional_demand_multiple | 10 | 0 | **yes**, via category long-form |
| retail_allocation_pct | 17 | 0 | **yes**, via category long-form |
| domestic_institutional_allocation_pct | 17 | 0 | **yes**, via category long-form |
| foreign_institutional_allocation_pct | 10 | 0 | **yes**, via category long-form |
| distribution_method | 20 | 0 | **yes** |
| price_determination_method | 20 | 0 | **yes** |
| lead_broker | 20 | 0 | **yes** |
| price_stability_planned | 20 | 0 | **yes** |
| price_stability_days | 20 | 0 | **not collected directly** — script-derived from `price_stability_undertaking`, §R.1 / §5.4.1 |
| issuer_lockup_days | 20 | 0 | **not collected directly** — script-derived from `issuer_lockup_undertaking`, §R.1 / §5.4.1 |
| shareholder_lockup_days | 20 | 0 | **not collected directly** — script-derived from `shareholder_lockup_undertaking`, §R.1 / §5.4.1 |
| sector | 20 | 0 | **no** — free text, see §2.5 |
| data_completeness_status | 20 (`PARTIAL`) | 79 (`PARTIAL`) | script-assigned |

Demand-category long-form coverage for the 79: **zero rows exist**.

### 1.6 Existing enum vocabularies — reused verbatim, never extended here

**R2 note on the scope of "never extended here".** The rule below binds the
vocabularies **inherited** from `config/ipo_master_schema.toml`,
`config/ipo_master_schema_v2.toml`, the demand-category schema document and the
predecessor collector spec. Every one of those is carried into R2 byte-identical:
R2 extends **none** of them, adds no member to `field_status`, and adds no
member to `total_demand_filter_status`, `investor_count_semantic`,
`normalized_categories`, `category_levels` or any other inherited list.

R2 extends exactly one vocabulary and introduces exactly one new one, and both
are **this document's own**, defined by R1 in its own §5.3 / §2.1 and present in
no config file, no canonical schema and no frozen artifact:

| vocabulary | R1 | R2 | where defined |
|---|---|---|---|
| `unit` | 10 members | **12** — adds `YEARS`, `MONTHS` | §5.3 column 6 |
| `duration_start_reference` | — | **new**, 6 members | §5.3 column 25 |

Extending a vocabulary this document owns is the ordinary business of a revision.
Extending an inherited one would fork a schema shared with the canonical record,
and R2 does not do it.

| enum | source | allowed values |
|---|---|---|
| `verification_statuses` | `ipo_master_schema.toml` | `OFFICIAL_VERIFIED`, `AUTHORIZED_INTERMEDIARY_VERIFIED`, `SECONDARY_VERIFIED`, `DATA_NOT_FOUND`, `SOURCE_CONFLICT` |
| `conflict_statuses` | `ipo_master_schema.toml` | `""`, `NO_CONFLICT`, `SOURCE_CONFLICT` |
| `data_completeness_statuses` | `ipo_master_schema.toml` | `NOT_CALCULABLE`, `PARTIAL`, `COMPLETE`, `SOURCE_CONFLICT` |
| `allowed_boolean_values` | `ipo_master_schema.toml` | `TRUE`, `FALSE` |
| `total_demand_filter_status` | `ipo_master_schema_v2.toml` | `FILTERED`, `UNFILTERED`, `NOT_SPECIFIED`, `NOT_APPLICABLE`, `DATA_NOT_FOUND` |
| `investor_count_semantic` | `ipo_master_schema_v2.toml` | `APPLICANT_COUNT`, `ALLOCATED_INVESTOR_COUNT`, `ORDER_COUNT`, `AMBIGUOUS`, `DATA_NOT_FOUND` |
| `normalized_categories` | `ipo_master_schema_v2.toml` | `RETAIL_DOMESTIC`, `HIGH_APPLICATION_DOMESTIC`, `INSTITUTIONAL_DOMESTIC`, `INSTITUTIONAL_FOREIGN`, `EMPLOYEE`, `RETAIL_FOREIGN`, `OTHER` |
| `category_levels` | `ipo_master_schema_v2.toml` | `LEAF`, `AGGREGATE` |
| `available_before_first_trade` | demand-category schema | `TRUE`, `FALSE`, `UNKNOWN` |
| source priority tiers | `ipo_master_schema.toml` | rank 1 `SPK`, 2 `KAP`, 3 `BORSA_ISTANBUL`, 4 `MKK`, 5 `AUTHORIZED_INTERMEDIARY_OR_CONSORTIUM`, 6 `TRUSTED_SECONDARY` |

Two enums are **not** in the TOML files and are inherited verbatim from
`BorsAi_External_Archive/SPECS/PRETRADE_ACQUISITION_COLLECTOR_SPEC_CORRECTED_20260819.md`
(the accepted, operator-corrected collector architecture spec):

| enum | allowed values |
|---|---|
| `field_status` | `VALUE_RECORDED`, `DATA_NOT_FOUND`, `FIELD_NOT_FOUND_IN_DOCUMENT`, `SOURCES_CONFLICT`, `SCOPE_DIFFERENCE`, `SEMANTIC_DIFFERENCE`, `SEMANTICALLY_AMBIGUOUS`, `SPEC_EDGE_CASE_UNRESOLVED` |
| `publication_timing_status` | `AVAILABLE_PRE_FIRST_TRADE`, `PUBLICATION_TIMING_UNRESOLVED`, `POST_FIRST_TRADE_NOT_ELIGIBLE` |

`VALUE_RECORDED` is the only value in `field_status` not literally present in the
predecessor spec's prose; it is the unmarked "a value was found and is not
ambiguous" case, which that spec expresses as `AUTO_ACCEPT_RAW_PACKET`. It is
named explicitly here because a CSV column cannot be left blank (§4.5).

### 1.7 `publication_timing_status` — existing definition, restated unchanged

From the predecessor collector spec §E, itself derived from
`[ipo_master_v2.temporal_leakage]`:

- `source_publication_date < first_trading_date` (strict) →
  `AVAILABLE_PRE_FIRST_TRADE`.
- `source_publication_date == first_trading_date` with no time-of-day evidence →
  `PUBLICATION_TIMING_UNRESOLVED` (matches
  `same_day_without_pre_open_time_proof = "UNKNOWN"`).
- `source_publication_date > first_trading_date` →
  `POST_FIRST_TRADE_NOT_ELIGIBLE`, unconditionally, regardless of what the
  document's content claims about when the fact became true.
- `source_publication_date` null → `PUBLICATION_TIMING_UNRESOLVED`, plainly, never
  disguised as `SCOPE_DIFFERENCE` or any adjacent state.
- A document's internal signature date is **never** substituted for its
  publication date.
- Later republication of a document is **never** evidence that its content was
  available earlier. Only the earliest confirmed SPK/KAP/BIST appearance counts.

**This status is assigned by the deterministic validation script (§8), never by
the collector.** The collector supplies `source_publication_date` /
`source_publication_time`; the script supplies the status and
`available_before_first_trade`.

### 1.8 File conventions observed in the repository

UTF-8 **with BOM**; CRLF line endings; `,` delimiter; `.` decimal separator; no
thousands separators; dates `YYYY-MM-DD`; booleans `TRUE`/`FALSE` uppercase;
`git config core.quotepath = true`.

---

## 2. Field dictionary

Two tables. **Table 1** is offer-level (one value per ticker per scope). **Table 2**
is the demand-category long form (many rows per ticker), reused unchanged from
the existing schema.

Column meanings: *Status* — `EXISTING` (column already defined in
`ipo_master_schema.toml` / `_v2.toml`; the name is reused verbatim) or `NEW`.
*Normalized type* — what goes in `normalized_value`.

### 2.1 Table 1 — offer-level fields (22)

| # | field_name | Status | Semantic definition (one line) | Normalized type | Primary document (§3) | If genuinely absent |
|---|---|---|---|---|---|---|
| 1 | `demand_shares_unfiltered` | NEW | Total nominal share quantity demanded in the bookbuild **before** any duplicate/ineligibility screen, exactly as the source states it. | decimal, shares/nominal | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 2 | `demand_shares_filtered` | NEW | Total nominal share quantity demanded **after** the source's stated screen (`kabul edilen`, `elenmiş`, `mükerrer ayıklanmış`). | decimal, shares/nominal | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 3 | `shares_offered_denominator` | NEW | The offered-share quantity the **source itself** divided by to reach its published demand multiple. Not necessarily equal to the canonical `shares_offered`. `scope_tag` mandatory. | decimal, shares/nominal | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 4 | `total_demand_multiple_value` | EXISTING (v2) | Total demand multiple **as directly published by the source**; never derived here. | decimal, ratio | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 5 | `total_demand_filter_status` | EXISTING (v2) | Whether the source describes its total as filtered, unfiltered, or leaves it open. Enum §1.6. | enum | same document as #4 | `DATA_NOT_FOUND` |
| 6 | `total_demand_definition` | EXISTING (v2) | Verbatim-grounded textual statement of the numerator, denominator and wording the source used. | string | same document as #4 | `DATA_NOT_FOUND` |
| 7 | `applicant_count` | EXISTING (v2) | Number of persons/applications reported on the **demand** side. Never converted to an order count or to an allocated count. | integer | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 8 | `allocated_investor_count` | EXISTING (v2) | Number of investors/applications that actually received an allocation. Never renamed to applicant count. | integer | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 9 | `order_count` | EXISTING (v2) | Filled **only** if the source explicitly reports a count of orders (`emir adedi/sayısı`). Never derived from order quantity or demanded shares. | integer | Halka Arz Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 10 | `investor_count_semantic` | EXISTING (v2) | Which of #7/#8/#9 the source's single unlabelled "yatırımcı sayısı" figure actually is, when only one is given. Enum §1.6. | enum | same document | `DATA_NOT_FOUND` |
| 11 | `distribution_method` | EXISTING (v1) | The distribution rule applied per investor group (`eşit dağıtım`, `oransal dağıtım`, mixtures), verbatim-grounded. | string | Tasarruf Sahiplerine Satış Duyurusu; confirmed in Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 12 | `price_determination_method` | EXISTING (v1) | How the price was set and demand collected (`sabit fiyatla talep toplama`, `fiyat aralığı ile talep toplama`, `Borsa'da satış`). | string | İzahname / Sermaye Piyasası Aracı Notu; TSSD | `DATA_NOT_FOUND` |
| 13 | `lead_broker` | EXISTING (v1) | Legal name(s) of the lead intermediary/consortium leader(s), `; `-separated when more than one, verbatim including `A.Ş.`. | string | TSSD cover / İzahname | `DATA_NOT_FOUND` |
| 14 | `price_stability_planned` | EXISTING (v1) | Whether a price-stabilisation (`fiyat istikrarı`) undertaking was **planned/disclosed pre-listing**. | boolean | TSSD / İzahname | `DATA_NOT_FOUND` |
| 15 | `price_stability_undertaking` | NEW (R2) | One disclosed price-stabilisation (`fiyat istikrarı`) window, **in the unit the source itself uses**. Same rules as #16/#17 (§2.1.1). A source-stated "no stabilisation" is a real `0` with `unit = DAYS`, never `DATA_NOT_FOUND`. | decimal + `unit` | TSSD / İzahname | `DATA_NOT_FOUND` |
| 16 | `issuer_lockup_undertaking` | NEW (R2) | One disclosed lock-up undertaking binding the **issuer** on new share issuance, **in the unit the source itself uses**. `normalized_value` = the magnitude the source prints; `unit` = `DAYS`/`MONTHS`/`YEARS` as printed; never converted. `duration_start_reference` and `undertaking_scope` mandatory. One row per undertaking. | decimal + `unit` | İzahname / TSSD | `DATA_NOT_FOUND` |
| 17 | `shareholder_lockup_undertaking` | NEW (R2) | One disclosed lock-up undertaking binding **existing shareholders** on sales, in the unit the source itself uses. Same rules as #16. One row per undertaking. | decimal + `unit` | İzahname / TSSD | `DATA_NOT_FOUND` |
| 18 | `market_segment` | NEW | The BIST market/segment the shares were admitted to **at listing** (e.g. `Yıldız Pazar`, `Ana Pazar`, `Alt Pazar`), verbatim. | string | Payların İşlem Görmeye Başlaması / BIST kotasyon duyurusu | `DATA_NOT_FOUND` |
| 19 | `sector_kap_code` | NEW | The official KAP/BIST sector **code** for the issuer. `scope_tag` mandatory: `AS_OF_LISTING` or `AS_OF_RETRIEVAL`. | string | KAP company record / BIST listing notice | `DATA_NOT_FOUND` |
| 20 | `sector_kap_label` | NEW | The official KAP/BIST sector **label** matching #19, verbatim. Same `scope_tag` rule. | string | as #19 | `DATA_NOT_FOUND` |
| 21 | `bookbuilding_start` | NEW | First calendar date of the demand-collection period, as disclosed. | date | TSSD; confirmed in Sonuç Bildirimi | `DATA_NOT_FOUND` |
| 22 | `bookbuilding_end` | NEW | Last calendar date of the demand-collection period, as disclosed. | date | TSSD; confirmed in Sonuç Bildirimi | `DATA_NOT_FOUND` |

`scope_tag` allowed values: `INCL_ADDITIONAL`, `EXCL_ADDITIONAL`,
`SCOPE_NOT_SPECIFIED`, `AS_OF_LISTING`, `AS_OF_RETRIEVAL`, `NOT_APPLICABLE`.
Mandatory (i.e. `SCOPE_NOT_SPECIFIED` is acceptable only when the source itself
leaves scope open) on fields #1, #2, #3; mandatory as
`AS_OF_LISTING`/`AS_OF_RETRIEVAL` on #19, #20; `NOT_APPLICABLE` elsewhere unless
the source itself makes scope material. `scope_tag` is **not** used to
distinguish duration undertakings — that is what `duration_start_reference` and
`undertaking_scope` are for (§2.1.1).

**(R5, D1) Point-in-time restriction on `AS_OF_LISTING`.** A value whose source is
the company record page of the disclosure platform (`KAP_COMPANY_RECORD`, §3.3)
may carry exactly one `scope_tag`: `AS_OF_RETRIEVAL`. That page is live: it shows
the issuer's sector code, sector label and legal name as they stand on the day it
is opened, after any reclassification or renaming since listing. `AS_OF_LISTING`
may be written **only** from a document published on or before the ticker's
`first_trading_date` — the izahname / sermaye piyasası aracı notu, the tasarruf
sahiplerine satış duyurusu, the Borsa İstanbul kotasyon or "payların işlem görmeye
başlaması" notice, or the disclosure-platform notification of that time — with the
publication date tested under §4.6 and §1.7, both unchanged: an internal signature
date is never substituted for it, and a later republication never back-dates
availability. **One exception, and it is narrow:** where the retrieval date is on
or before the ticker's `first_trading_date`, the company record is itself a
point-in-time record of the listing state, `AS_OF_LISTING` is correct, and the
existing column 18 `retrieval_timestamp_istanbul` (§5.3) is the evidence — no new
column, no schema change. The same restriction governs the collector instruction's
field 23 `company_name` wherever that row is scope-tagged at all. The full
provision, its one exception and its retroactive posture are §R5.1.

Field count is **22**, unchanged from R1. R2 removed three field names from this
table (`price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days`,
all now script-derived, §5.4.1) and added three (#15, #16, #17).

### 2.1.1 Duration fields — recording rules (R2)

**The three duration fields are #15, #16 and #17** — `price_stability_undertaking`,
`issuer_lockup_undertaking`, `shareholder_lockup_undertaking`. One rule set
governs all three; nothing below is specific to lock-ups. They add no permission
to write an underived value and they do not weaken §9 item 5; they exist
precisely so the collector never has to.

1. **Never convert.** If the source says `bir yıl`, `normalized_value` is `1` and
   `unit` is `YEARS`. Writing `365` is a §9 item 5 violation, and remains one
   under this revision. The same holds for months: `6 ay` is `6` + `MONTHS`,
   never `180` + `DAYS`. If the source itself states the undertaking in days,
   record days — the rule is *the source's unit*, not a preferred unit.
2. **One row per undertaking.** A document that binds the issuer for one year
   from the first trading date and additionally for 180 days from prospectus
   approval discloses **two** undertakings. They are two rows of the same field
   name, differing in `duration_start_reference` and, where the source
   distinguishes them, `undertaking_scope`. They are never merged,
   never summed, never reduced to whichever is longer or shorter, and the
   existence of a second undertaking is never a reason to record neither.
3. **`duration_start_reference` is mandatory** on #15, #16 and #17 and takes one
   of: `FIRST_TRADING_DATE`, `PROSPECTUS_APPROVAL_DATE`, `PUBLIC_OFFERING_DATE`,
   `ALLOCATION_DATE`, `NOT_SPECIFIED`, `NOT_APPLICABLE`. `NOT_SPECIFIED` is
   correct and expected when the source states a duration without anchoring it;
   it is not a failure. It is `NOT_APPLICABLE` on every other field.
4. **`undertaking_scope` is mandatory** on #15, #16 and #17: a verbatim,
   un-translated transcription of who or what the source says the undertaking
   binds (e.g. the named shareholder group, `tüm mevcut ortaklar`, a share class;
   for #15, the party that will conduct the stabilisation, where the source names
   one). Where the source does not qualify the party beyond the field's own
   meaning, write `SCOPE_NOT_SPECIFIED`. It is `NOT_APPLICABLE` on every other
   field.
5. **Genuine absence is unchanged.** If no undertaking of that kind is disclosed
   anywhere after searching, the row is `DATA_NOT_FOUND` with a non-empty
   `search_scope` per §4.4 — exactly as for any other field. An undertaking that
   exists but whose duration the source does not quantify is
   `SEMANTICALLY_AMBIGUOUS` with the verbatim phrase, not a guessed number.
6. **A source-stated zero is a real zero.** This matters most on #15: where the
   source explicitly states that no price stabilisation is planned, that is `0`
   with `unit = DAYS`, not `DATA_NOT_FOUND`. §4.5 governs unchanged — an explicit
   source-stated zero is a value, and an absent fact is a sentinel. The two are
   never interchangeable in either direction.
7. **The day count is not the collector's business.** `price_stability_days`,
   `issuer_lockup_days` and `shareholder_lockup_days` are all derived downstream
   (§5.4.1). A collector that writes any of them has produced an invalid batch
   (§9 item 11).

### 2.2 Table 2 — demand-category long form

**Reused unchanged** from `[ipo_master_v2.demand_category]` /
`artifacts/ipo_master/ipo_demand_category_schema.md`. One row per **source**
category. `source_category_label` is preserved verbatim; standardisation happens
only in `normalized_category`. The 15 data fields, all with the semantics already
fixed by that schema document:

`normalized_category`, `source_category_label`, `source_parent_label`,
`category_level`, `is_aggregate`, `applicant_count`, `allocated_investor_count`,
`order_count`, `planned_allocation_shares`, `planned_allocation_pct`,
`demand_nominal`, `demand_share_pct`, `demand_multiple`, `distributed_nominal`,
`distributed_pct`.

Binding rules carried over verbatim:

- A source row that is a subtotal is kept with `category_level = AGGREGATE`,
  `is_aggregate = TRUE`, so it is not lost — and aggregate and leaf rows are
  **never** summed together.
- `demand_multiple` is filled **only** where the source states a category
  multiple. It is never derived from `demand_nominal / planned_allocation_shares`.
- A source cell showing `-`, blank, or nothing published → `DATA_NOT_FOUND`.
  An explicit `0` or `%0,00` → real zero. `DATA_NOT_FOUND` is never converted to 0.
- No cross-semantic conversion between applicant / allocated / order counts.

The legacy `investor_count` column is **not** collected. It exists only for v1
backward compatibility and is uninterpretable without `investor_count_semantic`;
writing it for the 79 would create exactly the ambiguity the v2 schema was built
to remove.

### 2.3 f3 semantics — preserved, not touched (CRITICAL)

The frozen V1.5 feature `f3` is `total_demand_multiple`, read from the canonical
pretrade master, with its comparability governed by `total_demand_filter_status`
inside `apply_f3_comparability_filter()` (`scripts/modeling/preprocessing.py`,
step 1 of `preprocess_fold`): a training-fold-only modal filter-status rule that
nulls a ticker's f3 when its status **explicitly opposes** the training-fold modal
status. The V2 preregistration candidate additionally records that
`total_demand_filter_status` "already acts inside the frozen f3 comparability rule
and must not additionally appear as a predictor".

Therefore, binding on the collector:

1. **f3's definition is unchanged by this spec.** `f3 = total_demand_multiple` as
   it stands in the frozen canonical pretrade master, with its existing
   `total_demand_definition`, `total_demand_filter_status`,
   `total_demand_multiple_origin` and its existing comparability rule.
2. `demand_shares_unfiltered` and `demand_shares_filtered` (§2.1 #1, #2) are
   **new, separate, additive fields**. They are *not* an improved f3, not a
   correction to f3, and not an input to f3.
3. The collector **must not** recompute, "fix", re-derive, re-round or replace any
   existing `total_demand_multiple`, `total_demand_multiple_value`,
   `total_demand_definition`, `total_demand_filter_status` or
   `total_demand_multiple_origin` value for any of the 79 rows. Those cells are
   already populated (78/79, 79/79, 79/79, 79/79 respectively) and are frozen.
4. If newly found evidence **disagrees** with an existing canonical value, the
   collector records the new evidence as an ordinary row with
   `field_status = SOURCES_CONFLICT` and a note naming the canonical value it
   disagrees with, and **stops there**. The validation script raises a
   `CANONICAL_DISAGREEMENT` report item. There is no write-back, no averaging, no
   "the newer source is better" rule. This matches
   `conflict_policy = NO_AUTOMATIC_SELECTION` and
   `calculation_mismatch_policy = REPORT_ONLY_NO_AUTOMATIC_CORRECTION`.
5. `total_demand_multiple_origin` is **never** written by the collector. It is a
   canonical derivation label. For any new evidence, the collector records the raw
   numerator, the raw denominator and the source-published multiple; the origin
   label is a downstream, script-assigned artifact — exactly as
   `publication_timing_status` is (§1.7).

Consequence of ignoring this section: a collector that "corrects" f3 silently
mutates a frozen benchmark input and invalidates every recorded V1.5 and
V2/R3 result. This is the single most damaging error available in this task.

### 2.4 Reconciliation with the independently proposed (Fable) field list

The independent review proposed 18 offer-level field names plus 8
demand-category columns. Rulings, with reasons:

| Proposed | Ruling | Reason |
|---|---|---|
| `total_demand_multiple_source_reported` | **Renamed** to `total_demand_multiple_value` | An existing v2 column with exactly this semantics ("kaynakta doğrudan bildirilen toplam talep katı") already exists. A synonym would fork the schema. |
| `demand_shares_unfiltered`, `demand_shares_filtered`, `shares_offered_denominator` (+`scope_tag`) | **Accepted as NEW** | No existing column carries the raw numerator/denominator. `scope_tag` is realised as a schema column, not a name suffix. |
| `total_demand_filter_status` | **Accepted, enum not extended** | Existing v2 enum. `SEMANTICALLY_AMBIGUOUS` is deliberately *not* added to it — the predecessor spec records this as operator-ratified; ambiguity lives one level up, in `field_status`. |
| `applicant_count`, `allocated_investor_count` | **Accepted, existing names** | Already v2 columns. |
| — | **Added: `order_count`** | The `investor_count_semantic` enum contains `ORDER_COUNT`. Omitting the field would force an order count to be misfiled as an applicant count — the precise error the v2 schema exists to prevent. |
| — | **Added: `investor_count_semantic`** | Required whenever a source publishes a single unlabelled investor count; without it the count is uninterpretable. |
| — | **Added: `total_demand_definition`** | Required companion of `total_demand_multiple_value` under the existing schema ("üç alan birlikte zorunludur"). |
| demand-category columns (8 proposed) | **Superseded by the full 15-field existing set** | The 8 omit `source_parent_label`, `is_aggregate`, `order_count`, `planned_allocation_shares`, `demand_share_pct`, `demand_multiple`, `distributed_nominal`. Dropping `is_aggregate`/`source_parent_label` in particular removes the only mechanism preventing aggregate+leaf double counting. |
| `sector_kap` (+ AS_OF tag) | **Split into `sector_kap_code` + `sector_kap_label`** | And held strictly distinct from the existing `sector` column, which is free-text Turkish prose ("Gayrimenkul yatırım ortaklığı", "Demir-çelik üretimi"), not a taxonomy value. Writing a KAP code into `sector` would silently change that column's meaning against 20 rows' worth of established convention. |
| `market_segment`, `bookbuilding_start`, `bookbuilding_end`, `distribution_method`, `price_determination_method`, `lead_broker`, `price_stability_planned`, `price_stability_days`, `issuer_lockup_days`, `shareholder_lockup_days` | **Accepted** | Four are new; six reuse existing v1 column names verbatim. |

Net: **22 offer-level fields** (18 proposed − 1 renamed into an existing column
+ 3 added + 1 from the sector split), and the **15 data fields** of the existing
demand-category long form.

**R2 amendment to the last table row.** The three duration entries in that row —
`price_stability_days`, `issuer_lockup_days` and `shareholder_lockup_days` — were
accepted by R1 as collector-written v1 column names. R2 revises that single
ruling: the *columns* remain exactly as `config/ipo_master_schema.toml` defines
them and are not renamed or removed anywhere, but they are no longer
**collected**. The collector now records `price_stability_undertaking` /
`issuer_lockup_undertaking` / `shareholder_lockup_undertaking` in the source's own
unit (§2.1 #15/#16/#17) and the day counts are derived (§5.4.1). The reason is
the one R1 could not have known: sources state these undertakings in years or
months, so a field typed in days had no compliant value the collector could
write. Every other ruling in the table stands unchanged.

No irreconcilable conflict was found between the proposed list and the existing
schema. Every difference above is a naming or completeness correction, resolved
in favour of the existing schema per `CLAUDE.md` §22.

### 2.5 Deliberately excluded

| Field | Why excluded |
|---|---|
| `sector` (existing free-text column) | Not collected. It is prose, not a taxonomy; a preregistered grouping scheme does not exist (`issuer_sector_official_taxonomy_backfill` is `REQUIRES_BOUNDED_BACKFILL`, `NOT_A_V2_FEATURE`). `sector_kap_code`/`_label` are collected instead, as a *new* pair. |
| `investor_count` (legacy) | Uninterpretable without semantic; superseded by #7–#10. |
| Financial-statement fields (revenue, margins, leverage, valuation) | `financial_statement_information` is preregistered as `NOT_CURRENTLY_FEASIBLE`: it requires a TMS-29 / period-comparability policy that does not exist. |
| XU100 / market-regime history | `xu100_pre_cutoff_index_history` is a sealed, separate `SEALED_V3_MARKET_REGIME_CANDIDATE` item; collecting it here would let a window be chosen outside its seal. |
| Additional-sale planned-vs-exercised semantic confirmation | Preregistered separately as `f6_semantic_confirmation_planned_versus_exercised`, `authorized_in_this_task = FALSE`. It touches **V2 feature evidence** (f6/f7), not the thin post-bookbuild gap, and carries its own withdrawal consequence ("if the rows are found to mix planned and exercised semantics, f6 and f7 are withdrawn and V2 evaluation is blocked"). Folding it into a 79-row bulk collection would put a V2-blocking decision inside a routine batch. It needs its own authorization. |
| Anything post-listing | §0.4. |

### 2.6 Fields already complete for the 79 — do not re-collect, do not overwrite

`ipo_price`, `shares_offered`, `capital_increase_shares`, `existing_share_sale`,
`additional_sale_shares`, `post_ipo_share_capital`, `ipo_size_tl`,
`free_float_pct`, `capital_increase_pct_of_offer`, `existing_sale_pct_of_offer`,
`first_trading_date`, and the four total-demand columns of §2.3.

`company_name` is the one exception: 51/79 populated. It may be **completed** for
the 28 empty rows (identity only, from the KAP company record), and must never be
altered for the 51 populated rows.

---

## 3. Source document hierarchy

### 3.1 Source tiers (unchanged, from `ipo_master_schema.toml`)

`SPK` (1) > `KAP` (2) > `BORSA_ISTANBUL` (3) > `MKK` (4) >
`AUTHORIZED_INTERMEDIARY_OR_CONSORTIUM` (5) > `TRUSTED_SECONDARY` (6).
Ranks 1–4 are `official = true`; ranks 5–6 are not.

`source_priority` in the output is the tier **code**, not the rank number.

### 3.2 Rank does not resolve semantics

**A higher tier does not silently overwrite a lower tier when the two differ in
semantics rather than in value.** Rank breaks ties only between sources making the
*same claim under the same definition, scope and date*. A semantic difference
between an SPK statement and a KAP statement is a `SEMANTIC_DIFFERENCE`, recorded
as such — not an SPK win. This rule is inherited verbatim from the predecessor
collector spec §I.

An `AUTHORIZED_INTERMEDIARY` source is never labelled or treated as SPK/KAP-tier
evidence, and a `TRUSTED_SECONDARY` source is never used as the sole basis for a
numeric field in Table 1 or Table 2.

### 3.3 Document families and what each is authoritative for

| Document family | `source_document_type` | Authoritative for |
|---|---|---|
| Halka Arz Sonuç Bildirimi (KAP) — incl. the "Satış Sonuçları" / "Dağıtım Sonuçları" / "Halka Arzına İlişkin Sonuçlar" phrasings | `KAP_SONUC_BILDIRIMI` | Table 1 #1–#10; **all** of Table 2; confirmation of #21/#22 |
| Tasarruf Sahiplerine Satış Duyurusu and annexes | `TSSD` | Table 1 #11–#17, #21, #22; planned allocation percentages in Table 2 |
| İzahname / Sermaye Piyasası Aracı Notu | `IZAHNAME_OR_ARAC_NOTU` | Table 1 #12–#17; fallback for #11 |
| Payların İşlem Görmeye Başlaması bildirimi / BIST kotasyon duyurusu | `BIST_LISTING_NOTICE` | Table 1 #18; `first_trading_date` confirmation only |
| KAP company record | `KAP_COMPANY_RECORD` | Table 1 #19, #20; `company_name` completion |
| SPK haftalık bülteni | `SPK_BULLETIN` | approval evidence; cross-check for #12; never the sole source of a demand figure |
| Anything else discovered | `OUT_OF_SCOPE_FAMILY` | recorded (title, date, URL) but never used as a field source |

Trap inherited from the predecessor spec: a document titled
"Fiyat Tespit Raporu'na İlişkin Analist Raporu" is **not** a Fiyat Tespit Raporu.
It is an intermediary restatement, tier 5 at best, and never substitutes for the
original even when the original is missing.

### 3.4 Multi-source recording

If two or more documents state the same field, record **each** as its own row.
Agreement is established by the validation script comparing rows, not by the
collector picking one and discarding the other. There is no "best source"
collapse at collection time.

---

## 4. Conflict, absence and timestamp rules

### 4.1 True conflict

Two values are `SOURCES_CONFLICT` **only** when they share field, semantic
definition, date, scope and offer universe, and still disagree numerically.
Then: **both rows are recorded**, both get `field_status = SOURCES_CONFLICT`, both
get the **same `conflict_group_id`**, and **no selection is made**.

### 4.2 Not a conflict

| Situation | `field_status` | Handling |
|---|---|---|
| Different scope (additional sale included vs excluded; pre- vs post-additional-sale offer size) | `SCOPE_DIFFERENCE` | Both rows recorded, each with its own `scope_tag`. Not a conflict. |
| Same field name, different definition (e.g. one source's "talep katı" is filtered, the other's is not) | `SEMANTIC_DIFFERENCE` | Both rows recorded; `notes` states each definition. |
| Source wording cannot be resolved into either of the above | `SEMANTICALLY_AMBIGUOUS` | Row recorded with the verbatim phrase; escalated, never guessed. |
| A structurally unusual offer (multi-tranche, dual price) whose scope cannot be bounded | `SPEC_EDGE_CASE_UNRESOLVED` | Recorded and escalated; the ticker's other fields proceed normally. |

### 4.3 Forbidden resolutions

Averaging conflicting values. Choosing the "more convenient", rounder, larger,
smaller or more recent value. Choosing the source whose value looks more like the
other 78 rows. Silently promoting a tier-5/6 value to fill a tier-1–4 gap.
Deriving a missing multiple from a numerator and denominator the source did not
itself divide. All forbidden without exception.

### 4.4 Genuine absence

If, after searching, a field is not published anywhere:
`field_status = DATA_NOT_FOUND`, `normalized_value = DATA_NOT_FOUND`, and
`search_scope` **must** be non-empty and must name the document families actually
opened (e.g. `KAP_SONUC_BILDIRIMI;TSSD;IZAHNAME_OR_ARAC_NOTU`). A
`DATA_NOT_FOUND` row with an empty `search_scope` is a validation failure, not a
finding.

If a specific document was opened and does not contain the field, but other
document families remain unchecked, that row is
`field_status = FIELD_NOT_FOUND_IN_DOCUMENT` — a per-document observation, not a
per-field conclusion.

### 4.5 Forbidden absence encodings

Leaving a cell empty. Writing `0` for a missing value. Writing `N/A`, `NA`, `-`,
`yok`, `bilinmiyor`, `null`, `None`, or an em dash. Only `DATA_NOT_FOUND` (or, for
`total_demand_filter_status`, `NOT_APPLICABLE` where the schema defines it) is
acceptable. An explicit source-stated zero is a real `0` and is not missing.

### 4.6 Timestamps

- Every row carries `source_publication_date`; `source_publication_time` when the
  source exposes one.
- `publication_timing_status` and `available_before_first_trade` are **derived by
  the validation script** under §1.7, never written by the collector.
- A later-published correction **never** back-dates the fact. Only the earliest
  confirmed official appearance counts. A corrected document is recorded as its
  own row with its own real date.
- A document's internal signature/approval date is never used as its publication
  date; it may be recorded in `notes`.
- An intermediary page dated later than the KAP disclosure never overrides the KAP
  timestamp for the same fact.

### 4.7 Canonical disagreement

Any collected value that contradicts an already-frozen canonical cell for the same
ticker and field (§2.3 item 4, §2.6) is recorded as evidence and reported. It is
never written back, and it never changes the frozen artifact. Resolution is an
operator decision in a separate task.

---

## 5. Output schema

### 5.1 File layout (all paths ASCII only)

```
work/pretrade_extension/collection/
  B00/  PRETRADE_EXT_B00_offer_fields.csv
        PRETRADE_EXT_B00_demand_categories.csv
  B01/  PRETRADE_EXT_B01_offer_fields.csv
        PRETRADE_EXT_B01_demand_categories.csv
        PRETRADE_EXT_B01_category_cell_status.csv
  ...
  B16/  PRETRADE_EXT_B16_offer_fields.csv
        PRETRADE_EXT_B16_demand_categories.csv
        PRETRADE_EXT_B16_category_cell_status.csv
```

The third file per batch is the demand-category cell-status register (§5.6),
introduced by R2 and required for `B01`…`B16`. `B00` was collected and calibrated
under R1 and has two files; it is not re-collected and no register is
back-filled for it (§7.4).

**Turkish-character warning.** `core.quotepath` is `true` in this repository, so
non-ASCII bytes in a *path* are escaped in git output and become hard to audit.
File and directory names must be ASCII-only. Turkish characters inside CSV
*content* (`source_category_label`, `verbatim_source_phrase`, `lead_broker`,
`distribution_method`) are required and must be preserved exactly — never
ASCII-folded, never transliterated (`ş`→`s`, `ı`→`i`, `ğ`→`g` are all forbidden).

### 5.2 File format

UTF-8 **with BOM**; CRLF line endings; `,` delimiter; `"` quote character with
`""` escaping; `.` decimal separator (never `,`); no thousands separators; dates
`YYYY-MM-DD`; times `HH:MM` 24h Europe/Istanbul; timestamps
`YYYY-MM-DDTHH:MM:SS+03:00`; booleans `TRUE`/`FALSE`. Header row mandatory,
columns in exactly the order below.

### 5.3 Offer-level CSV — 26 columns

Columns 1–24 are R1's, in R1's order, with R1's meanings. Columns 25 and 26 are
appended by R2 (§R.1); appending rather than inserting keeps every R1 column at
its R1 position, so an R1-era reader that stops at column 24 reads an R2 file
correctly.

| # | column | filled by | notes |
|---|---|---|---|
| 1 | `batch_id` | collector | `B00`…`B16` |
| 2 | `ticker` | collector | must be in the frozen batch table |
| 3 | `field_name` | collector | one of the 22 names in §2.1 (or `company_name`) |
| 4 | `raw_value` | collector | exactly as printed in the source, original formatting, Turkish decimal comma preserved if that is what the source shows |
| 5 | `normalized_value` | collector | canonical form per §5.2, or `DATA_NOT_FOUND` |
| 6 | `unit` | collector | `SHARES`, `TL`, `RATIO`, `PCT`, `DAYS`, `MONTHS`, `YEARS`, `COUNT`, `DATE`, `TEXT`, `BOOLEAN`, `ENUM` — `MONTHS`/`YEARS` added by R2 (§R.1); this vocabulary is defined here, not inherited from any config TOML |
| 7 | `scope_tag` | collector | §2.1 enum |
| 8 | `source_document_type` | collector | §3.3 enum |
| 9 | `source_priority` | collector | tier code, §3.1 |
| 10 | `source_name` | collector | issuer/institution and document title |
| 11 | `source_url` | collector | direct URL to the document, not a search page |
| 12 | `kap_notification_id` | collector | KAP disclosure id, or `DATA_NOT_FOUND` for non-KAP sources |
| 13 | `attachment_filename` | collector | as served, or `DATA_NOT_FOUND` |
| 14 | `page_or_section` | collector | page number / table caption / heading |
| 15 | `verbatim_source_phrase` | collector | the exact sentence or table cell the value came from, Turkish preserved |
| 16 | `source_publication_date` | collector | `DATA_NOT_FOUND` if not establishable |
| 17 | `source_publication_time` | collector | `DATA_NOT_FOUND` if not exposed |
| 18 | `retrieval_timestamp_istanbul` | collector | when the collector actually opened the document |
| 19 | `collector` | collector | identifier of the collecting agent/session |
| 20 | `field_status` | collector | §1.6 enum |
| 21 | `conflict_group_id` | collector | shared id linking the rows of one conflict/scope/semantic set; `NOT_APPLICABLE` otherwise |
| 22 | `search_scope` | collector | `;`-separated document families actually opened; **mandatory** when `field_status = DATA_NOT_FOUND` |
| 23 | `notes` | collector | semantics, caveats, canonical-disagreement statements |
| 24 | `spec_version` | collector | `PRETRADE_EXT_COLLECTION_SPEC_V2` for `B01`…`B16`; `B00`'s existing rows keep `PRETRADE_EXT_COLLECTION_SPEC_V1` (§7.4) |
| 25 | `duration_start_reference` | collector | **R2.** Mandatory on §2.1 #15/#16/#17: `FIRST_TRADING_DATE`, `PROSPECTUS_APPROVAL_DATE`, `PUBLIC_OFFERING_DATE`, `ALLOCATION_DATE`, `NOT_SPECIFIED`. `NOT_APPLICABLE` on every other field. |
| 26 | `undertaking_scope` | collector | **R2.** Mandatory on §2.1 #15/#16/#17: verbatim transcription of who/what the undertaking binds, or `SCOPE_NOT_SPECIFIED` when the source does not qualify it. `NOT_APPLICABLE` on every other field. |

`conflict_group_id` is an addition to the independently proposed 21-column
schema. Without it, two rows of a `SOURCES_CONFLICT` pair cannot be mechanically
bound to each other, and a validator cannot tell a genuine conflict pair from two
unrelated rows that happen to share a field name.

Columns 25 and 26 carry `NOT_APPLICABLE` on all 19 non-duration field names, so
they cost the collector one fixed token per row and carry meaning only where §2.1
#15/#16/#17 make them mandatory. `NOT_APPLICABLE` here is a real "this column does
not apply to this field", not an absence encoding, and §4.5 is untouched: a
*missing fact* is still only ever `DATA_NOT_FOUND`.

### 5.4 Alignment with the existing 12-column provenance schema

The 24-column file is a strict **superset projection** of `provenance_fields`.
The validation script emits, per batch, a derived 12-column projection in exactly
the existing order — `ticker, field_name, raw_value, normalized_value,
source_priority, source_name, source_url, source_publication_date,
available_before_first_trade, verification_status, conflict_status, notes` —
where:

- `available_before_first_trade` ← derived from `publication_timing_status`
  (`AVAILABLE_PRE_FIRST_TRADE`→`TRUE`, `POST_FIRST_TRADE_NOT_ELIGIBLE`→`FALSE`,
  `PUBLICATION_TIMING_UNRESOLVED`→`UNKNOWN`);
- `verification_status` ← derived from `source_priority` + `field_status`
  (tiers 1–4 → `OFFICIAL_VERIFIED`; tier 5 → `AUTHORIZED_INTERMEDIARY_VERIFIED`;
  tier 6 → `SECONDARY_VERIFIED`; `field_status = DATA_NOT_FOUND` →
  `DATA_NOT_FOUND`; `field_status = SOURCES_CONFLICT` → `SOURCE_CONFLICT`);
- `conflict_status` ← `SOURCE_CONFLICT` when `field_status = SOURCES_CONFLICT`,
  else `NO_CONFLICT`.

These three columns are **never** written by the collector. The derived file also
carries `first_trading_date` and `publication_timing_status` for audit, giving a
29-column derived artifact alongside the 12-column projection.

Three further columns are script-assigned on the same footing — see §5.4.1.

### 5.4.1 Derived duration fields (R2)

`price_stability_days`, `issuer_lockup_days` and `shareholder_lockup_days` join
that set: they are **script-derived, never collector-written**, on exactly the
footing §1.7 already established for `publication_timing_status` and §2.3 item 5
for `total_demand_multiple_origin`.

The derivation script, when a later task authorizes it, must satisfy all of:

1. **Input.** Only the three duration fields' rows — `price_stability_undertaking`,
   `issuer_lockup_undertaking`, `shareholder_lockup_undertaking` — with their
   `unit`, `duration_start_reference` and `undertaking_scope`. It reads no source
   document and invents no undertaking. Each derived column takes its input from
   the corresponding undertaking field and from nothing else:
   `price_stability_days` ← #15, `issuer_lockup_days` ← #16,
   `shareholder_lockup_days` ← #17.
2. **The conversion constant lives in the script, not here.** This specification
   deliberately states no day-equivalent for a year or a month. The constant is
   declared in the script, carries its own version identifier, and every emitted
   day count records which constant version produced it. A specification that
   hardcoded the constant would freeze a commercial convention as though it were
   arithmetic, and would make revising it a spec revision instead of a script
   change. Rationale in `CHANGELOG_R1_TO_R2.md` §1.
3. **Ambiguity is preserved, not resolved.** Where a ticker has more than one
   undertaking of the same type, the script does **not** silently pick one. It
   emits the derived value only where a single undertaking applies, and otherwise
   emits `MULTIPLE_UNDERTAKINGS_NOT_REDUCIBLE` together with the full set for a
   human decision. `DATA_NOT_FOUND` in, `DATA_NOT_FOUND` out. A source-stated
   `0` is a value, not an absence, and passes through as `0` (§2.1.1 item 6).
4. **The derived value is not evidence.** It is not `OFFICIAL_VERIFIED`, not
   canonical, and never written back into any frozen artifact. Where it disagrees
   with an existing canonical `issuer_lockup_days` /`shareholder_lockup_days`
   value, §4.7 applies unchanged: report the disagreement, change nothing.
5. **Reversibility.** The verbatim magnitude, unit, start reference and source
   phrase remain in the collected file, so any derived day count can be recomputed
   or discarded without re-collection. This is the property that makes the
   derivation safe and the collector-side conversion unsafe.

### 5.5 Demand-category CSV — 31 columns

`batch_id, ticker, normalized_category, source_category_label,
source_parent_label, category_level, is_aggregate, applicant_count,
allocated_investor_count, order_count, planned_allocation_shares,
planned_allocation_pct, demand_nominal, demand_share_pct, demand_multiple,
distributed_nominal, distributed_pct, source_document_type, source_name,
source_url, kap_notification_id, attachment_filename, page_or_section,
source_publication_date, source_publication_time, retrieval_timestamp_istanbul,
collector, field_status, conflict_group_id, notes, spec_version`

= 20 of the existing 22 long-form schema fields reused verbatim, plus 11
collection-audit columns. The two not present —
`available_before_first_trade` and `verification_status` — are script-derived
exactly as in §5.4, and are added by the validator, not the collector.

**Unchanged by R2.** These 31 columns, their order and their meanings are
carried into R2 byte-identical. R2 adds no column here and removes none. That is
deliberate: this file is the one that must stay row-comparable with
`artifacts/ipo_master/consolidated/ipo_master_20_demand_categories_canonical.csv`,
and it is the file the §6 calibration was scored against. Changing its shape
would have put the completed calibration in question. The expressiveness R2 needs
is added beside it, in §5.6.

The row-level `field_status` in this file keeps its R1 meaning and its R1 enum:
it describes **the source record as a whole** — how the collector read this
category row from this document. Per-cell status lives in §5.6. A data cell with
no §5.6 entry is `VALUE_RECORDED` by construction.

### 5.6 Demand-category cell-status register — 9 columns (R2)

The third per-batch file. One row per demand-category **data cell** whose status
is anything other than a plainly recorded value — in practice, every cell holding
`DATA_NOT_FOUND`, plus any cell the collector marks ambiguous or conflicted.
Cells that simply hold a value are **not** listed; the register is an exception
log, not a mirror of the table.

```
batch_id, ticker, normalized_category, source_category_label, field_name,
field_status, search_scope, notes, spec_version
```

| # | column | notes |
|---|---|---|
| 1 | `batch_id` | as §5.3 |
| 2 | `ticker` | as §5.3 |
| 3 | `normalized_category` | together with 2 and 4, identifies the §5.5 row this cell belongs to |
| 4 | `source_category_label` | verbatim, exactly as written in the §5.5 row |
| 5 | `field_name` | one of the **15 data fields** of §2.2. Any other value is a `FAIL` |
| 6 | `field_status` | the §1.6 `field_status` enum, unchanged and unextended — the status **of this cell** |
| 7 | `search_scope` | `;`-separated document families actually opened; **mandatory** when `field_status = DATA_NOT_FOUND`, exactly as §4.4 requires for the offer-level file |
| 8 | `notes` | why the cell is in this state; the verbatim source phrase where one exists |
| 9 | `spec_version` | `PRETRADE_EXT_COLLECTION_SPEC_V2` |

Format is §5.2's, identically: UTF-8 with BOM, CRLF, `,` delimiter, `"` quoting,
no empty cells.

Binding rules:

1. **Completeness.** Every data cell in the §5.5 file holding `DATA_NOT_FOUND`
   has **exactly one** register row. Zero rows is a `FAIL` (the §4.4 search-scope
   obligation is unmet); two rows for one cell is a `FAIL` (§8 check 8).
2. **Referential integrity.** Every register row names a
   `(ticker, normalized_category, source_category_label)` triple that exists in
   that batch's §5.5 file, and a `field_name` in the 15. A register row with no
   matching category row is a `FAIL`.
3. **No values.** The register carries **no** data value, ever. It records status
   and search scope. A collector that puts a number in `notes` as a substitute
   for the §5.5 cell has produced an invalid batch.
4. **It creates no absence encoding.** §4.5 is untouched. The absent cell in the
   §5.5 file still reads `DATA_NOT_FOUND`; the register explains it, it does not
   replace it.
5. **`order_count` is not exempt.** It is in scope (§2.1 #9), it is frequently
   genuinely absent, and each such absence needs its register row with a real
   `search_scope` naming documents actually opened. §6.2's binding mitigation
   applies here in full: that a field is often absent is never a reason to write
   `DATA_NOT_FOUND` without searching, and the register is precisely the artifact
   that makes an unsearched absence visible.

**What this fixes.** R1's two open items — an absence in the category file with
nowhere to declare its search scope, and 15 data fields sharing one row-level
`field_status` — are both closed, without touching the 31-column schema and
therefore without touching anything the calibration was scored on.

---

## 6. Calibration set

### 6.0 Calibration status under R2 (read this first)

The whole of §6 is carried over from R1 unchanged. What changes is only what the
completed calibration is now understood to cover.

- **`B00` was collected and scored under R1** and is not re-run under R2 (§7.4).
  The §6.6 gates passed on the second attempt
  (`BORSAI_B00_ATTEMPT2_GATE_20260906_T6`): `MISMATCH = 0`, and
  `(MISMATCH + MISS) / scored_cells` comfortably inside the 10 % bound.
- **That result stands, and it is a result about R1's field set.** The gates were
  measured cell by cell against the canonical record over the fields R1 defined,
  in the 24-column and 31-column shapes R1 defined. Nothing in R2 alters those
  measurements, and R2 changes no gate, no threshold, no cell class and no
  scoring rule.
- **R2's added fields are NOT calibrated.** `issuer_lockup_undertaking`,
  `shareholder_lockup_undertaking`, `duration_start_reference`,
  `undertaking_scope` and the entire §5.6 register were introduced *after* the
  calibration and have never been scored against an answer key. No claim of
  measured collection reliability extends to them. They inherit `B00`'s pass in
  no sense whatsoever.
- **Re-running §6 under R2 is not authorized by this revision** and is not
  required by it. §6.7's attempt budget was consumed under R1 (two of three
  attempts used). Whether to spend the third attempt on a new calibration
  covering the R2 fields is an operator decision, made on the record, and outside
  this document.
- The two `B00` lock-up cells that this revision exists to fix were scored as
  `MISS` under R1 — a coverage failure the collector declared, inside Gate 2's
  tolerance. They were never scored as `MISMATCH`, and R2 does not retroactively
  reclassify them.

### 6.1 Selection rule (mechanical, frozen)

> Take the 20 members of `HISTORICAL99_FROZEN_COHORT_V1` whose
> `membership_source = CANONICAL20_PROTECTED_INPUT`. Sort by `first_trading_date`
> **descending**, tie-break `ticker` **ascending**. Take the first 5.

Selection depends only on a listing date. It does not depend on any outcome, on
how hard a ticker is to collect, on how complete its canonical record is, or on
anything a collector could steer. Applying the rule on 2026-09-06 yields the five
tickers listed in `CALIBRATION_SET.md`. If the rule is ever re-run it must return
the same five; if it does not, the cohort changed and this spec is void.

Recorded as a fact, not as a selection criterion: the five tickers the rule
returns coincide exactly with the historical `batch_01` cohort
(`artifacts/ipo_master/batches/batch_01_*`). This was not engineered — the rule
was fixed first and this is its output — but it does mean their canonical evidence
is the densest in the repository, which makes the comparison informative.

### 6.2 Blindness

The collector collects these five **blind**: it is given the ticker codes, this
specification and nothing else. It is not given, and must not be shown or told
about, the canonical values, the contents of the canonical files, the per-ticker
category row counts, or any partial hint of the answer key. The answer key lives
only in the repository's existing frozen canonical artifacts and is opened only by
the comparison step, after `B00` is submitted and its file hashes recorded.

Requesting the answer key, or any subset of it, before submitting `B00` voids the
calibration.

**Disclosed residual leak.** §1.5 is part of this document and is therefore
visible to the collector, and its `n20` column reports, per field, how many of the
20 dense tickers have a non-missing value (e.g. `order_count` 2/20,
`foreign_institutional_demand_multiple` 10/20). That is a **cohort-level
aggregate**: it names no ticker, gives no value, and does not say which of the 20
are the five. It is nonetheless a weak prior on how often a field is published, and
it is disclosed here rather than removed, because §1.5 is the inventory this
specification is required to carry.

Binding mitigation: the collector records what the source in front of it actually
says, and nothing else. It must **not** use the §1.5 counts as an expectation — not
to justify writing `DATA_NOT_FOUND` without searching, and not to doubt a value it
did find because the field "is usually missing". A `DATA_NOT_FOUND` is admissible
only with a non-empty `search_scope` naming documents actually opened (§4.4), which
is exactly the check that makes an unsearched `DATA_NOT_FOUND` detectable.

### 6.3 Comparison method (field-level, mechanical)

Comparison is per **cell**, where a cell is `(ticker, field_name, scope_tag)` for
offer-level fields and `(ticker, normalized_category, category_field)` for
category fields. Each cell is classified:

| Class | Definition | Counts as error |
|---|---|---|
| `MATCH` | Collected normalized value equals canonical value under §6.4 normalization | no |
| `MATCH_ABSENT` | Both collected and canonical are `DATA_NOT_FOUND` | no |
| `MISMATCH` | Both present, values differ | **yes** |
| `MISS` | Canonical has a value, collected is `DATA_NOT_FOUND` | **yes** |
| `CANONICAL_GAP_FILLED` | Canonical is `DATA_NOT_FOUND`, collected has a value | no — reported separately, requires manual review before any use |
| `UNSCORED` | Free-text field (§6.5) or a field with no canonical counterpart | no — reported as a count |
| `EXTRA_ROW` | A category row with no canonical counterpart row | no — reported, reviewed |

`scored_cells = MATCH + MATCH_ABSENT + MISMATCH + MISS`.

### 6.4 Value normalization before comparison

Numeric: strip thousands separators and whitespace, convert a Turkish decimal
comma to a point, compare as exact decimal strings after removing trailing zeros.
No tolerance band — these are transcriptions of printed figures, not computations.
Integer counts: exact. Dates: ISO. Booleans and enums: exact, uppercase.
Institution lists (`lead_broker`): compare as an order-insensitive set of names
after collapsing whitespace and normalising the legal-form suffix.

### 6.5 Fields excluded from scoring

`distribution_method` and `price_determination_method` are free-form Turkish prose
in the canonical record; string equality would produce noise, and judging "same
meaning, different words" is not mechanical. They are collected, and reported as
`UNSCORED` with their collected and canonical strings side by side for human
reading. They do not enter the error rate in either direction.

### 6.6 Acceptance gates

Two gates, both must pass:

- **Gate 1 (hard, zero tolerance).** `MISMATCH = 0` on every numeric, date and
  enum cell. Rationale: a mismatch is a **correctness** failure — the collector
  read a printed number and reported a different one, or assigned the wrong enum.
  There is no acceptable rate of that, because the 79 rows have no answer key to
  catch it later.
- **Gate 2 (coverage).** `(MISMATCH + MISS) / scored_cells ≤ 0.10`. Rationale: a
  `MISS` is a **coverage** failure — the document exists but was not found. Some
  is expected for older listings with thinner KAP archives, and unlike a mismatch
  it is self-declaring: it arrives as `DATA_NOT_FOUND` with a `search_scope`, so a
  reader knows the cell is missing rather than wrong.

`CALIBRATION_PASS` requires both. Anything else is `CALIBRATION_FAIL`.

### 6.7 If the gates are not met

1. Collection of the 79 **does not start**. `B01` is not opened.
2. Every discrepancy is root-caused individually and classified as: a spec defect
   (ambiguous field definition, wrong primary document), a collector procedure
   defect, or a genuine problem in the canonical record itself.
3. Spec defects are fixed by publishing a **new** spec revision (a new directory
   and a new tag — from this revision onward, `..._R3`, then `..._R4`). No
   published revision is ever edited in place. This document was itself produced
   under this rule: R1 was left untouched and R2 published beside it.
4. Calibration is re-run on **the same five tickers**. Re-selection is forbidden —
   picking a different five after a failure is selecting on difficulty.
5. **At most two re-runs.** Repeatedly tuning a collection procedure against a
   known answer key is itself a form of overfitting: after the third total attempt
   the process stops and the operator decides, on the record, whether to proceed,
   restructure the collection, or abandon it. Feedback given to the collector
   between attempts is limited to the per-field discrepancy list; the full
   canonical dataset is never handed over.

### 6.8 Where calibration output goes

```
work/pretrade_extension/calibration/
  PRETRADE_EXT_CALIBRATION_B00_comparison.csv     # one row per compared cell
  PRETRADE_EXT_CALIBRATION_B00_summary.json       # counts, rates, gate verdicts
  PRETRADE_EXT_CALIBRATION_B00_discrepancies.md   # human-readable root causes
```

The summary JSON records `scored_cells`, each class count, both gate results, the
overall verdict, the sha256 of the submitted `B00` files, and the sha256 of every
canonical file used as the key — so a later reader can verify the key was not
changed after the fact. Calibration output is **not** promoted into `artifacts/`;
it stays under `work/` until an operator decision moves it.

---

## 7. Batch plan

### 7.1 Batch construction rule

- Order the 79 thin tickers by `first_trading_date` **ascending**, tie-break
  `ticker` ascending.
- **5 tickers per batch**, matching the existing `batch_01`…`batch_04` convention
  used for the dense 20.
- 79 = 15 batches of 5 + 1 batch of 4 → **16 batches**, `B01`…`B16`.
- `B00` is the calibration batch (5 FULL20 tickers) and is **not** part of the 79.
- Total: **17 batches, 84 ticker-slots, 79 in-scope rows**.

Oldest-first ordering means the hardest archive cases (2023 listings, thinner KAP
history) are met first, while the spec can still be revised at the earliest
possible point.

### 7.2 Frozen batch table

| Batch | Tickers |
|---|---|
| `B01` | HATSN, DMRGD, MEKAG, DOFER, MHRGY |
| `B02` | BORLS, TABGD, VRGYO, MARBL, BINHO |
| `B03` | EKOS, AGROT, SKYMD, CATES, BEGYO |
| `B04` | KBORU, SURGY, MEGMT, AVPGY, PATEK |
| `B05` | BORSK, LMKDC, ALVES, OBAMS, ARTMS |
| `B06` | MOGAN, ODINE, ENTRA, RGYAS, LILAK |
| `B07` | KOTON, ALTNY, KOCMT, HRKET, ONRYT |
| `B08` | OZYSR, ALKLC, YIGIT, HOROZ, SEGMN |
| `B09` | EFORC, DCTTR, BAHKM, TCKRC, GUNDG |
| `B10` | AHSGY, OZATD, CEMZY, DURKN, BINBN |
| `B11` | CGCAM, SMRVA, ARMGD, EGEGY, GLRMK |
| `B12` | AKFIS, MOPAS, SERNT, BIGEN, DSTKF |
| `B13` | VSNMD, ENDAE, KLYPV, BALSU, BULGS |
| `B14` | DOFRB, ECOGR, VAKFA, PAHOL, ZERGY |
| `B15` | ARFYE, MEYSU, FRMPL, ZGYO, UCAYM |
| `B16` | NETCD, AKHAN, BESTE, SOHOE |

This assignment is frozen. A ticker is never moved between batches, and batches
are never merged, split or reordered — a batch is the audit unit, and moving
tickers between them makes per-batch quality statistics uncomparable.

### 7.3 Batch protocol

For each batch, in order: collect → submit both CSVs → run the deterministic
validator (§8) → read the batch report → only then open the next batch. A batch
whose validation returns `FAIL` is corrected and re-validated before the next
batch opens. Batches are never collected ahead in parallel, because a spec defect
found in `Bn` would by then already have contaminated `Bn+1`…

After `B04` (a quarter of the cohort) the accumulated validator reports are
reviewed for systematic defects. If a systematic spec defect is found, remaining
batches pause and a further spec revision (`R3`) is published; already-collected
batches are re-validated against the revision and re-collected only for the
affected fields.

### 7.4 Transition from R1 to R2 (binding)

1. **`B00` is not repeated.** The calibration tickers are the five densest
   Market20 rows; their canonical record already exists. `B00`'s output was a
   test of collection reliability, not production data for the 79, and nothing
   downstream consumes it as data. Re-collecting it under R2 would spend a
   §6.7 attempt to re-measure something already measured, on rows that are not
   in scope for this spec at all (§7.1).
2. **`B00`'s rows keep `spec_version = PRETRADE_EXT_COLLECTION_SPEC_V1`.** They
   are not rewritten, not re-stamped, and not migrated. The two files as
   submitted, and their recorded hashes, stand.
3. **`B01`…`B16` carry `spec_version = PRETRADE_EXT_COLLECTION_SPEC_V2`** and are
   collected in the R2 shapes: 26-column offer file, unchanged 31-column category
   file, and the §5.6 register.
4. **R1 and R2 rows may coexist in one file.** Any merge is keyed on the
   `spec_version` column, never on position, filename or collection date. A
   consumer that cannot read `spec_version` must not merge the two.
5. **Column migration on merge is mechanical and one-directional.** An R1 row
   entering a 26-column frame takes `NOT_APPLICABLE` in `duration_start_reference`
   and `undertaking_scope` — the honest reading, since R1 had no way to express
   either. An R2 row is never down-converted to 24 columns, because that would
   discard recorded facts.
6. **No §5.6 register is back-filled for `B00`.** Its absence for `B00` is
   expected and is not a validation failure; the validator applies §5.6's
   completeness check only to rows whose `spec_version` is V2.
7. **`issuer_lockup_days` / `shareholder_lockup_days` in `B00`.** `B00` recorded
   both as `DATA_NOT_FOUND` with `SPEC_EDGE_CASE_UNRESOLVED`, which was correct
   under R1. They are left exactly as they are. R2 does not reach back into a
   completed batch.
8. **The canonical record is untouched by all of the above**, as always (§2.6,
   §4.7, §9 item 1).

---

### 7.5 Transition from R2 to R3 (binding)

R3 changes one validation rule and no schema, so this transition has far less to
say than §7.4's. It is stated in full anyway, because a reader arriving at a batch
must be able to answer "which document validated this?" without inference.

1. **Nothing in §7.4 is repealed.** Every item of it — `B00` not repeated, `B00`'s
   rows keeping `PRETRADE_EXT_COLLECTION_SPEC_V1`, `B01`…`B16` carrying
   `PRETRADE_EXT_COLLECTION_SPEC_V2`, the merge keyed on `spec_version`, the
   one-directional column migration, no register back-filled for `B00`, `B00`'s
   two lock-up cells left as recorded, and the canonical record untouched —
   carries into R3 unchanged.
2. **The spec version string does not change.** `B01`…`B16` continue to write
   `PRETRADE_EXT_COLLECTION_SPEC_V2`. R3 is a document revision, not a schema
   version (header, §R3.2).
3. **No batch is re-collected.** No collector is asked to reopen a source, and
   `COLLECTOR_INSTRUCTION.md` is not reissued — check 12 imposes no collector
   obligation and never did.
4. **`B01` and `B02` were validated under R2 and stay validated under R2.** Their
   deliveries, hashes, validation reports, JSONs and acceptance decisions are
   unchanged (§R3.3 items 2–4).
5. **[AMENDED BY R4 §7.6 — the sentence R3 published is quoted first, then
   corrected. R3's own directory is untouched.]** R3 §7.5 item 5 as published
   reads: *"`B03` onward is validated under R3 (§R3.3 item 1)."* Under §7.6 it is
   corrected to: **R3 governs every validation run after the creation of the tag
   `frozen/collection-spec-r3` (2026-09-08 21:25:09 +03); validation runs before
   that moment — `B03`'s and `B04`'s among them — were governed by R2, and their
   acceptances stand (§R4.3, §R4.5 item 3).** A batch in flight at publication time
   is unaffected in what it must contain: the bytes that satisfy R2 satisfy R3.
6. **The `B01`/`B02` re-run ordered by §R3.3 item 5 is a measurement, not a
   re-validation.** It produces no verdict, changes no status, and writes only
   under `artifacts/derived/check12_revalidation/`.
7. **§7.3's post-`B04` systematic review still stands** and is not consumed by this
   revision. R3 was published after `B02` because a specific, already-diagnosed
   defect was in hand; that does not discharge the scheduled review, and a further
   revision remains available on the same §6.7 item 3 instrument.

---

### 7.6 When a revision takes effect (R4, binding on every revision)

R3 §7.5 was written so that a reader arriving at a batch could answer "which
document validated this?" without inference. It bound the answer to a batch
number, and the answer it produced was wrong for `B03` and `B04` (§R4.3). This
section replaces that mechanism, for this revision and for every future one.

1. **Effect begins at the tag.** A revision of this specification takes effect at
   the moment its annotated git tag is created, and not before. Effect is never
   bound to a batch number, a directory name, a file date, or the commit that
   publishes the text.
2. **Publishing is not enacting.** Between a revision's publication commit and its
   tag, the previous revision governs. A validation run in that window is correct
   under the previous revision, and is not defective for having applied it.
3. **A batch is validated under the revision in force when its validation runs.**
   Not when the batch was collected, not when it was delivered, not when it was
   accepted — when the validator ran.
4. **The batch record says which.** Every validation report and its JSON record
   the governing revision by directory name **and** by tag (for example
   `BORSAI_PRETRADE_EXTENSION_COLLECTION_SPEC_20260908_R3`,
   `frozen/collection-spec-r3`), together with the run timestamp that places it
   relative to that tag. A report that cannot name the tag in force names the
   previous revision, because an untagged revision is not in force.
5. **No revision names a batch number as its effective boundary.** Where a revision
   must state what it applies to, the form is "every validation run after this
   revision's tag" — never "from `Bn` onward".
6. **Completed batches are not re-validated by a later tag**, and no acceptance
   decision is reopened by one. A rule applied correctly under the revision then in
   force stays applied.
7. **The difference a later revision would have made may be measured**, report-only,
   under `artifacts/derived/`, and such a measurement changes no verdict, no status
   and no acceptance (§R4.6; R3 §R3.3 items 5–8 set the pattern).
8. **Applied to the record as it stands:** R1 in force from `frozen/collection-spec-v1`;
   R2 from `frozen/collection-spec-v2` (2026-09-06 22:54:45 +03), governing `B01`,
   `B02`, `B03` and `B04`; R3 from `frozen/collection-spec-r3`
   (2026-09-08 21:25:09 +03), governing every validation run after that moment and
   no batch validated before it; R4 from its own tag, once the operator creates it.
   R5 from its own tag, once the operator creates it.
   R6 from its own tag, once the operator creates it.

---

## 8. Batch validation — what the script must do

**No script is written by this task.** This section is the requirement list a
later, separately-authorized implementation task must satisfy. Validation is a
deterministic script's job, **not** a language model's: every check below is a
file comparison, a set membership test, a regex, a date comparison or a hash. A
model is not asked whether a batch "looks right".

Per batch, the validator must:

1. **Format** — UTF-8 BOM present, CRLF, delimiter, quoting, column count and
   column order exactly as §5.3 / §5.5 / §5.6; header match exact. Column count
   is resolved by `spec_version`: 24 for V1 offer rows, **26 for V2** (§7.4
   item 5).
2. **Membership** — every `ticker` in the batch appears in the §7.2 frozen table
   for that `batch_id`, and every ticker in that table appears in the file.
3. **Enums** — `field_status`, `scope_tag`, `source_document_type`,
   `source_priority`, `unit`, `duration_start_reference`, `normalized_category`,
   `category_level`, `is_aggregate`, `investor_count_semantic`,
   `total_demand_filter_status` all drawn from the frozen lists of §1.6 / §2.1 /
   §3.3 / §5.3. An unrecognised value is a `FAIL`, never a warning, never
   silently normalized. For a V1 row, `unit` is validated against R1's 10
   members; for a V2 row, against R2's 12.
4. **Field-name closure** — every `field_name` is one of the 22 of §2.1 (or
   `company_name`). An unknown field name is a `FAIL`. `price_stability_days`,
   `issuer_lockup_days` or `shareholder_lockup_days` appearing as a `field_name`
   in a V2 row is a `FAIL` (§9 item 11), not a warning.
5. **Sentinel discipline** — no empty cells; no `N/A`/`NA`/`-`/`null`/`None`; no
   `0` in a field whose `field_status` is `DATA_NOT_FOUND`; every
   `DATA_NOT_FOUND` row has a non-empty `search_scope`. For the demand-category
   file, that last obligation is met through the §5.6 register (check 16).
6. **Derivation** — compute `publication_timing_status` per §1.7 and
   `available_before_first_trade`, `verification_status`, `conflict_status` per
   §5.4; emit the 12-column provenance projection and the 29-column derived file.
   Assert the collector wrote none of these four columns, nor either of the two
   derived duration columns of §5.4.1.
7. **Conflict integrity** — every `SOURCES_CONFLICT` / `SCOPE_DIFFERENCE` /
   `SEMANTIC_DIFFERENCE` row shares its `conflict_group_id` with at least one
   other row; no `(ticker, field_name, scope_tag)` carries both a conflict row and
   a lone unmarked resolved row.
8. **Duplicates — three gates and two reports (R4, replaces R2/R3's check 8 in
   full; the second report added by R6, D1).**

   **Offer-level file, rows whose `field_name` is not §2.1 #15/#16/#17.**
   `(ticker, field_name, scope_tag, source_url)` must be unique. A repeat is
   `DUPLICATE_ROW_KEY`, a **`FAIL`**. Unchanged from R2/R3 in key and meaning, and
   unchanged in severity in every case but the one `(R6, D1)` defines below.

   **(R5, D4) What this key does not catch, and why that is not a defect.**
   Because the key carries `source_url`, two rows recording the **same field of the
   same ticker under the same scope from two different documents** are two distinct
   keys and are **not** a duplicate. They are exactly what §3.4 asks the collector
   to produce: each source recorded as its own row, agreement established
   downstream by the script comparing rows, never by the collector picking one and
   discarding the other. `DUPLICATE_ROW_KEY` fires only where the `source_url` is
   also the same — one document recorded twice. This note is interpretive: no key,
   no rule code and no severity changes (§R5.2).

   **(R6, D1) One case is reported rather than gated.** Where a colliding key
   group of more than one row satisfies **all three** of the following — every row
   carries a `conflict_group_id` other than `NOT_APPLICABLE`; those values are all
   identical; and every row carries a `field_status` from the conflict family
   (`SOURCES_CONFLICT`, `SCOPE_DIFFERENCE`, `SEMANTIC_DIFFERENCE`) — the collision
   is reported as `CONFLICT_FAMILY_ROW_KEY_COLLISION`, **report-only,
   informational, never gate-affecting**, naming the ticker, the field, the shared
   key, the shared `conflict_group_id`, and each colliding row's `field_status`,
   `normalized_value` and `page_or_section`. Those rows are what §4.1, §4.2 and
   check 7 oblige the collector to produce: one document stating one field under
   two semantics, both recorded, neither discarded, tied together by one group id.

   **In every other case `DUPLICATE_ROW_KEY` remains a `FAIL`**, and the key is
   unchanged. That expressly includes a group whose `conflict_group_id` is present
   on some rows and `NOT_APPLICABLE`, empty or absent on others: such a group is
   **not** a conflict family for this purpose and **is** a `FAIL`. The residual
   this accepts — two genuinely duplicated rows, symmetrically tagged into one
   group and both marked with a conflict-family `field_status`, are reported and
   not gated — is R4 D2's class of residual, narrower than it, and is argued in
   §R6.1(b). Evidence base: N = 1 (§R6.1(c)).

   **Offer-level file, rows whose `field_name` is §2.1 #15/#16/#17** (the duration
   fields). The key extends to
   `(ticker, field_name, scope_tag, duration_start_reference, undertaking_scope,
   source_url)`. A repeat of this key is reported as `DURATION_ROW_KEY_COLLISION`
   — **report-only, informational, never gate-affecting** — naming the ticker, the
   field, the shared key, and each colliding row's `normalized_value`, `unit` and
   `page_or_section` so a reader can see at once whether two distinct undertakings
   or one duplicated undertaking is in front of them.

   **It is not called a duplicate, because it is not one.** §2.1.1 item 2 makes two
   undertakings of the same field, from one document, differing in duration and
   unit, **two correct rows**; the extended key does not carry duration or unit and
   therefore cannot separate them. Coded as a `FAIL` under R2/R3 this clause
   produced 11 violations across `B01`, `B02` and `B04`, every one on
   `shareholder_lockup_undertaking`, every one on a correctly recorded pair, and
   0 true positives in 101 duration rows.

   **What still protects these rows.** Row preservation is enforced by the 1:1
   counter gate of `BORSAI_DURATION_DERIVATION_1TO1_RULING_20260908_T11.md` — one
   output row per input row, inequality is an error — which no uniqueness key can
   weaken; and check 15 already emits `MULTIPLE_UNDERTAKINGS` for the same rows.
   The residual this downgrade accepts, recorded rather than hidden: a genuine
   duplicate duration row is now reported and not gated. Measured exposure, 0 in
   101 rows.

   **Forbidden interim fix.** The key is **not** extended with `page_or_section`,
   `verbatim_source_phrase` or any other free-text column, notwithstanding that
   `+ page_or_section + normalized_value + unit` measures 0 residual collisions on
   all 101 delivered rows. A `FAIL` gate must not depend on a collector's free-text
   transcription choice (§R4.2(c)).

   **Deferred structural fix.** A typed undertaking identifier — an
   `undertaking_ordinal` per `(ticker, field_name, source_url)`, or the source's
   clause identifier as a typed field — restores a correct `FAIL` gate here. It
   needs a new column, a new `spec_version` and a reissued
   `COLLECTOR_INSTRUCTION.md`, so it belongs to a genuine schema revision and is
   recorded in §R4.2(c) for it, not implemented here.

   **Demand-category file.** `(ticker, normalized_category, source_category_label,
   source_url)` must be unique. A repeat is `DUPLICATE_ROW_KEY`, a **`FAIL`**.
   Unchanged.

   **§5.6 cell-status register.** `(ticker, normalized_category,
   source_category_label, field_name)` must be unique. A repeat is
   `DUPLICATE_ROW_KEY`, a **`FAIL`**. Unchanged — and deliberately so: §5.6 binding
   rule 1 ("two rows for one cell is a `FAIL` (§8 check 8)") depends on this gate
   and is preserved by leaving it untouched.

   **Severity summary.**

   | rule code | severity |
   |---|---|
   | `DUPLICATE_ROW_KEY` (offer non-duration, demand-category, register) | `FAIL` |
   | `DURATION_ROW_KEY_COLLISION` (offer, §2.1 #15/#16/#17) | report-only, never gate-affecting |
   | `CONFLICT_FAMILY_ROW_KEY_COLLISION` (offer non-duration, only where all three `(R6, D1)` conditions hold) | report-only, never gate-affecting |

9. **Canonical immutability** — recompute and compare the sha256 of every frozen
   canonical Historical99 artifact and of the config schema TOMLs. Any change is a
   hard `STOP`, per `CLAUDE.md` §8.
10. **Canonical agreement** — for fields already populated for the 79 (§2.6, §2.3),
    compare the collected value against canonical and emit a
    `CANONICAL_DISAGREEMENT` list. **Report only.** No write-back, ever.
11. **Aggregate/leaf guard and percentage-base reconstruction (R4, replaces
    R2/R3's check 11 in full).**

    Two branches over the demand-category file. Both are gates; both degrade to
    `uncheckable`, never to "passed", on an input they cannot evaluate. Neither
    ever "fixes" anything: no row is dropped, merged or corrected, under any
    branch, for any reason.

    **Branch A — additive fields. Unchanged from R2/R3 in every respect.**

    Fields: `applicant_count`, `allocated_investor_count`, `order_count`,
    `planned_allocation_shares`, `demand_nominal`, `distributed_nominal`.

    A **category family** is identified as §2.2's reused nesting defines it: an
    `AGGREGATE` row's `source_category_label` is the `source_parent_label` its
    `LEAF` children carry, within one `(batch_id, ticker)`. A family exists, and is
    compared, only where at least one `LEAF` row names that `AGGREGATE` row's label
    as its parent. For each family and each additive field, the leaf values are
    summed and compared against the aggregate cell at the **aggregate cell's own
    printed precision** (`ROUND_HALF_UP`, the convention already declared once for
    checks 11 and 12; for integer counts this reduces to exact equality). A
    mismatch is `AGGREGATE_LEAF_DIVERGENCE` — a **violation, gate-affecting**. A
    family/field combination in which the aggregate cell or any leaf cell is not a
    plain decimal is `uncheckable` and is counted, never matched and never diverged.

    **Branch B — percentage fields. New.**

    Fields, each with its nominal partner in the **same row** and in the base row.
    The pairing is §2.2's own and is not invented here:

    | percentage field | nominal partner |
    |---|---|
    | `planned_allocation_pct` | `planned_allocation_shares` |
    | `demand_share_pct` | `demand_nominal` |
    | `distributed_pct` | `distributed_nominal` |

    **Step A — the percentage base.** For each `(batch_id, ticker)` and each
    percentage field independently, the **base row** is the row of that ticker for
    which, in **that** percentage field, `category_level = AGGREGATE`,
    `is_aggregate = TRUE`, and the printed cell parses as a plain decimal equal to
    `100` at its own printed precision. It is the row the source designates as the
    whole by printing the whole.

    The base is identified **structurally and never by category label.** No
    `source_category_label` string, in any language or casing, participates in this
    rule. (Measured over `B00_codex_r2`…`B04`: exactly one base row in 57 of 57
    `(ticker, percentage field)` groups holding any numeric cell; all 57 are
    `AGGREGATE`/`TRUE`.)

    - Zero or more than one such row → every percentage cell of that field for that
      ticker is `uncheckable`, bucket `no_unique_percentage_base`.
    - The base row exists but its own nominal partner is not a plain decimal, or is
      zero → same consequence, bucket `percentage_base_nominal_unusable`.

    **Step B — per-cell reconstruction.** For every row of the ticker whose
    percentage cell parses as a plain decimal:

    - if that row's own nominal partner is not a plain decimal (`DATA_NOT_FOUND`,
      `SOURCES_CONFLICT`, `NOT_APPLICABLE`, or unparsable), the cell is
      `uncheckable`, bucket `cell_nominal_not_numeric` — never passed;
    - if the row **is** the base row, it is counted under `base_cells` and not
      compared: `base ÷ base × 100` is `100` by construction and carries no
      information. The surface is reported without it, so that the check's pass
      count is never inflated by cells that cannot fail;
    - otherwise compute

      ```
      round( own nominal ÷ base nominal × 100 , p )      p = the number of decimal
                                                             places THIS cell is
                                                             printed at
      ```

      with `ROUND_HALF_UP`, and compare to the printed cell.

    **Step C — severity.** A disagreement is
    `PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH` — a **violation, gate-affecting**.
    Nothing is corrected: `calculation_mismatch_policy =
    REPORT_ONLY_NO_AUTOMATIC_CORRECTION` governs **correction**, never severity,
    exactly as R3 §8 check 12 Step C states for check 12. The words "report only"
    in R2's and R3's check 11 carried that same meaning — never rewrite a row — and
    are restated here unambiguously so that the branch's severity cannot be read
    off an ambiguous phrase: both branches of this check are gate-affecting, and
    both were gate-affecting in the validator as implemented under R2 and R3.

    **What this branch replaces, and why.** R2/R3 compared the **sum of printed
    leaf percentages** against the **printed aggregate percentage**. The source
    asserts no such equality: it asserts that each printed percentage is that
    part's share of the whole. The replaced comparison is `round(a) + round(b)`
    against `round(a + b)`, which diverges by exactly one ulp whenever the two
    fractional remainders carry — measured 4 divergences in 13 comparisons, against
    0 in 24 additive comparisons. §R4.1 carries the demonstration and the four
    worked cases.

    **Coverage reporting.** `check_11_aggregate_leaf_guard` keeps its existing
    shape and its existing counters (`families_evaluated`,
    `field_comparisons_uncheckable`, `uncheckable_breakdown` with
    `aggregate_cell_not_numeric` and `leaf_cell_not_numeric`) for Branch A,
    unchanged in name and meaning, and gains a sibling block
    `check_11_percentage_base_reconstruction` reporting, per batch and per ticker:
    the base row identified for each percentage field and its nominal,
    `cells_checked`, `cells_matched`, `base_cells`, and an `uncheckable_breakdown`
    over `no_unique_percentage_base`, `percentage_base_nominal_unusable` and
    `cell_nominal_not_numeric`. An uncheckable cell is never reported as a pass —
    the check must not present a narrower surface as a cleaner one.

    **Severity summary.**

    | rule code | severity |
    |---|---|
    | `AGGREGATE_LEAF_DIVERGENCE` (Branch A, additive) | violation, gate-affecting (retained unchanged) |
    | `PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH` (Branch B, percentage) | violation, gate-affecting (R4, new) |

    **Worked example, from collected `B03` bytes.** AGROT records
    `demand_nominal = 648991222` on `Yurt İçi Kurumsal Yatırımcılar` and
    `demand_nominal = 994250802` on `TOPLAM`, whose `demand_share_pct` is `100`;
    the leaf's printed `demand_share_pct` is `65.27`. Step A designates `TOPLAM`;
    Step B computes 648,991,222 ÷ 994,250,802 × 100 = 65.2745… → `65.27` at the
    cell's own 2-dp precision → match, no violation. Had the collector dropped a
    digit and written `64899122`, the quotient is `6.53 ≠ 65.27` and check 11
    raises `PERCENTAGE_BASE_RECONSTRUCTION_MISMATCH`, correctly and
    gate-affectingly. **Under R2/R3 the same error raises nothing at all**: AGROT's
    two `LEAF` rows carry `source_parent_label = DATA_NOT_FOUND`, so no family
    exists and check 11 evaluates zero comparisons for this ticker — one of 18 such
    tickers in the 25 delivered.

12. **Arithmetic consistency — filter-aware, report-only (R3, replaces R2's
    check 12 in full).**

    **Fields.** #1 `demand_shares_unfiltered`, #2 `demand_shares_filtered`,
    #3 `shares_offered_denominator`, #4 `total_demand_multiple_value`,
    #5 `total_demand_filter_status` — all §2.1, all offer-level.

    **Step A — pairing, unchanged from R2.** A numerator row (#1 or #2) is paired
    with the #3 row of the **same** `scope_tag`; that pairing is compared against
    the #4 row of the same `scope_tag` if one exists, else against the ticker's
    single #4 row if there is exactly one, else the pairing is uncheckable. Only
    `field_status = VALUE_RECORDED` rows are used; every other status makes a row
    "not present" for this check and is counted, never guessed and never averaged
    (§9 item 4). R3 changes nothing in this step.

    **Step B — the filter gate (R3).** Before comparing, read the ticker's #5 row.
    #5 records **which numerator the source itself divided by**; that is its
    defined semantics (§2.1 #5, "Whether the source describes its total as
    filtered, unfiltered, or leaves it open"), and it is carried in the frozen
    enum of §1.6, whose members are exactly `FILTERED`, `UNFILTERED`,
    `NOT_SPECIFIED`, `NOT_APPLICABLE`, `DATA_NOT_FOUND` — inherited from
    `config/ipo_master_schema_v2.toml` and **not extended by this revision**. The
    source's verbatim sentence is separately carried in #6
    `total_demand_definition`, which this check reads for its report text and
    never parses for a value.

    | #5 | designated numerator | the other numerator |
    |---|---|---|
    | `UNFILTERED` | #1 — compared | #2 — **not compared** |
    | `FILTERED` | #2 — compared | #1 — **not compared** |
    | `NOT_SPECIFIED` | undetermined — both compared, Step D applies | — |
    | `DATA_NOT_FOUND` | undetermined — both compared, Step D applies | — |
    | `NOT_APPLICABLE` | none — Step E applies | — |

    A pairing suppressed by this gate is **`NOT_APPLICABLE` for this check**: it is
    counted in the coverage breakdown under `filter_status_excludes_numerator` and
    is never reported as a divergence, never as a pass.

    **Why `NOT_APPLICABLE` and not "compare it against something else".** The
    source publishes exactly one multiple, computed from exactly one numerator it
    names. There is no second published multiple for the other numerator, so there
    is no comparable denominator for that comparison to have — the missing term is
    not the divisor but the **published result** to check against. Manufacturing
    one (asserting that DOFER's filtered multiple "should" read 4.33) would be
    writing a value no source states, which §9 item 5 forbids and which this check
    has no licence to do: check 12 verifies a source's published arithmetic
    against itself; it does not recompute the source. `NOT_APPLICABLE` is
    therefore the correct ruling, and the alternative — comparing #2/#3 against a
    multiple the source derived from #1 — is exactly the defect §R3.1 closes.

    **Step C — comparison, unchanged from R2.** For each compared pairing, divide
    numerator by denominator, quantize to the number of decimal places #4 is
    stated at, and compare to #4. A mismatch is
    `ARITHMETIC_CONSISTENCY_DIVERGENCE` — a **violation**, gate-affecting, exactly
    as under R2. Nothing is corrected: `calculation_mismatch_policy =
    REPORT_ONLY_NO_AUTOMATIC_CORRECTION` governs **correction**, never severity,
    and did not make this rule advisory under R2 and does not under R3.

    **Step D — undetermined filter status (`NOT_SPECIFIED` / `DATA_NOT_FOUND`).**
    The two values differ in meaning — the source left the screen open, versus the
    collector could not establish it — but they put this check in the identical
    epistemic position: which numerator produced #4 is unknown, so neither can be
    designated and neither can be excluded. Both are compared. Then:

    - if **at least one** compared pairing matches #4, any diverging pairing is
      reported as `ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER` — **report-only,
      not gate-affecting** — naming the matching numerator, since the matching
      reading is the one the source most plausibly used and the divergence is the
      same definitional artefact Step B excludes where #5 is explicit;
    - if **no** compared pairing matches #4 (including the case where only one
      numerator was recorded at all), it is
      `ARITHMETIC_CONSISTENCY_DIVERGENCE` — a violation. Under every available
      reading of the source, its own three published figures disagree.

    **Step E — `NOT_APPLICABLE` and the contradiction gate (R3, new).** Under
    `artifacts/governance/spec_clarify_r1/CLARIFICATION.md` §1 (C1),
    `total_demand_filter_status = NOT_APPLICABLE` means the source published **no
    total demand multiple at all** — the status has no referent. Therefore:

    - #5 = `NOT_APPLICABLE` **and** #4 `VALUE_RECORDED` → the batch contradicts
      itself: `FILTER_STATUS_MULTIPLE_CONTRADICTION`, a **`FAIL`**. Either the
      multiple exists, in which case #5 must be `FILTERED`, `UNFILTERED` or
      `NOT_SPECIFIED`, or it does not, in which case #4 cannot be a recorded
      value. The two rows cannot both be right.
    - #5 ∈ {`FILTERED`, `UNFILTERED`} **and** #4 not `VALUE_RECORDED` → the same
      contradiction in mirror image, same rule code, same `FAIL`: a filter status
      asserted about a multiple that was not recorded.
    - #5 = `NOT_APPLICABLE` and #4 not `VALUE_RECORDED` → consistent. No triple
      exists; every pairing is uncheckable, as it already is under R2.

    **Step F — designated numerator absent (R3, new).** Where #5 designates a
    numerator whose row is not `VALUE_RECORDED` while the **other** numerator is
    recorded, emit `ARITHMETIC_CONSISTENCY_NOT_COMPARABLE` — **report-only, not
    gate-affecting** — naming the ticker, #5's value, both numerators' statuses
    and the recorded one. It is never a divergence. The source's own numerator was
    not published; comparing the other against a multiple the source did not
    compute from it is precisely the false positive this revision removes. The
    pairing is counted under `designated_numerator_not_value_recorded`.

    **Coverage reporting.** `check_12_arithmetic_consistency` keeps its existing
    shape and its existing bucket names (`no_unique_denominator_for_scope`,
    `no_unique_total_demand_multiple_for_scope`, `non_value_recorded_status`,
    `non_numeric_value`, `zero_denominator`) with unchanged meanings, and gains
    `filter_status_excludes_numerator` and
    `designated_numerator_not_value_recorded`. A suppressed pairing is uncheckable,
    never passed — the check must not report a narrower surface as a cleaner one.
    The per-batch report states, for every ticker, the #5 value it applied and the
    numerator it designated, so a reader can audit the gate rather than infer it.

    **Severity summary.**

    | rule code | severity |
    |---|---|
    | `ARITHMETIC_CONSISTENCY_DIVERGENCE` | violation, gate-affecting (retained from R2, narrowed) |
    | `FILTER_STATUS_MULTIPLE_CONTRADICTION` | `FAIL` (R3, new) |
    | `ARITHMETIC_CONSISTENCY_UNDETERMINED_FILTER` | report-only (R3, new) |
    | `ARITHMETIC_CONSISTENCY_NOT_COMPARABLE` | report-only (R3, new) |

    **Worked example, from collected `B02` bytes.** BINHO records #5 = `FILTERED`,
    #2 = `18236370`, #3 = `9500000` (both `EXCL_ADDITIONAL`), #4 = `1.92`.
    Step B designates #2; Step C computes 18,236,370 / 9,500,000 = 1.91962… → 1.92
    at #4's stated precision → match, no violation. Had the collector transcribed
    #3 as `95000000`, the quotient is 0.19 ≠ 1.92 and check 12 raises
    `ARITHMETIC_CONSISTENCY_DIVERGENCE`, correctly and gate-affectingly, on the
    numerator the source actually used. The check remains a gate; what it no longer
    does is fire on a numerator the source never used.
13. **Outcome firewall** — assert no column, value or note in the batch contains a
    post-listing price, return or OHLCV field; assert no outcome path was read
    while producing the batch; emit `REALIZED_OUTCOME_READS = 0`.
14. **Manifest** — sha256 of both CSVs, row counts **derived from the actual
    files**, never compared against a hardcoded historical constant
    (`CLAUDE.md` §23).
15. **Duration-field integrity (R2)** — for every §2.1 #15/#16/#17 row: `unit` is
    one of `DAYS`/`MONTHS`/`YEARS`; `duration_start_reference` and
    `undertaking_scope` are not `NOT_APPLICABLE`; `normalized_value` is a plain
    decimal or `DATA_NOT_FOUND`. For every other field name, both R2 columns are
    `NOT_APPLICABLE`. Where a ticker carries more than one undertaking of the same
    type, emit them as a `MULTIPLE_UNDERTAKINGS` report item — informational, not
    a failure, since §2.1.1 item 2 makes this the correct recording. A `0` on #15
    is a legitimate source-stated value and is never reported as an absence.
16. **Cell-status register completeness (R2)** — every demand-category data cell
    holding `DATA_NOT_FOUND` in a V2 batch has exactly one §5.6 register row;
    every register row resolves to an existing category row and a `field_name`
    among the 15; every register row with `field_status = DATA_NOT_FOUND` has a
    non-empty, non-generic `search_scope`. A missing register row is a `FAIL` —
    it is the §4.4 obligation going unmet. Applies only to `spec_version = V2`
    rows (§7.4 item 6).
17. **Report** — a per-batch validation JSON in the shape already used by
    `artifacts/ipo_master/batches/batch_0N_validation.json`: universe block,
    schema block, enum block, temporal block, coverage block, `scope_guards`
    (`ohlcv_collected: false`, `performance_analysis_run: false`,
    `v1_model_built_or_fit: false`, `live_forecast_track_touched: false`),
    `protected_hashes`, and a single `status` of `PASS` / `PASS_WITH_WARNINGS` /
    `FAIL`.

---

## 9. Standing prohibitions for the collector

1. Never modify any existing repository file. Collection output goes only to new
   files under `work/pretrade_extension/`.
2. Never change f3 or any total-demand column (§2.3).
3. Never read or record a post-listing outcome (§0.4).
4. Never average, pick, or rank away a conflict (§4.3).
5. Never write a value the source does not state, in any field, for any reason,
   including "it is obviously implied".
6. Never fold a `DATA_NOT_FOUND` into `0`.
7. Never treat collection as admission: a collected field is not a feature, is not
   `OFFICIAL_VERIFIED`, and is not eligible for any model until a separate
   preregistration admits it.
8. Never re-select the calibration set (§6.7).
9. Never collect batches ahead of validation (§7.3).
10. When uncertain: do not guess. Record the ambiguity with its verbatim phrase and
    escalate (`CLAUDE.md` §31).
11. **(R2)** Never write a script-derived field. `publication_timing_status`,
    `available_before_first_trade`, `verification_status`, `conflict_status`,
    `total_demand_multiple_origin`, `price_stability_days`, `issuer_lockup_days`
    and `shareholder_lockup_days` are assigned downstream (§1.7, §2.3 item 5,
    §5.4, §5.4.1). A batch containing any of them as a collector-written
    `field_name` is invalid.
12. **(R2)** Never convert a duration into another unit. Record the magnitude and
    the unit the source printed (§2.1.1). This is item 5 applied to duration
    fields, not an exception to it.
13. **(R5)** Never treat the live company record as a point-in-time record.
    Outside the single exception of §2.1 and §R5.1 item 3 — a record opened on or
    before the ticker's `first_trading_date` — a value read from
    `KAP_COMPANY_RECORD` is `AS_OF_RETRIEVAL` for every field it supplies, and
    `AS_OF_LISTING` requires a document published on or before that date. Reading a
    listing-date value off a current page is item 5 applied to scope, not an
    exception to it.

**R2 note on item 5.** Item 5 is carried into this revision **verbatim and
undiminished**, and this revision exists in the shape it does *because* of it.
The R1-era gap was not that item 5 was too strict; it was that the schema gave
the collector nowhere to put what the source actually said, leaving silence as
the only compliant answer. R2 removes that dilemma by widening what can be
recorded, never by widening what may be invented. Item 12 makes the application
to durations explicit, and §5.4.1 puts the one act item 5 forbids the collector —
computing a day count — in a versioned, auditable, reversible script instead.
Nothing here licenses a collector to write an unstated value in any field, for
any reason, including that it follows arithmetically.

**R2 note on §6.2.** §6.2's binding mitigation is likewise carried over
undiminished: the collector records what the source in front of it says, and must
not use any fill expectation as a reason to write `DATA_NOT_FOUND` without
searching, or to doubt a value it did find. R2 *strengthens* this rather than
weakening it: §5.6 requires a per-cell `search_scope` naming documents actually
opened for every absent demand-category cell, which is exactly the check that
makes an unsearched absence detectable — a check the category file previously had
no column to support.

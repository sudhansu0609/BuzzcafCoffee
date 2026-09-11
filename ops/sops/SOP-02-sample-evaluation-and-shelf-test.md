---
title: SOP-02 Sample evaluation and the four-week shelf test
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: Blind tasting the way Indian customers drink instant coffee, plus the caking/aroma test that was skipped in 2023.
---

# SOP-02 Sample evaluation and the four-week shelf test

## Part A — Tasting (day 1)

**Taste blind.** Decant each supplier's sample into identical unmarked jars coded A/B/C. Someone else holds the key.

**Taste the way the customer drinks it.** Indian instant coffee is mostly drunk with milk and sugar, and very often cold. A flavour that reads pleasant black can vanish in milk; one that is cloying black can be right in a latte. For every sample, at the dose printed on the pack:

| Prep | What to check | Score 1–5 |
|---|---|---|
| Black, hot | Does the flavour taste like the thing it claims (hazelnut, caramel, chocolate) or like a generic sweet note? Chemical aftertaste? | |
| With milk + sugar, hot | Does the flavour survive milk? Bitterness balance? | |
| Cold coffee (blended with cold milk, ice) | Dissolves fully? Flavour still present? | |
| Dissolution | Stir into hot and cold water; any residue or floating specks? | |
| Appearance | Granule colour, uniformity, free-flowing | |

Record scores per sample in Ops → Suppliers → `sample_result` and attach the sheet to notes. A sample scoring under 3 on "tastes like what it claims" is out, regardless of price.

## Part B — Four-week shelf test (days 1–28)

Instant coffee is hygroscopic: it pulls moisture from air, clumps, cakes into a block and loses aroma. A jar fine on arrival can be a brick two months later, and the customer reads that as a cheap product. The 2023 clumping/stale complaints were almost certainly this.

Set up **six jars per front-runner** (use the supplier's actual jar and seal if they supply them):

| Jars | Condition | Simulates |
|---|---|---|
| 2 | Sealed, room temperature, dark cupboard | Warehouse / FBA |
| 2 | Sealed, warm and humid (bathroom shelf or near the kitchen) | Monsoon, Chennai/Kolkata shelf |
| 2 | Opened and re-closed twice daily with a dry spoon | Customer use |

Weekly (days 7, 14, 21, 28) note for each jar: caking (none / soft lumps / hard lumps / solid), aroma (strong / faded / off), taste (as day 1 / faded / off), seal integrity.

**Pass:** no hard caking in any jar; aroma and taste still clearly present at day 28 in the opened-daily jars. Anything else is a **fail** — either the coffee, the jar, or the seal is wrong, and it is the supplier's job to say which.

Record in Ops → Suppliers → `shelf_test_result`. Keep the day-28 jars as the pre-launch reference sample.

## Part C — What this costs

Nothing except the paid samples (₹5–8k across suppliers) and four weeks. It is exactly the step that was skipped last time. Do not commit the production budget until Part B is finished for the chosen supplier.

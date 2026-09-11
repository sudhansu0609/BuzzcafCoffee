---
title: SOP-03 Batch receiving and QC (six checks)
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: What happens to every delivery before a single unit goes to Amazon or a customer.
---

# SOP-03 Batch receiving and QC

**Rule:** only after all six checks does stock go to FBA or to a customer. A bad batch discovered at an Amazon warehouse is expensive to remove and damages account health — the account is the most valuable thing the company owns.

Open a new record in Ops → Batches the day the delivery arrives. Tick each check there; the batch page shows what is missing.

## The six checks

| # | Check | How | Fail → |
|---|---|---|---|
| 1 | **Paperwork** | COA present for *this* batch number. Batch number legible on jars. Manufacture and best-before dates on the COA, the invoice and the label all agree. | Do not unpack further. Call the supplier. |
| 2 | **Open one unit** | Aroma, colour, free-flowing granules, no clumps. Brew a cup hot and a cold coffee. Compare with the SOP-02 reference jar. | Quarantine the batch. Photograph. |
| 3 | **Label vs artwork** | Both FSSAI numbers (theirs + 11522079000056), "Manufactured by" and "Marketed by", net quantity, MRP incl. taxes, batch, dates DD/MM/YYYY, veg symbol, consumer care, storage line. A wrong label is a recall, not a reprint. | Batch cannot ship until relabelled. |
| 4 | **Fill weight and seal** | Weigh five jars; each ≥ declared net quantity (allow +, never −). Induction seal intact on all five — a failed seal becomes a caked jar and a one-star review. | Weigh 20 more; if >1 short, reject. |
| 5 | **Two retention samples** | Two sealed jars, labelled with batch number and date, stored in the retention box, kept until best-before + 6 months. Log them under Batches → Retention samples. | — |
| 6 | **Log it** | Batch, dates, quantity received, supplier, COA reference (file in `vault/09-batches-coa/COA-<batch>.pdf`), destination (own stock / FBA shipment ID). Set QC result. | — |

## After the checks

- Set `qc_result` = pass. Record `qty_received`; keep `qty_remaining` current (SOP-12).
- Create the FBA shipment (SOP-06) or move to own-stock shelf.
- If **fail** or **quarantine**: photograph everything, email the supplier the same day quoting the agreement's defective-batch clause, log the outcome in the batch notes, and open a Task.

## Why this is also the recall trail

The batch record + COA + retention samples + complaints logged against the batch number are exactly what FSSAI expects a relabeller to produce on request, and what settles a dispute with a customer or the supplier. Three complaints on one batch is a pattern — see SOP-05.

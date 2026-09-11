---
title: SOP-05 Complaint handling and the recall trail
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: Log every complaint against a batch, respond plainly, and know when three complaints become a supplier conversation or a recall.
---

# SOP-05 Complaint handling and the recall trail

## 1. Log first, then reply

Every complaint, from any channel, goes into Ops → Complaints the day it arrives, with the **batch number** from the jar (ask the customer for a photo of the base/label if they can). "unknown" is acceptable but should be rare.

Fields that matter: date, channel, product, batch, issue category, severity, action.

| Severity | Meaning | Response time |
|---|---|---|
| low | Preference ("too sweet"), delivery delay | 48 h |
| medium | Clumped, faded, damaged jar, wrong item | 24 h |
| high | Off taste/smell, foreign matter, broken glass | same day |
| safety | Illness reported, contamination suspected | immediately — and go to §4 |

## 2. Reply plainly

- Amazon: reply through Buyer-Seller Messaging; answer questions on the listing yourself. Never ask for a rating change; never offer anything in exchange for a review.
- Website/Instagram/WhatsApp: one message, human, with a fix: replacement, refund, or a brewing tip if it is a preparation issue (a lot of "tastes bad" is dose or water temperature — the how-to card exists for this).
- Record the action and mark resolved with a date.

## 3. Patterns

The dashboard flags **three or more complaints on one batch**. That is a pattern, not bad luck:

1. Open the retention samples for that batch (Batches → Retention samples → status "opened for investigation"). Compare with the SOP-02 reference.
2. Email the supplier the same day with the complaint summaries, the COA reference and your retention-sample findings. Quote the defective-batch clause.
3. Decide: continue selling / pull remaining stock from FBA (create a removal order) / hold own stock.
4. Log the decision in Ops → Decisions.

## 4. Recall (safety or regulator-driven)

FSSAI expects a relabeller to have a recall plan. Ours:

1. **Identify** the batch(es) from the complaint and the batch register. The register shows quantity received, where it went (FBA shipment ID / own stock), and remaining stock.
2. **Stop** — pause the Amazon listing(s) for that batch's ASIN, block the SKU on the website, remove from FBA via removal order.
3. **Notify** the manufacturer in writing the same day; they hold the production records.
4. **Inform** FSSAI (designated officer, FDA Maharashtra Pune) if the issue is a safety hazard, per the Food Recall Procedure Regulations. Keep a copy of the notice in `vault/03-fssai/`.
5. **Contact customers** who bought that batch: Amazon order reports by date range; website orders by batch (the fulfilment record notes batch per order, SOP-07). Offer refund/replacement.
6. **Evidence**: retention samples, COA, lab test if commissioned (Ops → Lab tests), complaint log, correspondence. This is what the annual return and any inspection will ask for.
7. **Close** with a decision entry: root cause, supplier remedy, what changes.

## 5. Praise counts too

Log five-star reviews that mention something specific as issue "praise". They tell you what to put on the listing.

---
title: SOP-12 Daily inventory reconciliation across Amazon and the website
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: Keeping one truthful stock number when the same jars are listed on Amazon and buzzcaf.com.
---

# SOP-12 Daily inventory reconciliation

The same physical stock is sold on Amazon (FBA) and on our website with **no shared inventory count**. Overselling on Amazon damages seller metrics and is hard to recover from. Below roughly 30 orders a day a disciplined manual ritual is genuinely fine — as a fixed ritual, not a good intention. Above that, move to Easyecom or Unicommerce.

## The split

FBA stock and own stock are **physically separate pools**. FBA units are only sold on Amazon; own-stock units are only sold on the website. There is no overselling *between* channels if this rule holds; the reconciliation is about keeping the numbers honest and reordering in time.

## Daily (with the SOP-07 ritual)

1. Website admin → Inventory: on-hand per SKU. Compare with the shelf count for anything that sold yesterday. Fix the number in admin if it is wrong; note why.
2. Ops → Batches: reduce `qty_remaining` on the batch(es) picked yesterday.
3. Amazon → Inventory: fulfillable units per SKU. Note in the daily log if under the reorder threshold.

## Weekly

- FBA inventory report vs Ops batch records for FBA destinations: reserved, unfulfillable and inbound units explained.
- Own shelf: full physical count of jars by batch; matches Ops within ±0.

## Reorder rule

Weeks of cover = fulfillable units ÷ average weekly sales (last 4 weeks). Reorder when cover < production lead time + 2 weeks (e.g. 3-week lead → reorder at 5 weeks' cover). Never go out of stock on Amazon: ranking loss outlasts the stock-out.

## Log

A single sheet (or Ops → Tasks note) per day: date, SKU, website on-hand, FBA fulfillable, discrepancy, action. Monthly it feeds SOP-08 step 7.

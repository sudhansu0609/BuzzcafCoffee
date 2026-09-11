---
title: SOP-11 Content and product placement across the Buzzcaf Media channels
version: 1.0
last_reviewed: 2026-09-07
owner: Sudhansu
summary: How the coffee shows up in the YouTube channels and Instagram without becoming an ad, and how every mention is traceable to orders.
---

# SOP-11 Content and product-placement workflow

Buzzcaf Media already runs five YouTube channels (Beyond3Baje, Spilled Coffee After Dark, Life3Baje, Khayal3Baje, Spilled Coffee Studio) through BuzzcafAI Studio. The coffee brand shares the name. That is an asset most small food brands do not have — and it is only worth something if the placement is honest, consistent and measurable.

## 1. Principles

- **Disclose.** Every video that shows or mentions the coffee carries "Buzzcaf is our own coffee brand" in the description and, if it is the topic of the video, on screen. ASCI guidelines apply to self-promotion too; YouTube's paid-promotion flag is *not* needed for your own product, but honesty is.
- **Presence, not pitch.** The jar on the desk, the cup in hand, one line in the outro. A 30-second hard sell every episode burns the audience.
- **One link, one code per channel.** So you know which channel actually sells.

## 2. Standard assets (kept in `youtube/` at the project root, owned by the website team)

- Description block (3 lines + link + code) per channel.
- Pinned comment text.
- End-screen element: the product page link with UTM.
- Lower-third / overlay PNG with the jar and the code.
- Landing page `buzzcaf.com/yt/<channel>` that applies the channel coupon automatically.

## 3. Attribution

| Channel | Coupon code | UTM source |
|---|---|---|
| Beyond3Baje | B3B10 | beyond3baje |
| Spilled Coffee After Dark | AFTERDARK10 | afterdark |
| Life3Baje | LIFE10 | life3baje |
| Khayal3Baje | KHAYAL10 | khayal3baje |
| Spilled Coffee Studio | STUDIO10 | studio |
| Instagram | INSTA10 | instagram |

Website admin → Coupons shows redemptions per code; GA4 shows sessions per `utm_source`. Review monthly in SOP-08 step 12.

## 4. Workflow per video (added as a step in the BuzzcafAI workflow)

1. **Script stage**: writer adds one natural mention where it fits (a cold-coffee break, a "what I'm drinking" aside). Not forced; skip if it does not fit.
2. **Shoot**: jar visible, label facing camera, in at least one wide shot. For the recipe/how-to videos the coffee *is* the content.
3. **Edit**: end-screen element + lower-third in the last 20 s.
4. **Publish**: description block + pinned comment from the standard asset for that channel. Check the link resolves and the code applies.
5. **Log**: Ops → Tasks or BuzzcafAI project note: video URL, channel, publish date. Monthly: orders per code.

## 5. Recipe content engine

Instant coffee in India is drunk cold, with milk, as dalgona, as mocha. Recipe shorts are the highest-value content: useful, searched, show the product in use, and each shoot yields (a) a YouTube Short, (b) an Instagram Reel, (c) a website how-to page, (d) a listing image. One shoot, four uses. Batch-shoot 4–6 recipes in one session per month.

## 6. What not to do

- No giveaway-for-reviews, no "rate us 5 stars" on Amazon links — account risk.
- No health claims ("boosts metabolism", "sugar-free" unless it literally is and the label says so).
- No showing the old label (it names Buzzcaf as manufacturer — no longer true).

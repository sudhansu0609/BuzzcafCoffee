# Promotion Plan — Sep to Nov 2026

Budget for paid media inside this window: **₹0 until 15 genuine Amazon reviews**, then ₹5,000–10,000/month on Amazon Sponsored Products only. Everything else here is owned media, and the biggest owned asset is the five YouTube channels under Buzzcaf Media.

## 1. The engine: YouTube (Buzzcaf Media)
Channels: Beyond3Baje, Spilled Coffee After Dark, Life3Baje, Khayal3Baje, Spilled Coffee Studio. Two of them literally have "coffee" in the name. Nobody else launching an instant coffee brand in India has this.

### 1a. Standing integration on every upload (from the next video)
Ready-to-paste copy is in `youtube/`.
1. **Description block** — first 3 lines above the fold: "☕ This video is fuelled by Buzzcaf — our own instant coffee. 10% off with BEYOND10 → buzzcaf.com/yt?c=beyond3baje". Channel-specific code and link (UTM built in).
2. **Pinned comment** — same offer, one line, posted within a minute of publish.
3. **End screen** — 20 s: the jar on screen, the code on a lower-third; end-screen element links to the site (needs the site added as an associated website in YouTube Studio → Settings → Channel → Advanced; requires Google Search Console verification of buzzcaf.com — the site ships the verification meta tag via env).
4. **Product placement** — the jar and a made cup visible on the desk in every talking-head shot. Never a sales pitch mid-video; just present. This is the compounding part.
5. **Community post** every fortnight per channel: recipe, behind-the-scenes, batch arriving, first orders.
6. **Channel banner + links section**: "Buzzcaf Coffee" link in the channel header links (all 5).
7. **YouTube Shopping**: once the site is live and eligible (channel in YPP or 10k+ subs), connect the store via YouTube Studio → Earn → Shopping → "Connect store" (Shopify / other via Google Merchant Center). We keep a Merchant Center product feed at `/api/feeds/merchant.xml` for this — Phase 2.

### 1b. Dedicated coffee content (one per fortnight, rotating channels)
| Date | Channel | Video | Purpose |
|---|---|---|---|
| ~20 Oct | Spilled Coffee Studio | "I restarted my coffee company. Here's everything that went wrong the first time." | Launch story; honest; drives site |
| ~27 Oct | Spilled Coffee After Dark | "Late-night cold coffee, 3 ways (dalgona, iced hazelnut latte, mocha)" | Recipe = product in use; searchable |
| ~3 Nov | Life3Baje | "Diwali gifting under ₹700 that isn't mithai" | Duo pack, Diwali window |
| ~10 Nov | Beyond3Baje | "What a 50 g jar of instant coffee actually costs to make in India" | Transparency content; trust |
| ~17 Nov | Khayal3Baje | Hindi: "Ghar par cafe jaisa cold coffee — 2 minute" | Hindi search; huge audience |
| ~24 Nov | Spilled Coffee Studio | "First 30 days of sales — real numbers" | Retention of viewers as customers |
Shorts: cut 3 vertical Shorts from each (recipe steps, jar reveal, unboxing a batch). BuzzcafAI already has the scriptwriter/research agents — a "Buzzcaf coffee" brand guide entry is the only thing to add (see `07-SOPS-AND-PROTOCOLS.md`, SOP-11).

### 1c. Measurement
Coupon code per channel + `/yt?c=` links with UTM → Admin → Attribution. Weekly: orders per channel, revenue per channel, code redemptions. Kill nothing before 8 weeks of data.

## 2. Amazon (where most strangers will buy)
- The listing is the marketing: 7 images (hero on white, flavour infographic, prepared cold coffee, jar-in-hand scale, 3-step how-to, readable label, brand-trust card), A+ content, title written for search ("Hazelnut Instant Coffee 50 g | Flavoured Coffee Powder for Cold Coffee & Latte | Buzzcaf").
- Brand Registry (trademark) → Brand Store → Sponsored Brands later.
- "Request a Review" on every order. Never incentivise reviews.
- Sponsored Products from ~week of 10 Nov if ≥15 reviews: exact-match "hazelnut instant coffee", "flavoured instant coffee", "caramel coffee powder", brand term. Daily budget ₹300. Judge on ACoS < 35%.
- Amazon Posts (free, brand-registered) — reuse Instagram creative.

## 3. Instagram @buzzcaf (revive, don't restart)
- 3 posts/week from one batch shoot per fortnight: recipe reel, process (jars arriving, QC, packing), customer repost.
- Bio link → `buzzcaf.com/yt?c=instagram` (code `INSTA10`).
- Reels are the Shorts re-uploaded. No separate production.
- Collab posts with the YouTube channel handles.

## 4. Google
- Google Business Profile for Buzzcaf Private Limited, Pune (20 minutes, free) — reviews, map, "products".
- Search Console for buzzcaf.com (also needed for YouTube end-screen links). Site ships sitemap, Product and Organization schema; blog/how-to pages target "cold coffee recipe with instant coffee", "dalgona coffee recipe", "hazelnut coffee".
- Merchant Center free listings (Phase 2).

## 5. WhatsApp
- WhatsApp Business app with catalogue (4 products) and quick replies. Number on site and label = consumer care number (PLACEHOLDER until you choose one; get a separate SIM).
- Broadcast list of customers who opt in: reorder nudge at day 21 (a 50 g jar lasts 2–4 weeks).

## 6. Seeding and PR (₹0–5,000)
- 20 jars to friends/creators who will honestly post; no review requests attached.
- Pune coffee/food micro-creators (5–20k followers): gift a duo pack, no fee, ask nothing.
- Product Hunt/Reddit r/IndianFood etc: only the "what it costs to make" transparency story; not ads.

## 7. Diwali window (20 Oct – 7 Nov)
- Duo pack as "Gift a Buzz" with a free printed card; gift message field is in checkout.
- Corporate: email 10 Pune startups/offices with a 25-box minimum offer (₹599 each duo, GST invoice). High AOV, low CAC.

## 8. Weekly rhythm (fits 8–10 hours)
| Day | 60–90 min | What |
|---|---|---|
| Tue eve | Ops + Amazon | Ops dashboard, orders, reviews, respond to questions, stock check, one supplier follow-up |
| Sat morn | Content | Batch shoot or edit; schedule 3 IG posts, 1 community post per channel; paste YouTube block into the week's uploads |
| Any | 15 min/day | WhatsApp replies, Amazon Q&A |

## 9. What we do NOT do before December
Quick commerce (Blinkit/Zepto/Instamart), Meta ads, influencer fees, offline retail, more than two flavours in stock.

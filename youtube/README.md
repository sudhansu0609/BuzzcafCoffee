# YouTube Integration Kit

Everything needed to put Buzzcaf into every upload on the five Buzzcaf Media channels, starting with the next video. Copy-paste; the links and codes already exist on the website (seeded coupons) so attribution works from day one.

| File | Use |
|---|---|
| `description-blocks.md` | The 3-line block for the top of every description, per channel, plus the full "about Buzzcaf" footer |
| `pinned-comments.md` | One-line pinned comment per channel |
| `end-screen-and-placement.md` | 20-second end-screen script, lower-third text, product-placement rules |
| `community-posts.md` | 8 community post templates (recipe, batch arriving, first orders, Diwali) |
| `links-and-utm.md` | Every link + coupon, one table, so nobody hand-types a URL |
| `video-briefs.md` | The six dedicated coffee videos (Oct–Nov) as briefs BuzzcafAI's ScriptWriter can take |
| `amazon-listing-copy.md` | Titles, bullets, A+ outline, image shot list for the Amazon listings |
| `corporate-gifting-email.md` | Diwali B2B email |
| `buzzcafai-brand-guide-snippet.md` | Text to add to BuzzcafAI so its agents know the product |

## Setup steps (one-time, 30 minutes, needs your logins)
1. Google Search Console → add `buzzcaf.com` → verify with the meta tag (env `GOOGLE_SITE_VERIFICATION` in the website) — required before YouTube lets you link to it from end screens.
2. YouTube Studio (each channel) → Settings → Channel → Advanced → Associated website → `buzzcaf.com`.
3. Each channel → Customisation → Basic info → Links → add "☕ Buzzcaf Coffee" → the channel's `/yt?c=` link. Turn on "show link on banner".
4. Each channel → Content → default upload settings → paste the description block so new uploads inherit it.
5. YouTube Shopping (later): Studio → Earn → Shopping → connect store (via Google Merchant Center feed) once the channel is eligible.

# End screen, lower-third and product placement

## End screen (last 20 seconds, every video)
Visual: jar (the launch flavour) centre-left on the desk, a made cold coffee beside it; end-screen elements right side (subscribe, next video, **link → buzzcaf.com**).

Voice (8 seconds, natural, not an ad read):
> "If you want the coffee that's been on this desk all video — it's ours, Buzzcaf. Link's below, the code gets you ten percent. Okay, see you in the next one."

Lower-third (on screen for the full 20 s):
```
BUZZCAF · buzzcaf.com · code BEYOND10
```
(swap the code per channel — see links-and-utm.md)

Make one 20-second end-screen clip per channel once and reuse it in every edit (BuzzEdit has the timeline; save as a preset).

## Mid-video mention (only when it fits, max once)
A one-liner when you actually drink it on camera: "This is the hazelnut one, by the way." That's it. Viewers hate a pitch; they remember a habit.

## Product placement rules
1. Jar visible in every talking-head shot, label facing camera, within the centre 60% of frame. Not hidden behind the mic.
2. A real cup being drunk, not a prop. Cold coffee in a clear glass reads best on camera.
3. Never two different brands of coffee in shot.
4. Thumbnail: the jar may appear in thumbnails of coffee-related videos only. Don't force it.
5. Shorts: last frame = jar + code, 1.5 s.

## Google Search Console + associated website (prerequisite for end-screen links)
1. search.google.com/search-console → Add property `buzzcaf.com` → HTML tag method → copy the content value into the website env `GOOGLE_SITE_VERIFICATION` → redeploy → Verify.
2. YouTube Studio → Settings → Channel → Advanced settings → Associated website → add and verify (uses the same Search Console).
3. Now the end-screen "Link" element and cards can point to buzzcaf.com.

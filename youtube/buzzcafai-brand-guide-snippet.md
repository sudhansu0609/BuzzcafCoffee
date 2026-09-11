# Add to BuzzcafAI (so its agents know the product)

BuzzcafAI keeps per-channel brand guides and a Studio Assistant persona. Add the block below to each channel's brand guide (the file BuzzcafAI's `knowledge/` uses for the channel guide — see its `AGENTS.md`), or paste it as a saved topic / memory. This lets ScriptWriter, ResearchAgent and the Analyze blueprint insert the Buzzcaf block and CTA automatically.

```
## Sponsor / owned product: Buzzcaf coffee
- Buzzcaf is OUR OWN brand (Buzzcaf Private Limited, Pune). Not a paid sponsor; disclose as "our own coffee".
- Product: flavoured instant coffee, 50 g glass jars. Flavours: Hazelnut, Caramel, Belgian Chocolate, Original. Launch flavours: [Hazelnut + ___].
- Price: ₹349 single, ₹649 duo, ₹999 four-box. Ships pan-India from buzzcaf.com; also on Amazon.in.
- Channel code: <BEYOND10 | AFTERDARK10 | LIFE10 | KHAYAL10 | STUDIO10>. Link: https://buzzcaf.com/yt?c=<beyond3baje|afterdark|life3baje|khayal3baje|studio>
- In every script: (1) the jar is on the desk — reference it naturally at most once mid-video; (2) the end-screen line: "If you want the coffee that's been on this desk all video — it's ours, Buzzcaf. Link below, the code gets you ten percent."; (3) description block and pinned comment from the kit.
- Tone: honest, small, ours. Never "best coffee in India". Never a hard sell. Recipes and behind-the-scenes over claims.
- Compliance: FSSAI Lic. 11522079000056 in the description footer. No health claims (no "boosts metabolism", "sugar-free" unless true).
```

Suggested SOP (also in Ops as SOP-11): when a video project is created in BuzzcafAI, the ScriptWriter step reads this block and the Publishing step's checklist includes "Buzzcaf block pasted + pinned comment + end screen preset".

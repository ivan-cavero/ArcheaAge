# Legal & project context

> **Not legal advice.** This document is a researched summary of publicly
> available information (August 2026) intended to explain, honestly, why this
> project exists, what its legal exposure is, and what funding models are
> realistic. For operating a public server commercially, consult a lawyer in
> your jurisdiction.

---

## 1. Why this project exists

- **ArcheAge's official western service is gone.** XLGAMES and publisher
  Kakao Games announced the shutdown in April 2024 and closed the servers on
  **June 27, 2024** after years of declining population.
- There is **no official way to play the original ArcheAge anymore**.
  XLGAMES' active product is *ArcheAge War* (a different game, Korea-centric).
- The community moved to player-run servers: **ArcheRage** (running openly
  since ~2017, 150k+ registered accounts) and **AA Classic** (3.0-based,
  actively patched as of 2026), among others. Two years after the official
  sunset, **no takedown action against any ArcheAge private server is
  publicly known**.
- ArcheaAge is therefore a **game-preservation effort**: an open-source
  platform (launcher, metaserver, plugin API, content pipeline) so the game
  remains playable and improvable by its community.

## 2. The actual legal landscape

### 2.1 What is (and isn't) risky

| Activity | Exposure |
| --- | --- |
| **Playing** on a private server | Effectively none. Contractual (EULA) issues only ever applied against live official services. |
| **Writing/distributing emulator code** (this repo) | Low–medium. Copyright law touches code that copies or derives from the original server — which is why AAEmu-style emulators are clean-room reimplementations from network behavior, published openly under LGPL. We distribute **only original code and documentation**, never game assets. |
| **Operating a public server** | Medium. Technically infringing (no "abandonware exception" exists; the DMCA §1201 server-shutdown exemption explicitly does **not** cover MMOs, because their content lives on the external server). In practice, enforcement against servers of **dead** games is rare — rightsholders rarely act when they no longer sell the product themselves. |
| **Monetizing a server** | Highest. Commercial exploitation of someone else's IP raises stakes (higher statutory damages, priority target). Historically, actions against private servers concentrate on ones that sell access, items or subscriptions. |

### 2.2 Grounds a rightsholder could theoretically claim

1. **Copyright infringement** — server emulation and any distribution of
   client files. Mitigation: clean-room protocol work, no asset
   redistribution, players bring their own client from their own sources.
2. **Trademark** — "ArcheAge", logos and art are trademarks of XLGAMES.
   Using the exact brand commercially increases risk. Note this project's
   name is deliberately altered ("Archea**A**ge"); server operators should
   brand their communities distinctly.
3. **Tortious interference** — inducing breach of live-service contracts.
   **Not applicable**: there is no live western service to interfere with
   since June 2024.

### 2.3 Precedents that matter

- *Sega v. Accolade* / *Sony v. Connectix* (US): reverse engineering for
  interoperability can be fair use — the basis on which emulator projects
  operate. Adverse precedent also exists (*Blizzard v. BnetD*), typically
  tied to EULA violations against **live** services.
- Tolerated preservation projects for dead MMOs have run openly for years
  (e.g., *Warhammer Online: Return of Reckoning*, *SWGEmu*, and the ArcheAge
  servers above).
- The landmark takedowns (Nostalrius, etc.) targeted servers of **live**
  games — a different situation from ours.

## 3. Funding & monetization (honest analysis)

Servers cost real money (hardware, bandwidth, DDoS protection, dev time).
Some funding model is required; they are not equal in risk:

| Model | Risk | Notes |
| --- | --- | --- |
| **Cost-covering donations** (transparent books, goals, no perks or cosmetic-only thanks) | Lowest | The community norm for preservation servers. Recommended starting point. |
| Cosmetic-only support tiers | Low-medium | Common compromise; still commercial use of IP — keep it clearly separated from gameplay power. |
| Subscriptions / item shops / paid advantages | High | Turns the operation into a commercial target and historically draws both rightsholder action and community backlash (see AA Classic's 2023 pre-order controversy). Avoid pay-to-win outright. |

Practical mitigations regardless of model:

- Operate funding through a proper legal entity; publish transparent books.
- Never sell exclusivity or power; refunds policy for anything paid.
- Distinct branding (avoid XLGAMES trademarks in commercial contexts).
- Have a wind-down/refund plan; treat the operation as revocable at any time.
- Jurisdiction matters; get local counsel before charging money.

## 4. This repository's own stance

- We distribute **original code only** (LGPL-3.0): launcher, metaserver,
  tools, docs. No client, no `game_pak`, no artwork, no music — clients come
  from each player's own sources (see `.client_files/README.md`).
- Protocol knowledge comes from **clean-room analysis and the already-public
  AAEmu project**, not from leaked source.
- Default funding posture for infrastructure we run: **transparent,
  cost-covering donations**. Any future monetization must follow §3's
  mitigations and will be documented publicly before it exists.
- If XLGAMES or a rightsholder objects to any part of this project, the
  affected parts will be taken down promptly upon notice.

---

*Sources consulted (Aug 2026): MMORPG.GG and Massively Overpowered coverage
of the June 27, 2024 sunset; mein-mmo.de and MOP reporting on private-server
activity and the AA Classic monetization controversy; ArcheRage/AA Classic
official sites; Law Stack Exchange and MakeTechEasier analyses of private-
server legality; 17 U.S.C. §1201 rulemaking text.*

# Context Pack Refresh Receipt

Phase: 1
Status: complete
Mode: map/delta refresh first, per Q1.

## Commands Executed

Context pack refreshes were run from the Paperclip cockpit builder:

```bash
node /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/context-packs/build-context-packs.mjs --repo <slug> --profile map
node /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/context-packs/build-context-packs.mjs --repo <slug> --profile delta
```

Initial infrastructure refresh:

- `portfolio-os`
- `paperclip`
- `hermes-agent`
- `gstack`

Second pass after the live YT-Synth run proved venture packs were stale or not covered:

- `leadforge`
- `yt-synth`
- `agency-swarm`

Portfolio OS was refreshed again after preserving its artifact commits.

## Current Manifest Summary

Source: `/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/context-packs/latest.json`

| Repo | Cwd | Head | Generated |
| --- | --- | --- | --- |
| `leadforge` | `/Users/mnm/Documents/Github/LeadForge` | `d4c579a` | `2026-07-06T01:58:47.709Z` |
| `portfolio-os` | `/Users/mnm/Documents/Github/portfolio-os` | `2b7080a741` | `2026-07-06T01:59:12.740Z` |
| `yt-synth` | `/Users/mnm/Documents/Github/YT-Synth` | `89b8c99` | `2026-07-06T01:58:49.960Z` |
| `agency-swarm` | `/Users/mnm/Documents/Github/agency-swarm` | `33bc44e8` | `2026-07-06T01:58:52.256Z` |
| `paperclip` | `/Users/mnm/Documents/Github/paperclip` | `092474504` | `2026-07-06T01:52:43.042Z` |
| `hermes-agent` | `/Users/mnm/Documents/Github/hermes-agent` | `f289cf97d` | `2026-07-06T01:52:45.945Z` |
| `gstack` | `/Users/mnm/Documents/Github/gstack` | `50c67adc` | `2026-07-06T01:52:54.081Z` |

## Gaps Found

- The builder currently has configured pack slugs for seven repos only: `leadforge`, `portfolio-os`, `yt-synth`, `agency-swarm`, `paperclip`, `hermes-agent`, and `gstack`.
- `hermes-paperclip-adapter`, Graphify outputs, ScrapeGraphAI, and GBrain are part of the operating system, but they do not have first-class context-pack slugs in this manifest.
- The live YT-Synth CMO run consumed a stale context manifest before the venture refresh pass, proving that refreshing only infrastructure repos is not enough.

## Resulting Fix

Paperclip context-economy live canary targets were expanded to include the active venture slugs:

- `leadforge`
- `yt-synth`
- `agency-swarm`

This prevents the canary layer from falsely passing while live venture Hermes runs can still receive stale pack envelopes.

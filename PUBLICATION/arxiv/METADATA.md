# arXiv Submission Metadata — CAIRN Protocol Whitepaper v2.0

## Title

CAIRN: A Protocol for Agent Failure Detection, Classification, and Recovery in the On-Chain Agent Economy

## Authors

Maroua Boudoukha (corresponding author)
— Independent researcher
— Contact: github.com/MarouaBoud

## Abstract (for arXiv submission — plain-text, no markdown)

AI agent task completion rates remain at approximately 50% across popular frameworks, yet no standardized protocol exists for failure detection, classification, and recovery in the on-chain agent economy. We present CAIRN, the first protocol to classify agent failures by recoverability rather than symptom, enabling deterministic routing to checkpoint-based recovery or dispute resolution.

CAIRN defines a 6-state machine with three-tier recovery routing, enforced by smart contracts: when an agent fails mid-task, the protocol detects the failure via missed heartbeats or resource exhaustion, classifies it into one of three recoverability classes (LIVENESS, RESOURCE, LOGIC), computes a multiplicative recovery score r = F^0.80 × B^0.35 × D^0.15, and routes the task to either a qualified fallback agent who resumes from the last IPFS-committed checkpoint, or to dispute resolution. The formula is empirically validated via Monte Carlo simulation across 100,000 task-failure events and 16 experiments, achieving 23.46% misrouting — within 0.93pp of the Bayes-optimal theoretical minimum (22.53%) — and reducing wasted-recovery false positives by 65% versus a linear baseline. Escrow is settled proportionally to verified work. We prove escrow safety, termination, and state determinism, and show that honest checkpointing is the dominant strategy under realistic economic parameters.

Our key insight is that economic enforcement — escrow-conditioned record writing — bootstraps a collective intelligence layer without requiring altruistic participation. Every failure becomes a queryable record. Every recovery teaches the next agent.

CAIRN integrates three Ethereum standards: ERC-8004 for agent identity and reputation, ERC-8183 for job escrow lifecycle, and ERC-7710 for scoped delegation. It is deployed on Base and composable with existing agent frameworks (LangGraph, Olas, CrewAI, AutoGen) and emerging coordination protocols (Google A2A, Anthropic MCP).

## arXiv Categories

**Primary:** `cs.DC` (Distributed, Parallel, and Cluster Computing)

**Cross-list (recommended — pick 1–2):**
- `cs.CR` (Cryptography and Security) — blockchain, smart-contract, incentive-design content
- `cs.MA` (Multiagent Systems) — agent coordination, failure recovery
- `cs.SE` (Software Engineering) — protocol specification, formal verification of state machine

## Comments Field (arXiv form)

```
1083 lines, 16 figures (included). Source: github.com/MarouaBoud/cairn-protocol.
Reproducible simulation: python3 -m simulation.run_eq4 (seed=42).
v1 testnet deployed on Base Sepolia; v2 specification in this paper.
```

## Keywords

AI agents, blockchain, failure recovery, smart contracts, Monte Carlo validation, mechanism design, ERC-8004, ERC-8183, checkpoint protocols, distributed systems

## License Declaration

The paper header (lines 7–14 of `cairn-whitepaper.md`) currently states:
> Copyright 2026 Maroua BOUDOUKHA. All rights reserved.
> Redistribution or commercial use requires written permission.

**arXiv considerations:**
- arXiv requires a non-exclusive, irrevocable license to distribute. Default options are `arXiv.org perpetual, non-exclusive` (most restrictive that arXiv accepts) or a Creative Commons variant (CC BY, CC BY-NC, CC BY-SA, CC0).
- "All rights reserved" is **compatible** with arXiv's default license (arXiv gets a distribution license; the author retains copyright).
- **Recommendation:** Keep "All rights reserved" for copyright but allow arXiv's default perpetual non-exclusive distribution license. This is the path most protocol/industry papers take.

## Files to Upload

1. `cairn-whitepaper.pdf` — generated from `cairn-whitepaper.md` via pandoc (see README.md)
2. OR `cairn-whitepaper.tex` — LaTeX source generated from markdown (preferred by arXiv)
3. `figures/fig1_weight_heatmap.png` through `fig16_triple_confusion.png` — 16 simulation figures

## Pre-submission Checklist

- [ ] Generate PDF or LaTeX source (see README.md)
- [ ] Verify PDF renders correctly (tables, subscripts, Greek letters, code blocks)
- [ ] Confirm all 16 figures render at adequate resolution
- [ ] Check that arXiv's PDF size limit (50 MB) is not exceeded
- [ ] Draft a plain-text abstract ≤1920 characters (arXiv limit) — the abstract above is ~1650 chars ✓
- [ ] Confirm author list, affiliations, and email match intended byline
- [ ] Select license (CC BY, CC BY-NC, CC0, or arXiv perpetual non-exclusive)
- [ ] Confirm arXiv account is verified and endorsed in `cs.DC` (new contributors sometimes need endorsement from an existing arXiv author)
- [ ] Draft comments field (see above)
- [ ] Review final rendered PDF one more time end-to-end

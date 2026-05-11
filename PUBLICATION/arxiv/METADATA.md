# arXiv Submission Metadata — CAIRN Protocol Whitepaper v2.0

## Title

CAIRN: A Protocol for Agent Failure Detection, Classification, and Recovery in the On-Chain Agent Economy

## Authors

Maroua Boudoukha (corresponding author)
— Independent researcher
— Contact: github.com/MarouaBoud

## Abstract (for arXiv submission — plain-text, no markdown)

AI agent task completion rates remain at approximately 50% across popular frameworks, yet no standardized protocol exists for failure detection, classification, and recovery in the on-chain agent economy. We present CAIRN, the first on-chain agent protocol to classify failures by recoverability rather than symptom, adapting the classical crash-vs-Byzantine distinction from distributed systems to enable deterministic routing to checkpoint-based recovery or dispute resolution.

CAIRN defines a 6-state machine with three-tier recovery routing enforced by smart contracts. On failure, the protocol classifies the failure into LIVENESS, RESOURCE, or LOGIC, computes a multiplicative recovery score r = F^0.80 × B^0.35 × D^0.15, and routes the task to a qualified fallback agent that resumes from the last IPFS checkpoint, or to dispute. The formula is calibrated against a ground-truth model derived from published failure-mode distributions: across 100,000 synthetic task-failure events and 16 experiments, it achieves 23.46% misrouting — within 0.93pp of the Bayes-optimal minimum (22.53%) for the same model — and reduces wasted-recovery false positives by 65% versus a linear baseline. We are explicit that this is near-optimality against the calibrated model, not production data; a staged roadmap replaces synthetic ground truth with observed outcomes as testnet data accumulates. Escrow settles proportionally to verified work. We prove escrow safety, termination, and state determinism.

Economic enforcement — escrow-conditioned record writing — bootstraps a collective intelligence layer without requiring altruistic participation. CAIRN integrates ERC-8004, ERC-8183, and ERC-7710; deployed on Base, composable with LangGraph, Olas, CrewAI, AutoGen, Google A2A, and Anthropic MCP. Source and reproducible simulation (seed=42): github.com/MarouaBoud/cairn-protocol.

## arXiv Categories

**Primary:** `cs.MA` (Multiagent Systems) — agent coordination, failure recovery, fallback assignment. The external reviewer flagged this as the most natural primary category for an agent-economy paper.

**Cross-list (recommended):**
- `cs.DC` (Distributed, Parallel, and Cluster Computing) — for the Chandy-Lamport lineage, the state-machine formalism, and the distributed-fault classification (crash vs. Byzantine adaptation)
- `cs.CR` (Cryptography and Security) — blockchain, smart-contract, incentive-design content, mechanism-design proofs

**Optional additional cross-list:**
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

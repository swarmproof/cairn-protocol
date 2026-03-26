# CAIRN Protocol — Final Submission Guide

> **Participant:** Lagertha
> **Participant ID:** `3c149a8709e04f8b8764281ea4c789c0`
> **Team ID:** `9374ee29ce794e4dbc6133f1378b4c0c`
> **Registration Tx:** [basescan.org/tx/0xb4f60b...](https://basescan.org/tx/0xb4f60b114709231de015394d566783d5cf6af9331668fbde79a08fabcfe0dfca)

---

## Step 1: Self-Custody Transfer

```bash
# A. Initiate transfer
curl -X POST https://synthesis.md/api/participants/me/transfer/init \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"targetOwnerAddress": "YOUR_WALLET_ADDRESS"}'

# Save the transferToken from response (valid 15 minutes)

# B. Confirm transfer
curl -X POST https://synthesis.md/api/participants/me/transfer/confirm \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"transferToken": "TOKEN_FROM_STEP_A", "targetOwnerAddress": "YOUR_WALLET_ADDRESS"}'
```

---

## Step 2: Get Track UUIDs

```bash
curl -X GET "https://synthesis.md/api/catalog?page=1&limit=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Find these tracks and save their UUIDs:
- **Protocol Labs: Agents With Receipts**
- **Let the Agent Cook**

---

## Step 3: Create Project

```bash
curl -X POST https://synthesis.md/api/projects \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @.synthesis/SUBMISSION_PAYLOAD.json
```

**Or copy this payload directly:**

```json
{
  "teamUUID": "9374ee29ce794e4dbc6133f1378b4c0c",
  "name": "CAIRN Protocol",
  "description": "Agent failure and recovery protocol that turns every agent failure into a lesson every other agent inherits — enforced by escrow, validated by attestation, owned by no one. CAIRN standardizes how agents checkpoint progress, emit heartbeats, and recover from failures via fallback assignment with proportional escrow settlement.",
  "problemStatement": "Agent workflows fail 80% of the time. At 85% success per action, a 10-step workflow completes only ~20% of the time. When failures happen today: work is lost (restart from zero), escrow locks (funds stuck for hours/days), no one learns (same failure repeats), and human intervention is required (2am pages). The ecosystem bleeds ~$5,300/month per operator to unrecovered failures. CAIRN solves this with automatic recovery, checkpoint preservation, and collective intelligence that compounds across the entire agent ecosystem.",
  "repoURL": "https://github.com/MarouaBoud/cairn-protocol",
  "deployedURL": "https://cairn-protocol-iona-78423aa1.vercel.app",
  "trackUUIDs": ["PROTOCOL_LABS_UUID", "LET_AGENT_COOK_UUID"],
  "conversationLog": "12 build sessions documented in .synthesis/CONVERSATION_LOG.md. Phases: Contract-Dev (Sessions 1-4, 315 tests, 98.95% coverage), SDK-Dev (Sessions 5-7, Python CairnClient/CairnAgent), Frontend-Dev (Sessions 8-10, Next.js 14 dashboard), Integration (Sessions 11-12, subgraph + polish). Key decisions: UUPS proxy pattern, CEI + ReentrancyGuard, Merkle checkpoint batching (89-99% gas savings), dual-write to IPFS. Blockers resolved: gas optimization via batching, real-time events via wagmi watches. Full chronological log: .synthesis/agent_log.json (70+ entries).",
  "submissionMetadata": {
    "agentFramework": "anthropic-agents-sdk",
    "agentHarness": "claude-code",
    "model": "claude-opus-4-5",
    "skills": ["contract-dev", "sdk-dev", "frontend-dev", "code-reviewer", "security-engineer"],
    "tools": ["Foundry", "Vercel", "The Graph", "wagmi", "Next.js", "Python", "IPFS/Pinata", "Base Sepolia", "OpenZeppelin"],
    "helpfulResources": [
      "https://eips.ethereum.org/EIPS/eip-8183",
      "https://eips.ethereum.org/EIPS/eip-8004",
      "https://eips.ethereum.org/EIPS/eip-7710",
      "https://docs.base.org",
      "https://book.getfoundry.sh",
      "https://thegraph.com/docs"
    ],
    "helpfulSkills": [
      {"name": "contract-dev", "reason": "Implemented 6-state machine, UUPS proxies, and 315 tests with 98.95% coverage"},
      {"name": "security-engineer", "reason": "CEI pattern, ReentrancyGuard, custom errors, input validation on all public functions"}
    ],
    "intention": "continuing",
    "intentionNotes": "Active development planned - mainnet launch Q2 2026"
  }
}
```

Save the `projectUUID` from the response.

---

## Step 4: Post on Moltbook

Create a post with:
- What CAIRN does
- Tracks: Protocol Labs + Let the Agent Cook
- Links: https://github.com/MarouaBoud/cairn-protocol + https://cairn-protocol-iona-78423aa1.vercel.app

Then update project with Moltbook URL:

```bash
curl -X POST https://synthesis.md/api/projects/PROJECT_UUID \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"submissionMetadata": {"moltbookPostURL": "YOUR_MOLTBOOK_POST_URL"}}'
```

---

## Step 5: Publish

```bash
curl -X POST https://synthesis.md/api/projects/PROJECT_UUID/publish \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Step 6: Tweet

```
🪨 Just shipped CAIRN Protocol for @synthesis_md!

Agent failure → recoverable progress
• Checkpoints preserved on-chain
• Automatic fallback routing
• Fair escrow settlement

Live demo: cairn-protocol-iona-78423aa1.vercel.app
Repo: github.com/MarouaBoud/cairn-protocol

#Synthesis2026 #AgentsWithReceipts
```

---

## Quick Reference

| Field | Value |
|-------|-------|
| **Team UUID** | `9374ee29ce794e4dbc6133f1378b4c0c` |
| **Participant ID** | `3c149a8709e04f8b8764281ea4c789c0` |
| **Project Name** | CAIRN Protocol |
| **Repo** | https://github.com/MarouaBoud/cairn-protocol |
| **Demo** | https://cairn-protocol-iona-78423aa1.vercel.app |
| **CairnCore** | `0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640` |
| **Chain** | Base Sepolia (84532) |
| **Agent Framework** | anthropic-agents-sdk |
| **Agent Harness** | claude-code |
| **Model** | claude-opus-4-5 |

---

## Onchain Artifacts

| Contract | Address |
|----------|---------|
| CairnCore | [`0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640`](https://sepolia.basescan.org/address/0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640) |
| CairnTaskMVP | [`0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417) |
| CairnGovernance | [`0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f`](https://sepolia.basescan.org/address/0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f) |
| RecoveryRouter | [`0xE52703946cb44c12A6A38A41f638BA2D7197a84d`](https://sepolia.basescan.org/address/0xE52703946cb44c12A6A38A41f638BA2D7197a84d) |
| FallbackPool | [`0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0`](https://sepolia.basescan.org/address/0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0) |
| ArbiterRegistry | [`0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68`](https://sepolia.basescan.org/address/0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68) |

---

## Files Ready

- [x] `.synthesis/agent.json`
- [x] `.synthesis/agent_log.json`
- [x] `.synthesis/CONVERSATION_LOG.md`
- [x] `.synthesis/SUBMISSION_PAYLOAD.json`
- [x] `README.md` (with Hackathon Submission section)

---

**Deadline:** March 22, 2026 at 11:59 PM PST

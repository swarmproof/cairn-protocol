# CAIRN Sponsor Alignment

> Strategic alignment with Synthesis Hackathon 2026 sponsors

---

## Indispensable Sponsors

These sponsors are **load-bearing** — CAIRN cannot function without them.

| Sponsor | Role in CAIRN | Integration Point | Why Indispensable |
|---------|---------------|-------------------|-------------------|
| **EF dAI / ERC-8004** | Agent identity + reputation read/write | A3 (identity), A12 (positive rep), A13 (negative rep) | No identity = can't identify agents. No reputation = can't filter fallbacks. |
| **Virtuals / EF dAI ERC-8183** | Job lifecycle + escrow standard | All states — CAIRN is an ERC-8183 Hook | No escrow = no economic forcing function. |
| **MetaMask / ERC-7710** | Delegation caveat for fallback authorization | A3 (pre-auth), A10 (transfer to fallback) | No delegation = require human signature at recovery time. |
| **Olas / Valory** | Fallback agent pool (Mech Marketplace) | A9 (fallback selection) | No fallback pool = no recovery. |
| **Bonfires** | Intelligence layer query + visualization | A2 (pre-task query), A9 (fallback routing) | No intelligence = no pattern learning. |

---

## Additive Sponsors

These sponsors are **valuable but not load-bearing** — CAIRN could work without them (with reduced functionality).

| Sponsor | How CAIRN Uses Them | Why Valuable |
|---------|---------------------|--------------|
| **Base** | Deployment chain | Low gas, fast blocks, ERC-8004/8183 already deployed, AgentKit native |
| **Filecoin / Protocol Labs** | IPFS for record storage | Decentralized, content-addressed, immutable records |
| **The Graph** | Subgraph indexing `TaskFailed`/`TaskResolved` events | Fast queries, production-grade indexing |

---

## Integration Map

```
CairnTask.sol
│
├── RUNNING
│   ├── ERC-8183 (Virtuals/EF dAI) — job + escrow locked on startTask()
│   └── ERC-7710 (MetaMask) — delegation caveat pre-authorized by operator
│
├── FAILED
│   └── Bonfires — failure record written via BonfiresAdapter on TaskFailed event
│
├── RECOVERING
│   ├── Olas Mech Marketplace (Valory) — fallback agent pool queried
│   ├── Bonfires — success rate signal for fallback selection
│   └── ERC-7710 (MetaMask) — pre-authorized caveat sub-delegated to fallback
│
├── RESOLVED
│   ├── ERC-8183 (Virtuals/EF dAI) — complete() called, escrow released
│   ├── ERC-8004 (EF dAI) — positive reputation signal written
│   └── Bonfires — resolution record written via BonfiresAdapter
│
└── DISPUTED
    ├── ERC-8183 (Virtuals/EF dAI) — escrow held, claimRefund() on timeout
    ├── ERC-8004 (EF dAI) — negative reputation signal written
    └── Bonfires — dispute record written, exposed as arbitration evidence
```

---

## Prize Alignment

### EF dAI Track

**Why CAIRN wins:**
- Deep integration with both ERC-8004 and ERC-8183
- Novel use case: reputation as fallback admission gate
- Novel use case: ERC-8183 Hook for failure/recovery lifecycle
- Demonstrates composability of the dAI stack

### Olas / Valory Track

**Why CAIRN wins:**
- Uses Mech Marketplace as the live fallback pool
- Creates demand for Olas agents (every CAIRN task is a potential fallback assignment)
- Demonstrates value of the Olas registry beyond direct operator selection

### MetaMask Track

**Why CAIRN wins:**
- Correct use of ERC-7710 caveat-enforced delegation
- Pre-authorization at init, sub-delegation at recovery
- No human required at recovery time — the trust model is set up correctly

### Bonfires Track

**Why CAIRN wins:**
- Novel use case: knowledge graph written entirely by agent activity (no humans)
- Demonstrates compounding value of Bonfires as infrastructure
- Query API is load-bearing in two protocol actions (A2, A9)

---

## Why This Alignment Wins

The judges are agents running on Bonfires knowledge graphs evaluating "what crypto wants." CAIRN directly answers the question every agent judge has implicitly experienced: *what happens when I fail?*

The answer is:
- Not silence
- Not lost funds
- Not a restart from zero
- Not a human waking up at 3am

The answer is: **a deterministic protocol fires. You are recovered. Your experience becomes intelligence. The ecosystem learns.**

That is infrastructure every agent judge recognizes as necessary for their own existence.

---

## Talking Points by Sponsor

### When talking to EF dAI judges:

> "CAIRN is the first protocol to use ERC-8004 reputation as an admission gate for economic activity. If your reputation is below threshold, you can't receive fallback assignments. This makes the reputation score load-bearing — not just decorative."

### When talking to Olas judges:

> "Every CAIRN task creates potential demand for Olas agents. The fallback pool is a new market for your Mechs — they get paid for completing tasks that other agents failed."

### When talking to MetaMask judges:

> "We use ERC-7710 correctly — pre-authorization at task init with scoped caveats, sub-delegation at recovery time. No human signature required when failure happens. This is the trust model the delegation framework was designed for."

### When talking to Bonfires judges:

> "The knowledge graph in Bonfires is built entirely by agent activity. No human writes to it. This inverts Bonfires' typical use case and demonstrates that the infrastructure works for autonomous knowledge accumulation."

---

*Synthesis Hackathon 2026*

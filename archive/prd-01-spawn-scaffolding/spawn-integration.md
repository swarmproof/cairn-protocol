# Spawn Prompt: Integration

> CAIRN MVP Integration Testing & Demo Polish

## CONTEXT

You are responsible for end-to-end testing and demo preparation for CAIRN protocol MVP.

**PRD Location**: `/PRDs/PRD-01-MVP-HACKATHON.md`
**Target Repo**: `cairn-protocol`
**Your Tasks**: 23-26 (Integration & Polish phase)
**Depends On**: Frontend deployed (Task 22)

**Read First**:
- PRD Section 2.7 (User Workflows)
- PRD Section 8.4 (E2E Test Scenarios)
- PRD Appendix A (Demo Script — THE MOST IMPORTANT PART)

## SCOPE

**No new directories** — you're testing and polishing existing work.

**Artifacts to Create**:
```
cairn-protocol/
├── DEMO.md              # Demo script with timing
├── E2E_RESULTS.md       # Test results log
└── VIDEO_BACKUP/        # (optional) Pre-recorded demo
    └── cairn-demo.mp4
```

## YOUR TASKS

### Task 23: E2E Happy Path Test
**Test the complete flow without failure**

**Steps**:
1. Connect wallet to Base Sepolia
2. Submit task via frontend (5 subtasks, 0.01 ETH escrow)
3. Run primary agent (from SDK)
4. Watch checkpoints appear in UI (5 total)
5. Complete task
6. Settle
7. Verify: Primary receives 99.5%, protocol 0.5%

**Acceptance**:
- [ ] All steps complete without errors
- [ ] UI shows correct state at each step
- [ ] Settlement amounts match expected
- [ ] Transaction confirmed on Basescan

### Task 24: E2E Recovery Path Test
**Test the failure → recovery flow**

**Steps**:
1. Connect wallet
2. Submit task (5 subtasks)
3. Run primary agent, checkpoint 3 times
4. Stop primary agent (simulate crash)
5. Click "Inject Failure" or wait for heartbeat timeout
6. Verify task moves to FAILED
7. Click "Trigger Recovery" (or auto-trigger)
8. Run fallback agent (reads checkpoint 3, completes 4-5)
9. Settle
10. Verify: Primary 60%, Fallback 40%

**Acceptance**:
- [ ] Failure detected within heartbeat interval
- [ ] Fallback receives checkpoint CIDs
- [ ] Fallback resumes from checkpoint 3 (not restart)
- [ ] Settlement split is exactly 60/40
- [ ] All events visible in UI

### Task 25: Demo Script Rehearsal
**Practice the demo until flawless**

**Script** (from PRD Appendix A):
1. **The Problem** (30 sec): "Agent workflows fail 80%..."
2. **Show Task Running** (30 sec): Checkpoints 1, 2, 3 appearing
3. **Inject Failure** (30 sec): Click button, show FAILED state
4. **Recovery** (60 sec): Fallback assigned, reads checkpoint, continues
5. **Settlement** (30 sec): "Both get paid for their work"
6. **Close** (30 sec): "CAIRN: Agents that fail forward"

**Acceptance**:
- [ ] Demo completes in under 4 minutes
- [ ] No fumbling or errors
- [ ] Talking points memorized
- [ ] Backup plan if something fails

### Task 26: Record Backup Video
**In case live demo fails**

**Requirements**:
- [ ] Screen recording of full demo
- [ ] Voiceover explaining each step
- [ ] 720p minimum quality
- [ ] Under 4 minutes
- [ ] Saved to `VIDEO_BACKUP/` or cloud link

## BOUNDARIES

**Do NOT**:
- Make code changes (report bugs, don't fix)
- Skip any test scenario
- Submit if critical bugs found

**Do**:
- Document every bug found
- Time each demo section
- Practice transitions between screens
- Prepare fallback talking points

## SUCCESS CRITERIA

1. **Happy Path**: Works 100% (3 consecutive runs)
2. **Recovery Path**: Works 100% (3 consecutive runs)
3. **Demo Time**: Under 4 minutes
4. **Video**: Recorded and accessible
5. **Confidence**: Team can run demo without notes

## TEST CHECKLIST

### Pre-Demo Checklist
- [ ] Wallet has Base Sepolia ETH (get from faucet)
- [ ] Contract address correct in frontend
- [ ] Pinata JWT valid
- [ ] RPC endpoint responsive
- [ ] Frontend deployed and accessible
- [ ] Agent scripts ready to run

### During Demo Checklist
- [ ] Browser devtools closed (cleaner UI)
- [ ] Wallet connected before demo starts
- [ ] Task pre-submitted OR submit is first action
- [ ] Timer running (stay under 4 min)

### Post-Demo Checklist
- [ ] Settlement visible on Basescan
- [ ] Task in RESOLVED state
- [ ] Both agents show correct balances

## BUG REPORTING FORMAT

If bugs found, create issues in this format:

```markdown
## [BLOCKER/MAJOR/MINOR] Bug Title

**Steps to Reproduce**:
1. ...
2. ...
3. ...

**Expected**: ...
**Actual**: ...

**Screenshot/Video**: [attach]

**Environment**:
- Browser: ...
- Wallet: ...
- Network: Base Sepolia
```

## HANDOFF

When complete, update `PRD-01-STATUS.md`:
- Mark tasks 23-26 as ✅
- Link to demo video
- Note any remaining issues
- Mark "Ready for Submission"

Create `DEMO.md` with:
- Final demo script with timing
- Links to frontend, contract, video
- Troubleshooting tips

Notify: "CAIRN MVP ready for submission. Demo video at [link]. Frontend at [link]."

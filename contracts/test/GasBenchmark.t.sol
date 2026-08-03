// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";

/// @title Full-system gas benchmark (PRD-04 Phase 5, G6)
/// @notice Measures per-call gas for the v2 hot paths, including
///         commitCheckpointBatch at batch sizes 1/10/50 (which are
///         count-independent by design — Merkle batching commits one root
///         per batch regardless of checkpoint count). Run with -vv to read
///         the console output; numbers backfill WHITEPAPER_V2 §6.5.
contract GasBenchmarkTest is Test {
    CairnCore core;
    RecoveryRouterV2 router;
    FallbackPool pool;
    ArbiterRegistry registry;
    CairnGovernance governance;

    address admin = makeAddr("admin");
    address feeRecipient = makeAddr("feeRecipient");
    address operator = makeAddr("operator");
    address primaryAgent = makeAddr("primaryAgent");
    address fallbackAgent = makeAddr("fallbackAgent");

    bytes32 specHash = keccak256("task spec");
    bytes32 taskType = keccak256("defi.swap");

    function setUp() public {
        governance = new CairnGovernance(admin);
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));
        router = new RecoveryRouterV2(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);

        vm.startPrank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));
        core.setThreeTierRouting(true);
        vm.stopPrank();

        vm.deal(operator, 100 ether);
        vm.deal(fallbackAgent, 10 ether);
        vm.deal(address(core), 10 ether);

        bytes32[] memory tt = new bytes32[](1);
        tt[0] = taskType;
        vm.prank(fallbackAgent);
        pool.register{value: 1 ether}(tt, 5);
    }

    function _submit() internal returns (bytes32 taskId) {
        vm.prank(operator);
        taskId = core.submitTask{value: 0.1 ether}(
            taskType, specHash, primaryAgent, 60, block.timestamp + 1 hours
        );
    }

    function _startedTask() internal returns (bytes32 taskId) {
        taskId = _submit();
        vm.prank(primaryAgent);
        core.startTask(taskId);
    }

    function _measureCheckpointBatch(uint256 count) internal returns (uint256 used) {
        bytes32 taskId = _startedTask();
        vm.prank(primaryAgent);
        uint256 g = gasleft();
        core.commitCheckpointBatch(taskId, count, keccak256("root"), keccak256("cid"), specHash);
        used = g - gasleft();
    }

    function test_GasReport() public {
        // submitTask (full success path incl. fallback auto-selection)
        vm.prank(operator);
        uint256 g = gasleft();
        bytes32 taskId = core.submitTask{value: 0.1 ether}(
            taskType, specHash, primaryAgent, 60, block.timestamp + 1 hours
        );
        console.log("submitTask                    :", g - gasleft());

        // startTask
        vm.prank(primaryAgent);
        g = gasleft();
        core.startTask(taskId);
        console.log("startTask                     :", g - gasleft());

        // heartbeat
        vm.warp(block.timestamp + 30);
        vm.prank(primaryAgent);
        g = gasleft();
        core.heartbeat(taskId);
        console.log("heartbeat                     :", g - gasleft());

        // commitCheckpointBatch at 1 / 10 / 50 (fresh started task each, first batch)
        console.log("commitCheckpointBatch(count=1):", _measureCheckpointBatch(1));
        console.log("commitCheckpointBatch(count=10):", _measureCheckpointBatch(10));
        console.log("commitCheckpointBatch(count=50):", _measureCheckpointBatch(50));

        // completeTask (settlement path)
        bytes32 t2 = _startedTask();
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(t2, 1, keccak256("r"), keccak256("c"), specHash);
        vm.prank(primaryAgent);
        g = gasleft();
        core.completeTask(t2);
        console.log("completeTask (settle)         :", g - gasleft());

        // recoveryScore: full multiplicative path (LIVENESS, both pow calls)
        g = gasleft();
        router.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 1e18, 1e18);
        console.log("computeRecoveryScore (LIVENESS):", g - gasleft());

        // recoveryScore: LOGIC short-circuit (F=0 → r=0, no pow calls)
        g = gasleft();
        router.computeRecoveryScore(ICairnTypes.FailureClass.LOGIC, 1e18, 1e18);
        console.log("computeRecoveryScore (LOGIC)  :", g - gasleft());

        // routingTier (pure view classifier)
        g = gasleft();
        router.routingTier(0.5e18);
        console.log("routingTier                   :", g - gasleft());
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";

/// @title Checkpoint count binding (H-5)
/// @notice The batch size equals the number of published CIDs, the root is computed
///         on-chain from them, and every counted checkpoint is provable against it.
contract CheckpointBindingTest is Test {
    CairnCore public core;
    RecoveryRouterV2 public router;
    FallbackPool public pool;
    ArbiterRegistry public registry;
    CairnGovernance public governance;

    address public admin = makeAddr("admin");
    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");

    bytes32 public specHash = keccak256("task spec");
    bytes32 public taskType = keccak256("defi.swap");

    function setUp() public {
        governance = new CairnGovernance(admin);
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));
        router = new RecoveryRouterV2(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);
        vm.prank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));
        vm.deal(operator, 100 ether);
    }

    // ─── helpers ─────────────────────────────────────────────────

    function _start() internal returns (bytes32 taskId) {
        vm.prank(operator);
        taskId = core.submitTask{ value: 1 ether }(
            taskType, specHash, primaryAgent, 60, block.timestamp + 1 days
        );
        vm.prank(primaryAgent);
        core.startTask(taskId);
    }

    function _cids(uint256 n, uint256 salt) internal pure returns (bytes32[] memory c) {
        c = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            c[i] = keccak256(abi.encode(salt, i));
        }
    }

    function _hashPair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return a < b ? keccak256(abi.encodePacked(a, b)) : keccak256(abi.encodePacked(b, a));
    }

    function _leaves(bytes32[] memory cids) internal pure returns (bytes32[] memory level) {
        level = new bytes32[](cids.length);
        for (uint256 i = 0; i < cids.length; i++) {
            level[i] = keccak256(abi.encodePacked(cids[i], i));
        }
    }

    function _next(bytes32[] memory level) internal pure returns (bytes32[] memory next) {
        next = new bytes32[]((level.length + 1) / 2);
        for (uint256 i = 0; i < next.length; i++) {
            next[i] = 2 * i + 1 < level.length
                ? _hashPair(level[2 * i], level[2 * i + 1])
                : level[2 * i];
        }
    }

    /// @dev Reference root: fresh array per level, promoted odd node.
    function _refRoot(bytes32[] memory cids) internal pure returns (bytes32) {
        bytes32[] memory level = _leaves(cids);
        while (level.length > 1) level = _next(level);
        return level[0];
    }

    /// @dev Proof for leaf `idx`: sibling at each level where one exists.
    function _proof(bytes32[] memory cids, uint256 idx) internal pure returns (bytes32[] memory) {
        bytes32[] memory tmp = new bytes32[](64);
        uint256 len;
        bytes32[] memory level = _leaves(cids);
        while (level.length > 1) {
            uint256 sib = idx ^ 1;
            if (sib < level.length) tmp[len++] = level[sib];
            level = _next(level);
            idx /= 2;
        }
        bytes32[] memory proof = new bytes32[](len);
        for (uint256 i = 0; i < len; i++) proof[i] = tmp[i];
        return proof;
    }

    // ═══════════════════════════════════════════════════════════════
    // count binding
    // ═══════════════════════════════════════════════════════════════

    function test_CountEqualsPublishedCids() public {
        bytes32 taskId = _start();
        bytes32[] memory cids = _cids(7, 1);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, cids, specHash);

        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(t.checkpointCount, 7);
        assertEq(t.primaryCheckpoints, 7);
        assertEq(t.latestCheckpointCID, cids[6]);
    }

    function test_EmptyBatch_Reverts() public {
        bytes32 taskId = _start();
        vm.prank(primaryAgent);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InvalidCheckpointCount.selector, 0, 1000));
        core.commitCheckpointBatch(taskId, new bytes32[](0), specHash);
    }

    function test_OverCapBatch_Reverts() public {
        bytes32 taskId = _start();
        vm.prank(primaryAgent);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InvalidCheckpointCount.selector, 1001, 1000));
        core.commitCheckpointBatch(taskId, _cids(1001, 2), specHash);
    }

    function test_MaxBatch_Succeeds() public {
        bytes32 taskId = _start();
        bytes32[] memory cids = _cids(1000, 3);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, cids, specHash);
        assertEq(core.getTask(taskId).checkpointCount, 1000);
        assertEq(core.getBatchRoots(taskId)[0], _refRoot(cids));
    }

    // ═══════════════════════════════════════════════════════════════
    // root computation and proofs
    // ═══════════════════════════════════════════════════════════════

    function test_SingleCid_RootIsLeaf() public {
        bytes32 taskId = _start();
        bytes32[] memory cids = _cids(1, 4);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, cids, specHash);
        assertEq(core.getBatchRoots(taskId)[0], keccak256(abi.encodePacked(cids[0], uint256(0))));
        assertTrue(core.verifyCheckpoint(taskId, cids[0], 0, 0, new bytes32[](0)));
    }

    function testFuzz_RootMatchesReference(uint8 n) public {
        uint256 size = bound(n, 1, 64);
        bytes32 taskId = _start();
        bytes32[] memory cids = _cids(size, uint256(n));
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, cids, specHash);
        assertEq(core.getBatchRoots(taskId)[0], _refRoot(cids));
    }

    /// Every counted checkpoint is individually provable, for odd and even sizes.
    function test_EveryLeafProvable() public {
        uint256[4] memory sizes = [uint256(2), 5, 8, 13];
        for (uint256 s = 0; s < sizes.length; s++) {
            bytes32 taskId = _start();
            bytes32[] memory cids = _cids(sizes[s], 100 + s);
            vm.prank(primaryAgent);
            core.commitCheckpointBatch(taskId, cids, specHash);
            for (uint256 i = 0; i < cids.length; i++) {
                assertTrue(core.verifyCheckpoint(taskId, cids[i], 0, i, _proof(cids, i)));
            }
            // A CID at the wrong index does not verify
            assertFalse(core.verifyCheckpoint(taskId, cids[0], 0, 1, _proof(cids, 1)));
        }
    }

    /// A CID that was not published is not provable against the stored root.
    function test_UnpublishedCid_NotProvable() public {
        bytes32 taskId = _start();
        bytes32[] memory cids = _cids(4, 9);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, cids, specHash);
        assertFalse(core.verifyCheckpoint(taskId, keccak256("not published"), 0, 2, _proof(cids, 2)));
    }

    function test_SeparateBatches_SeparateRoots() public {
        bytes32 taskId = _start();
        bytes32[] memory a = _cids(3, 11);
        bytes32[] memory b = _cids(4, 12);
        vm.startPrank(primaryAgent);
        core.commitCheckpointBatch(taskId, a, specHash);
        core.commitCheckpointBatch(taskId, b, specHash);
        vm.stopPrank();

        bytes32[] memory roots = core.getBatchRoots(taskId);
        assertEq(roots[0], _refRoot(a));
        assertEq(roots[1], _refRoot(b));
        assertEq(core.getTask(taskId).checkpointCount, 7);
        assertTrue(core.verifyCheckpoint(taskId, b[3], 1, 3, _proof(b, 3)));
    }
}

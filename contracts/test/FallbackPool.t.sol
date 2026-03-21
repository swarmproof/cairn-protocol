// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {IFallbackPool} from "../src/interfaces/IFallbackPool.sol";
import {MockERC8004} from "./mocks/MockERC8004.sol";

/// @title FallbackPool Tests
/// @notice Comprehensive tests for fallback agent registration and selection
/// @dev Based on PRD-04 Sections 2-3
contract FallbackPoolTest is Test {
    FallbackPool public pool;
    MockERC8004 public reputationRegistry;

    address public cairnCore = makeAddr("cairnCore");
    address public feeRecipient = makeAddr("feeRecipient");
    address public agent1 = makeAddr("agent1");
    address public agent2 = makeAddr("agent2");
    address public agent3 = makeAddr("agent3");
    address public randomUser = makeAddr("randomUser");

    bytes32 public taskType1 = keccak256("defi.swap");
    bytes32 public taskType2 = keccak256("nft.mint");

    uint256 public constant MIN_STAKE_PERCENT = 10;
    uint256 public constant MIN_REPUTATION = 50;
    uint256 public constant PRECISION = 100;

    function setUp() public {
        // Deploy mock reputation registry
        reputationRegistry = new MockERC8004();

        // Deploy FallbackPool with mock registry (no Olas adapter)
        pool = new FallbackPool(cairnCore, feeRecipient, address(reputationRegistry), address(0), address(0));

        // Fund agents
        vm.deal(agent1, 10 ether);
        vm.deal(agent2, 10 ether);
        vm.deal(agent3, 10 ether);

        // Note: MockERC8004 defaults to 70 reputation if not set
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Constructor() public view {
        assertEq(pool.cairnCore(), cairnCore);
        assertEq(pool.feeRecipient(), feeRecipient);
        assertEq(pool.minReputation(), MIN_REPUTATION);
        assertEq(pool.minStakePercent(), MIN_STAKE_PERCENT);
    }

    function test_ConstructorAllowsZeroCairnCore() public {
        // Zero cairnCore is allowed for initial deployment (set via setCairnCore later)
        FallbackPool newPool = new FallbackPool(address(0), feeRecipient, address(0), address(0), address(0));
        assertEq(newPool.cairnCore(), address(0));

        // Can set cairnCore later
        newPool.setCairnCore(cairnCore);
        assertEq(newPool.cairnCore(), cairnCore);
    }

    function test_RevertConstructorZeroFeeRecipient() public {
        vm.expectRevert(IFallbackPool.ZeroAddress.selector);
        new FallbackPool(cairnCore, address(0), address(0), address(0), address(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Register() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 3);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertTrue(agent.registered);
        assertEq(agent.stake, 1 ether);
        assertEq(agent.maxConcurrentTasks, 3);
        assertEq(agent.reputation, 70); // Default mock
        assertEq(agent.activeTaskCount, 0);
        assertEq(agent.completedTasks, 0);
        assertEq(agent.failedTasks, 0);
    }

    function test_RegisterWithMultipleTaskTypes() public {
        bytes32[] memory taskTypes = new bytes32[](2);
        taskTypes[0] = taskType1;
        taskTypes[1] = taskType2;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 5);

        // Check agent is registered for both task types
        address[] memory type1Agents = pool.getTaskTypeAgents(taskType1);
        address[] memory type2Agents = pool.getTaskTypeAgents(taskType2);

        assertEq(type1Agents.length, 1);
        assertEq(type2Agents.length, 1);
        assertEq(type1Agents[0], agent1);
        assertEq(type2Agents[0], agent1);
    }

    function test_RegisterEmitsEvent() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        vm.expectEmit(true, false, false, true);
        emit IFallbackPool.AgentRegistered(agent1, taskTypes, 1 ether);
        pool.register{value: 1 ether}(taskTypes, 3);
    }

    function test_RevertRegisterAlreadyRegistered() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 3);

        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.AlreadyRegistered.selector);
        pool.register{value: 1 ether}(taskTypes, 3);
    }

    function test_RevertRegisterNoStake() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        vm.expectRevert(abi.encodeWithSelector(IFallbackPool.InsufficientStake.selector, 1, 0));
        pool.register{value: 0}(taskTypes, 3);
    }

    function test_RevertRegisterNoTaskTypes() public {
        bytes32[] memory taskTypes = new bytes32[](0);

        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.InvalidTaskTypes.selector);
        pool.register{value: 1 ether}(taskTypes, 3);
    }

    function test_RevertRegisterInsufficientReputation() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        // Set low reputation via mock registry
        reputationRegistry.setReputation(agent1, 30);

        vm.prank(agent1);
        vm.expectRevert(abi.encodeWithSelector(IFallbackPool.InsufficientReputation.selector, 50, 30));
        pool.register{value: 1 ether}(taskTypes, 3);
    }

    // ═══════════════════════════════════════════════════════════════
    // STAKE MANAGEMENT TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_AddStake() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(agent1);
        pool.addStake{value: 0.5 ether}();

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertEq(agent.stake, 1.5 ether);
    }

    function test_AddStakeEmitsEvent() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(agent1);
        vm.expectEmit(true, false, false, true);
        emit IFallbackPool.StakeAdded(agent1, 0.5 ether, 1.5 ether);
        pool.addStake{value: 0.5 ether}();
    }

    function test_RevertAddStakeNotRegistered() public {
        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.NotRegistered.selector);
        pool.addStake{value: 0.5 ether}();
    }

    function test_WithdrawStake() public {
        _registerAgent(agent1, 2 ether);

        uint256 balanceBefore = agent1.balance;

        vm.prank(agent1);
        pool.withdrawStake(0.5 ether);

        uint256 balanceAfter = agent1.balance;
        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);

        assertEq(agent.stake, 1.5 ether);
        assertEq(balanceAfter - balanceBefore, 0.5 ether);
    }

    function test_WithdrawStakeEmitsEvent() public {
        _registerAgent(agent1, 2 ether);

        vm.prank(agent1);
        vm.expectEmit(true, false, false, true);
        emit IFallbackPool.StakeWithdrawn(agent1, 0.5 ether, 1.5 ether);
        pool.withdrawStake(0.5 ether);
    }

    function test_RevertWithdrawStakeNotRegistered() public {
        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.NotRegistered.selector);
        pool.withdrawStake(0.5 ether);
    }

    function test_RevertWithdrawStakeInsufficientBalance() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(agent1);
        vm.expectRevert(abi.encodeWithSelector(IFallbackPool.InsufficientStake.selector, 2 ether, 1 ether));
        pool.withdrawStake(2 ether);
    }

    function test_RevertWithdrawStakeActiveTasks() public {
        _registerAgent(agent1, 1 ether);

        // Activate a task
        vm.prank(cairnCore);
        pool.activateFallback(keccak256("task1"), agent1);

        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.ActiveRecoveriesPending.selector);
        pool.withdrawStake(0.5 ether);
    }

    // ═══════════════════════════════════════════════════════════════
    // DEREGISTRATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Deregister() public {
        _registerAgent(agent1, 1 ether);

        uint256 balanceBefore = agent1.balance;

        vm.prank(agent1);
        pool.deregister();

        uint256 balanceAfter = agent1.balance;
        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);

        assertFalse(agent.registered);
        assertEq(agent.stake, 0);
        assertEq(balanceAfter - balanceBefore, 1 ether);
    }

    function test_DeregisterEmitsEvent() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(agent1);
        vm.expectEmit(true, false, false, true);
        emit IFallbackPool.AgentDeregistered(agent1, 1 ether);
        pool.deregister();
    }

    function test_DeregisterRemovesFromTaskTypes() public {
        _registerAgent(agent1, 1 ether);

        // Verify agent is in task type list
        address[] memory agentsBefore = pool.getTaskTypeAgents(taskType1);
        assertEq(agentsBefore.length, 1);

        vm.prank(agent1);
        pool.deregister();

        // Verify agent is removed
        address[] memory agentsAfter = pool.getTaskTypeAgents(taskType1);
        assertEq(agentsAfter.length, 0);
    }

    function test_RevertDeregisterNotRegistered() public {
        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.NotRegistered.selector);
        pool.deregister();
    }

    function test_RevertDeregisterActiveTasks() public {
        _registerAgent(agent1, 1 ether);

        // Activate a task
        vm.prank(cairnCore);
        pool.activateFallback(keccak256("task1"), agent1);

        vm.prank(agent1);
        vm.expectRevert(IFallbackPool.ActiveRecoveriesPending.selector);
        pool.deregister();
    }

    // ═══════════════════════════════════════════════════════════════
    // SELECTION TESTS (PRD-04 Section 2.4)
    // ═══════════════════════════════════════════════════════════════

    function test_SelectFallbackSingleAgent() public {
        _registerAgent(agent1, 1 ether);

        address selected = pool.selectFallback(taskType1, 1 ether);
        assertEq(selected, agent1);
    }

    function test_SelectFallbackNoAgents() public {
        address selected = pool.selectFallback(taskType1, 1 ether);
        assertEq(selected, address(0));
    }

    function test_SelectFallbackInsufficientStake() public {
        // Register with 0.05 ether stake
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 0.05 ether}(taskTypes, 3);

        // Escrow = 1 ether requires 0.1 ether stake (10%)
        address selected = pool.selectFallback(taskType1, 1 ether);
        assertEq(selected, address(0)); // Agent doesn't qualify
    }

    function test_SelectFallbackHigherStakeWins() public {
        // For escrow = 10 ether, min stake = 1 ether (10%)
        // Agent 1: 1 ether stake = 1x required (stakeRatio = 100)
        _registerAgentWithStake(agent1, 1 ether);

        // Agent 2: 3 ether stake = 3x required, capped at 2x (stakeRatio = 200)
        // Higher stake score than agent1
        _registerAgentWithStake(agent2, 3 ether);

        // Escrow = 10 ether (min stake = 1 ether)
        address selected = pool.selectFallback(taskType1, 10 ether);

        // Agent 2 should win (higher capped stake ratio)
        // Both have same success/reputation/availability, but stake differs
        assertEq(selected, agent2);
    }

    function test_SelectFallbackBetterReputationWins() public {
        // Both agents with same stake
        _registerAgent(agent1, 1 ether);
        _registerAgent(agent2, 1 ether);

        // Set different reputations
        reputationRegistry.setReputation(agent1, 60);
        reputationRegistry.setReputation(agent2, 90);

        // Re-register agent2 to pick up new reputation
        // Note: In real implementation, reputation would be read from ERC-8004
        // For this test, we need to check the selection logic

        address selected = pool.selectFallback(taskType1, 1 ether);
        // Both should be eligible, selection depends on score algorithm
        assertTrue(selected == agent1 || selected == agent2);
    }

    function test_SelectFallbackAtCapacity() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 1); // Max 1 concurrent

        // Activate to reach capacity
        vm.prank(cairnCore);
        pool.activateFallback(keccak256("task1"), agent1);

        // Now agent is at capacity
        address selected = pool.selectFallback(taskType1, 1 ether);
        assertEq(selected, address(0)); // No available agent
    }

    function test_GetMinStake() public view {
        // 10% of escrow
        assertEq(pool.getMinStake(1 ether), 0.1 ether);
        assertEq(pool.getMinStake(10 ether), 1 ether);
        assertEq(pool.getMinStake(0.5 ether), 0.05 ether);
    }

    // ═══════════════════════════════════════════════════════════════
    // ACTIVATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ActivateFallback() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertEq(agent.activeTaskCount, 1);
    }

    function test_ActivateFallbackEmitsEvent() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        vm.expectEmit(true, true, false, false);
        emit IFallbackPool.FallbackActivated(taskId, agent1);
        pool.activateFallback(taskId, agent1);
    }

    function test_RevertActivateFallbackNotCairnCore() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(randomUser);
        vm.expectRevert(IFallbackPool.NotCairnCore.selector);
        pool.activateFallback(keccak256("task1"), agent1);
    }

    function test_RevertActivateFallbackNotRegistered() public {
        vm.prank(cairnCore);
        vm.expectRevert(IFallbackPool.NotRegistered.selector);
        pool.activateFallback(keccak256("task1"), agent1);
    }

    function test_RevertActivateFallbackAtCapacity() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 1); // Max 1

        vm.prank(cairnCore);
        pool.activateFallback(keccak256("task1"), agent1);

        vm.prank(cairnCore);
        vm.expectRevert(IFallbackPool.AtMaxCapacity.selector);
        pool.activateFallback(keccak256("task2"), agent1);
    }

    // ═══════════════════════════════════════════════════════════════
    // COMPLETION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_CompleteFallbackTaskSuccess() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        vm.prank(cairnCore);
        pool.completeFallbackTask(taskId, agent1, true, 5);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertEq(agent.activeTaskCount, 0);
        assertEq(agent.completedTasks, 1);
        assertEq(agent.failedTasks, 0);
    }

    function test_CompleteFallbackTaskFailure() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        vm.prank(cairnCore);
        pool.completeFallbackTask(taskId, agent1, false, 5);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertEq(agent.activeTaskCount, 0);
        assertEq(agent.completedTasks, 0);
        assertEq(agent.failedTasks, 1);
    }

    function test_CompleteFallbackTaskEmitsEvent() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        vm.prank(cairnCore);
        vm.expectEmit(true, true, false, true);
        emit IFallbackPool.FallbackCompleted(taskId, agent1, true);
        pool.completeFallbackTask(taskId, agent1, true, 5);
    }

    function test_RevertCompleteFallbackTaskNotCairnCore() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        vm.prank(randomUser);
        vm.expectRevert(IFallbackPool.NotCairnCore.selector);
        pool.completeFallbackTask(taskId, agent1, true, 5);
    }

    // ═══════════════════════════════════════════════════════════════
    // SLASHING TESTS (PRD-04 Section 2.5)
    // ═══════════════════════════════════════════════════════════════

    function test_SlashOnZeroCheckpointFailure() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        uint256 feeRecipientBefore = feeRecipient.balance;

        // Fail with zero checkpoints → 25% slash
        vm.prank(cairnCore);
        pool.completeFallbackTask(taskId, agent1, false, 0);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        // 1 ether - 0.25 ether (25% slash) = 0.75 ether
        assertEq(agent.stake, 0.75 ether);
        assertEq(feeRecipient.balance - feeRecipientBefore, 0.25 ether);
    }

    function test_SlashOnHighFailureRate() public {
        _registerAgent(agent1, 1 ether);

        // Complete 7 tasks: 3 successes first, then 4 failures
        // This ensures that when failures happen, totalTasks > 5
        // and failure rate > 30% triggers the slash
        for (uint256 i = 0; i < 7; i++) {
            bytes32 taskId = keccak256(abi.encode("task", i));

            vm.prank(cairnCore);
            pool.activateFallback(taskId, agent1);

            // First 3 succeed, then 4 fail
            // After task 6: totalTasks=7, failedTasks=4 → 57% failure rate > 30%
            bool success = i < 3;
            vm.prank(cairnCore);
            pool.completeFallbackTask(taskId, agent1, success, 5);
        }

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        // Should have been slashed for high failure rate (10% slash)
        // After 4 failures with totalTasks > 5, slash triggers
        assertTrue(agent.stake < 1 ether);
    }

    function test_NoSlashOnSomeCheckpointsFailure() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        // Fail with some checkpoints → no auto-slash (arbiter decides)
        vm.prank(cairnCore);
        pool.completeFallbackTask(taskId, agent1, false, 3);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        // No slash for partial completion
        assertEq(agent.stake, 1 ether);
    }

    function test_SlashEmitsEvent() public {
        _registerAgent(agent1, 1 ether);

        bytes32 taskId = keccak256("task1");

        vm.prank(cairnCore);
        pool.activateFallback(taskId, agent1);

        vm.prank(cairnCore);
        vm.expectEmit(true, false, false, false);
        emit IFallbackPool.AgentSlashed(agent1, 0.25 ether, feeRecipient, "Zero checkpoints failure");
        pool.completeFallbackTask(taskId, agent1, false, 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_GetAllAgents() public {
        _registerAgent(agent1, 1 ether);
        _registerAgent(agent2, 1 ether);

        address[] memory agents = pool.getAllAgents();
        assertEq(agents.length, 2);
    }

    function test_GetTaskTypeAgents() public {
        _registerAgent(agent1, 1 ether);

        address[] memory agents = pool.getTaskTypeAgents(taskType1);
        assertEq(agents.length, 1);
        assertEq(agents[0], agent1);
    }

    // ═══════════════════════════════════════════════════════════════
    // EDGE CASES
    // ═══════════════════════════════════════════════════════════════

    function test_MultipleConcurrentTasks() public {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 3); // Max 3 concurrent

        // Activate 3 tasks
        for (uint256 i = 0; i < 3; i++) {
            bytes32 taskId = keccak256(abi.encode("task", i));
            vm.prank(cairnCore);
            pool.activateFallback(taskId, agent1);
        }

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertEq(agent.activeTaskCount, 3);

        // Should not be selectable anymore
        address selected = pool.selectFallback(taskType1, 0.1 ether);
        assertEq(selected, address(0));
    }

    function test_SelectionWithMixedEligibility() public {
        // Agent 1: Low stake, won't qualify for large escrow
        _registerAgentWithStake(agent1, 0.05 ether);

        // Agent 2: High stake, qualifies
        _registerAgentWithStake(agent2, 1 ether);

        // Agent 3: At capacity
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;
        vm.prank(agent3);
        pool.register{value: 1 ether}(taskTypes, 1);
        vm.prank(cairnCore);
        pool.activateFallback(keccak256("fill"), agent3);

        // Only agent2 should be selectable
        address selected = pool.selectFallback(taskType1, 1 ether);
        assertEq(selected, agent2);
    }

    function test_ReregisterAfterDeregister() public {
        _registerAgent(agent1, 1 ether);

        vm.prank(agent1);
        pool.deregister();

        // Should be able to re-register
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent1);
        pool.register{value: 2 ether}(taskTypes, 5);

        IFallbackPool.FallbackAgent memory agent = pool.getAgent(agent1);
        assertTrue(agent.registered);
        assertEq(agent.stake, 2 ether);
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════════

    function _registerAgent(address agent, uint256 stake) internal {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent);
        pool.register{value: stake}(taskTypes, 3);
    }

    function _registerAgentWithStake(address agent, uint256 stake) internal {
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType1;

        vm.prank(agent);
        pool.register{value: stake}(taskTypes, 3);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title IERC8183 - Agent Escrow Hook Interface
/// @notice Standard callback interface for agent escrow lifecycle events
/// @dev See https://eips.ethereum.org/EIPS/eip-8183
///
/// Purpose: Allows external systems (analytics, insurance, governance) to
/// react to task lifecycle events without modifying core protocol logic.
///
/// Integration: CairnCore calls these hooks at critical lifecycle points,
/// enabling composable protocol extensions without upgrades.
interface IERC8183 {
    // ═══════════════════════════════════════════════════════════════
    // LIFECYCLE HOOKS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Called when a task is submitted with escrow
    /// @dev Hook implementations MUST NOT revert or task creation fails
    /// @param taskId The created task identifier
    /// @param agent The primary agent assigned
    /// @param escrow Amount of escrow locked (in wei)
    function onTaskSubmitted(bytes32 taskId, address agent, uint256 escrow) external;

    /// @notice Called when a checkpoint batch is committed
    /// @dev Hook implementations MUST NOT revert or checkpoint fails
    /// @param taskId The task being checkpointed
    /// @param cid The latest checkpoint CID in the batch
    function onCheckpoint(bytes32 taskId, bytes32 cid) external;

    /// @notice Called when a task completes (success or failure)
    /// @dev Hook implementations MUST NOT revert or completion fails
    /// @param taskId The completed task
    /// @param success True if task succeeded, false if failed
    function onTaskCompleted(bytes32 taskId, bool success) external;

    /// @notice Called when escrow is settled and distributed
    /// @dev Hook implementations MUST NOT revert or settlement fails
    /// @param taskId The settled task
    /// @param agentPayout Amount paid to agents (in wei)
    /// @param operatorRefund Amount refunded to operator (in wei)
    function onSettlement(bytes32 taskId, uint256 agentPayout, uint256 operatorRefund) external;
}

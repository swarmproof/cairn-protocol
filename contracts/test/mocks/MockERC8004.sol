// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC8004} from "../../src/interfaces/IERC8004.sol";

/// @title MockERC8004 - Test implementation of ERC-8004 reputation registry
/// @notice Allows arbitrary reputation setting for testing purposes
contract MockERC8004 is IERC8004 {
    /// @notice Global reputation scores
    mapping(address => uint256) private _globalReputation;

    /// @notice Task-type-specific reputation scores
    mapping(address => mapping(bytes32 => uint256)) private _taskTypeReputation;

    /// @notice Task types an agent has reputation in
    mapping(address => bytes32[]) private _agentTaskTypes;

    /// @notice Set global reputation (for testing)
    function setReputation(address agent, uint256 reputation) external {
        _globalReputation[agent] = reputation;
    }

    /// @notice Set task-type-specific reputation (for testing)
    function setReputationForType(address agent, bytes32 taskType, uint256 reputation) external {
        if (_taskTypeReputation[agent][taskType] == 0) {
            _agentTaskTypes[agent].push(taskType);
        }
        _taskTypeReputation[agent][taskType] = reputation;
    }

    /// @inheritdoc IERC8004
    function getReputation(address agent) external view override returns (uint256) {
        uint256 rep = _globalReputation[agent];
        // Default to 70 if not set (matches original mock behavior)
        return rep > 0 ? rep : 70;
    }

    /// @inheritdoc IERC8004
    function getReputationForType(address agent, bytes32 taskType)
        external
        view
        override
        returns (uint256)
    {
        uint256 rep = _taskTypeReputation[agent][taskType];
        // Default to global reputation if task-specific not set
        return rep > 0 ? rep : this.getReputation(agent);
    }

    /// @inheritdoc IERC8004
    function getTaskTypes(address agent) external view override returns (bytes32[] memory) {
        return _agentTaskTypes[agent];
    }

    /// @inheritdoc IERC8004
    function reportSuccess(address agent, bytes32 taskType) external override {
        // Increase reputation by 1 (capped at 100)
        uint256 current = _taskTypeReputation[agent][taskType];
        if (current == 0) {
            current = this.getReputation(agent);
            _agentTaskTypes[agent].push(taskType);
        }
        if (current < 100) {
            _taskTypeReputation[agent][taskType] = current + 1;
        }

        emit ReputationUpdated(agent, taskType, current + 1, current);
    }

    /// @inheritdoc IERC8004
    function reportFailure(address agent, bytes32 taskType, uint8 severity) external override {
        // Decrease reputation by severity (floor at 0)
        uint256 current = _taskTypeReputation[agent][taskType];
        if (current == 0) {
            current = this.getReputation(agent);
            _agentTaskTypes[agent].push(taskType);
        }

        uint256 newRep;
        if (current > severity) {
            newRep = current - severity;
        } else {
            newRep = 0;
        }

        _taskTypeReputation[agent][taskType] = newRep;
        emit ReputationUpdated(agent, taskType, newRep, current);
    }
}

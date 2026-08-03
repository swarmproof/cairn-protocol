// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

/// @title IRecoveryRouterV2 - Optional v2 extension for three-tier routing
/// @notice Exposes the three-tier routing classifier introduced in RecoveryRouterV2
///         (WHITEPAPER_V2 §6.4, PRD-04). This is an OPTIONAL extension to
///         IRecoveryRouter: CairnCore only casts its router to this interface
///         when three-tier routing is explicitly enabled by governance, so a v1
///         router that does not implement these methods remains fully compatible
///         under the default (binary) routing path.
interface IRecoveryRouterV2 {
    /// @notice Classify a recovery score into a routing tier.
    /// @param score Recovery score on the 0-1e18 scale.
    /// @return tier 2 = RECOVERING (full scope), 1 = RECOVERING (reduced scope), 0 = DISPUTED.
    function routingTier(uint256 score) external view returns (uint8 tier);

    /// @notice Upper routing threshold — score >= this routes to full-scope recovery.
    function upperThreshold() external view returns (uint256);

    /// @notice Lower routing threshold — score in [lower, upper) routes to reduced-scope
    /// recovery.
    function lowerThreshold() external view returns (uint256);
}

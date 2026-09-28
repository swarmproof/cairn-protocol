// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {ICairnTypes} from "../interfaces/ICairnTypes.sol";
import {ud, unwrap, pow as udPow} from "@prb/math/UD60x18.sol";

/// @title MultiplicativeRecoveryScore - r = F^0.80 × B^0.35 × D^0.15
/// @author CAIRN Protocol
/// @notice The v2 recovery score, shared by RecoveryRouterV2 and its UUPS variant so both
///         compute identical scores.
library MultiplicativeRecoveryScore {
    /// @notice Precision scale (1e18 = 100% in UD60x18)
    uint256 internal constant PRECISION = 1e18;

    /// @notice Budget exponent b = 0.35 in UD60x18
    uint256 internal constant B_EXPONENT = 0.35e18;

    /// @notice Deadline exponent c = 0.15 in UD60x18
    uint256 internal constant D_EXPONENT = 0.15e18;

    /// @notice F^0.80 for LIVENESS class weight 0.70 (0.70^0.80, 18 decimals)
    uint256 internal constant F_POW_LIVENESS = 751_758_646_650_045_568;

    /// @notice F^0.80 for RESOURCE class weight 0.30 (0.30^0.80, 18 decimals)
    uint256 internal constant F_POW_RESOURCE = 381_677_890_961_817_600;

    /// @notice F^0.80 for LOGIC class weight 0.00
    uint256 internal constant F_POW_LOGIC = 0;

    /// @notice A B or D input exceeds 1e18
    error InputOutOfRange();

    /// @notice Raw class weight F (not raised to 0.80)
    function classWeight(ICairnTypes.FailureClass failureClass) internal pure returns (uint256) {
        if (failureClass == ICairnTypes.FailureClass.LIVENESS) return 0.70e18;
        if (failureClass == ICairnTypes.FailureClass.RESOURCE) return 0.30e18;
        return 0;
    }

    /// @notice F^0.80 via lookup (three possible values)
    function fPow(ICairnTypes.FailureClass failureClass) internal pure returns (uint256) {
        if (failureClass == ICairnTypes.FailureClass.LIVENESS) return F_POW_LIVENESS;
        if (failureClass == ICairnTypes.FailureClass.RESOURCE) return F_POW_RESOURCE;
        return F_POW_LOGIC;
    }

    /// @notice Compute r = F^0.80 × B^0.35 × D^0.15 on the 1e18 scale
    /// @dev LOGIC short-circuits to 0. PRBMath pow(0, e) = 0 for e != 0, so a zero B or D
    ///      also yields 0.
    function score(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    ) internal pure returns (uint256) {
        if (budgetRemaining > PRECISION || deadlineRemaining > PRECISION) {
            revert InputOutOfRange();
        }
        uint256 f = fPow(failureClass);
        if (f == 0) return 0;

        uint256 bPow = unwrap(udPow(ud(budgetRemaining), ud(B_EXPONENT)));
        uint256 dPow = unwrap(udPow(ud(deadlineRemaining), ud(D_EXPONENT)));

        uint256 r = (f * bPow) / PRECISION;
        return (r * dPow) / PRECISION;
    }
}

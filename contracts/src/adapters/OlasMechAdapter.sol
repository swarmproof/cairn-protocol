// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {IOlasMech} from "../interfaces/IOlasMech.sol";

/// @title OlasMechAdapter - Adapter for querying Olas Mech Marketplace
/// @author CAIRN Protocol
/// @notice Bridges CAIRN task types with Olas Mech capabilities
/// @dev Maps CAIRN's task taxonomy to Olas service types for fallback selection
///
/// Integration Pattern:
/// 1. Admin maps CAIRN task types to Olas capabilities via mapTaskType()
/// 2. FallbackPool calls queryAvailableMechs() during fallback selection
/// 3. Adapter returns eligible Olas mechs as fallback candidates
///
/// Based on PRD-04 Section 2.7: Olas Mech Marketplace Integration
contract OlasMechAdapter {
    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Olas Mech registry contract
    IOlasMech public immutable mechRegistry;

    /// @notice Mapping from CAIRN task types to Olas capabilities
    /// @dev cairnTaskType => olasCapability
    /// Example: keccak256("defi.price_fetch") => keccak256("price_oracle")
    mapping(bytes32 => bytes32) public cairnToOlasCapability;

    /// @notice Reverse mapping for Olas capabilities to CAIRN task types
    /// @dev olasCapability => cairnTaskTypes[]
    mapping(bytes32 => bytes32[]) public olasToCairnCapability;

    /// @notice Minimum reputation score for Olas mechs
    /// @dev Calculated from requestsCompleted / (requestsCompleted + requestsFailed)
    uint256 public minOlasReputation = 70; // 70% success rate

    /// @notice Admin address for mapping management
    address public admin;

    /// @notice Whether Olas integration is enabled
    bool public enabled = true;

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    event TaskTypeMapped(bytes32 indexed cairnType, bytes32 indexed olasCapability);
    event TaskTypeUnmapped(bytes32 indexed cairnType, bytes32 indexed olasCapability);
    event MinReputationUpdated(uint256 oldValue, uint256 newValue);
    event AdapterEnabled(bool enabled);

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    error OnlyAdmin();
    error ZeroAddress();
    error AdapterDisabled();
    error InvalidReputation();
    error NoMapping();

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════

    /// @notice Initialize the Olas Mech adapter
    /// @param _mechRegistry Olas Mech registry contract address
    /// @param _admin Admin address for mapping management
    constructor(address _mechRegistry, address _admin) {
        if (_mechRegistry == address(0)) revert ZeroAddress();
        if (_admin == address(0)) revert ZeroAddress();

        mechRegistry = IOlasMech(_mechRegistry);
        admin = _admin;

        // Initialize default mappings (PRD-04 Section 2.7)
        _setDefaultMappings();
    }

    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════

    modifier onlyAdmin() {
        if (msg.sender != admin) revert OnlyAdmin();
        _;
    }

    modifier whenEnabled() {
        if (!enabled) revert AdapterDisabled();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // CORE FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Query available Olas mechs for a CAIRN task type
    /// @dev Called by FallbackPool during fallback selection
    /// @param taskType CAIRN task type (e.g., keccak256("defi.price_fetch"))
    /// @return mechs Array of mech addresses eligible for fallback
    function queryAvailableMechs(bytes32 taskType)
        external
        view
        whenEnabled
        returns (address[] memory mechs)
    {
        // Get mapped Olas capability
        bytes32 olasCapability = cairnToOlasCapability[taskType];
        if (olasCapability == bytes32(0)) {
            // No mapping exists - return empty array
            return new address[](0);
        }

        // Query Olas registry for mechs with this capability
        uint256[] memory serviceIds = mechRegistry.getMechsByCapability(olasCapability);

        // Filter by reputation and active status
        address[] memory candidates = new address[](serviceIds.length);
        uint256 count = 0;

        for (uint256 i = 0; i < serviceIds.length; i++) {
            if (_isOlasMechEligible(serviceIds[i])) {
                address mechAddr = mechRegistry.getMechAddress(serviceIds[i]);
                candidates[count] = mechAddr;
                count++;
            }
        }

        // Resize array to actual count
        mechs = new address[](count);
        for (uint256 i = 0; i < count; i++) {
            mechs[i] = candidates[i];
        }

        return mechs;
    }

    /// @notice Check if an Olas mech is eligible for CAIRN fallback
    /// @param mechAddress Olas mech contract address
    /// @param taskType CAIRN task type
    /// @return Whether the mech is eligible
    function isOlasMechEligible(address mechAddress, bytes32 taskType)
        external
        view
        whenEnabled
        returns (bool)
    {
        // Get mapped Olas capability
        bytes32 olasCapability = cairnToOlasCapability[taskType];
        if (olasCapability == bytes32(0)) return false;

        // Get all mechs with this capability
        uint256[] memory serviceIds = mechRegistry.getMechsByCapability(olasCapability);

        // Find the mech's service ID
        for (uint256 i = 0; i < serviceIds.length; i++) {
            address mechAddr = mechRegistry.getMechAddress(serviceIds[i]);
            if (mechAddr == mechAddress) {
                return _isOlasMechEligible(serviceIds[i]);
            }
        }

        return false;
    }

    /// @notice Get Olas mech information for a service ID
    /// @param serviceId Olas service ID
    /// @return Mech information struct
    function getOlasMechInfo(uint256 serviceId) external view returns (IOlasMech.MechInfo memory) {
        return mechRegistry.getMech(serviceId);
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Map a CAIRN task type to an Olas capability
    /// @dev Enables Olas mechs with this capability to serve as fallbacks
    /// @param cairnType CAIRN task type (e.g., keccak256("defi.price_fetch"))
    /// @param olasCapability Olas capability (e.g., keccak256("price_oracle"))
    function mapTaskType(bytes32 cairnType, bytes32 olasCapability) external onlyAdmin {
        cairnToOlasCapability[cairnType] = olasCapability;
        olasToCairnCapability[olasCapability].push(cairnType);

        emit TaskTypeMapped(cairnType, olasCapability);
    }

    /// @notice Unmap a CAIRN task type from Olas capability
    /// @param cairnType CAIRN task type to unmap
    function unmapTaskType(bytes32 cairnType) external onlyAdmin {
        bytes32 olasCapability = cairnToOlasCapability[cairnType];
        if (olasCapability == bytes32(0)) revert NoMapping();

        delete cairnToOlasCapability[cairnType];

        // Remove from reverse mapping
        bytes32[] storage cairnTypes = olasToCairnCapability[olasCapability];
        for (uint256 i = 0; i < cairnTypes.length; i++) {
            if (cairnTypes[i] == cairnType) {
                cairnTypes[i] = cairnTypes[cairnTypes.length - 1];
                cairnTypes.pop();
                break;
            }
        }

        emit TaskTypeUnmapped(cairnType, olasCapability);
    }

    /// @notice Update minimum reputation threshold for Olas mechs
    /// @param newMinReputation New minimum reputation (0-100)
    function setMinReputation(uint256 newMinReputation) external onlyAdmin {
        if (newMinReputation > 100) revert InvalidReputation();

        uint256 oldValue = minOlasReputation;
        minOlasReputation = newMinReputation;

        emit MinReputationUpdated(oldValue, newMinReputation);
    }

    /// @notice Enable or disable Olas integration
    /// @param _enabled Whether to enable the adapter
    function setEnabled(bool _enabled) external onlyAdmin {
        enabled = _enabled;
        emit AdapterEnabled(_enabled);
    }

    /// @notice Update admin address
    /// @param newAdmin New admin address
    function setAdmin(address newAdmin) external onlyAdmin {
        if (newAdmin == address(0)) revert ZeroAddress();
        admin = newAdmin;
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Check if an Olas mech meets eligibility criteria
    /// @param serviceId Olas service ID
    /// @return Whether the mech is eligible
    function _isOlasMechEligible(uint256 serviceId) internal view returns (bool) {
        // Check if mech is active
        if (!mechRegistry.isMechActive(serviceId)) return false;

        // Get mech info
        IOlasMech.MechInfo memory mechInfo = mechRegistry.getMech(serviceId);

        // Calculate reputation (success rate)
        uint256 totalRequests = mechInfo.requestsCompleted + mechInfo.requestsFailed;
        if (totalRequests == 0) {
            // New mech - allow if active
            return true;
        }

        uint256 successRate = (mechInfo.requestsCompleted * 100) / totalRequests;
        return successRate >= minOlasReputation;
    }

    /// @notice Initialize default CAIRN -> Olas task type mappings
    /// @dev Based on PRD-04 Section 2.7 examples
    function _setDefaultMappings() internal {
        // DeFi task types
        cairnToOlasCapability[keccak256("defi.price_fetch")] = keccak256("price_oracle");
        cairnToOlasCapability[keccak256("defi.trade_execute")] = keccak256("trading_bot");
        cairnToOlasCapability[keccak256("defi.liquidity_provide")] = keccak256("liquidity_manager");

        // Data task types
        cairnToOlasCapability[keccak256("data.report_generate")] = keccak256("data_analyst");
        cairnToOlasCapability[keccak256("data.scrape_website")] = keccak256("web_scraper");

        // Governance task types
        cairnToOlasCapability[keccak256("governance.vote_delegate")] = keccak256("governance_agent");

        // Compute task types
        cairnToOlasCapability[keccak256("compute.model_inference")] = keccak256("ai_inference");

        // Initialize reverse mappings
        olasToCairnCapability[keccak256("price_oracle")].push(keccak256("defi.price_fetch"));
        olasToCairnCapability[keccak256("trading_bot")].push(keccak256("defi.trade_execute"));
        olasToCairnCapability[keccak256("liquidity_manager")].push(keccak256("defi.liquidity_provide"));
        olasToCairnCapability[keccak256("data_analyst")].push(keccak256("data.report_generate"));
        olasToCairnCapability[keccak256("web_scraper")].push(keccak256("data.scrape_website"));
        olasToCairnCapability[keccak256("governance_agent")].push(keccak256("governance.vote_delegate"));
        olasToCairnCapability[keccak256("ai_inference")].push(keccak256("compute.model_inference"));
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW HELPERS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get all CAIRN task types mapped to an Olas capability
    /// @param olasCapability Olas capability identifier
    /// @return CAIRN task types array
    function getCairnTaskTypes(bytes32 olasCapability) external view returns (bytes32[] memory) {
        return olasToCairnCapability[olasCapability];
    }

    /// @notice Check if a task type mapping exists
    /// @param cairnType CAIRN task type
    /// @return Whether a mapping exists
    function hasMappingFor(bytes32 cairnType) external view returns (bool) {
        return cairnToOlasCapability[cairnType] != bytes32(0);
    }
}

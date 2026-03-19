import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatEther, formatUnits } from "viem";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format address for display (0x1234...5678)
export function formatAddress(address: string): string {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// Format bytes32 task ID for display
export function formatTaskId(taskId: string): string {
  if (!taskId) return '';
  return `${taskId.slice(0, 10)}...${taskId.slice(-6)}`;
}

// Format ETH value with proper decimals
export function formatEth(wei: bigint, decimals: number = 4): string {
  const eth = formatEther(wei);
  const num = parseFloat(eth);
  return num.toFixed(decimals);
}

// Format timestamp to relative time
export function formatRelativeTime(timestamp: number): string {
  const now = Math.floor(Date.now() / 1000);
  const diff = now - timestamp;

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Format deadline to countdown
export function formatDeadline(deadline: number): string {
  const now = Math.floor(Date.now() / 1000);
  const remaining = deadline - now;

  if (remaining <= 0) return 'Expired';
  if (remaining < 60) return `${remaining}s left`;
  if (remaining < 3600) return `${Math.floor(remaining / 60)}m left`;
  if (remaining < 86400) return `${Math.floor(remaining / 3600)}h left`;
  return `${Math.floor(remaining / 86400)}d left`;
}

// Convert bytes32 CID to IPFS CID string
export function bytes32ToCid(bytes32: string): string {
  // For MVP, we store a truncated CID hash
  // In production, this would be a proper IPFS CID conversion
  return bytes32.slice(2, 48); // Remove 0x prefix and take first 46 chars
}

// Get IPFS gateway URL for a CID
export function getIpfsUrl(cid: string): string {
  const gateway = process.env.NEXT_PUBLIC_IPFS_GATEWAY || 'https://gateway.pinata.cloud/ipfs';
  return `${gateway}/${cid}`;
}

// Calculate settlement percentages
export function calculateSettlementSplit(
  primaryCheckpoints: number,
  fallbackCheckpoints: number,
  protocolFeeBps: number = 50
): {
  primaryPercent: number;
  fallbackPercent: number;
  protocolPercent: number;
} {
  const totalCheckpoints = primaryCheckpoints + fallbackCheckpoints;
  if (totalCheckpoints === 0) {
    return { primaryPercent: 0, fallbackPercent: 0, protocolPercent: 0 };
  }

  const protocolPercent = protocolFeeBps / 100; // 0.5%
  const remainingPercent = 100 - protocolPercent;

  const primaryPercent = (primaryCheckpoints / totalCheckpoints) * remainingPercent;
  const fallbackPercent = (fallbackCheckpoints / totalCheckpoints) * remainingPercent;

  return {
    primaryPercent: Math.round(primaryPercent * 100) / 100,
    fallbackPercent: Math.round(fallbackPercent * 100) / 100,
    protocolPercent,
  };
}

// Check if demo mode is enabled
export function isDemoMode(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_MODE === 'true';
}

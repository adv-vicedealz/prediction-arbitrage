import { useEffect, useState } from 'react';
import { useTracker } from '../context/TrackerContext';
import { WalletPosition } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface MarketInfo {
  slug: string;
  trades_captured: number;
  tracking_duration_mins: number;
  market_end_time?: string;
  resolved?: boolean;
  winning_outcome?: string;
  coverage_percent?: number;
}

interface TrackingInfo {
  markets: MarketInfo[];
}

function PositionCard({ position, marketInfo }: { position: WalletPosition; marketInfo?: MarketInfo }) {
  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatShares = (value: number) => value.toFixed(2);
  const formatPrice = (value: number) => `$${value.toFixed(3)}`;

  const getEdgeColor = (edge: number) => {
    if (edge > 0.02) return 'text-green-400';
    if (edge > 0) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getHedgeColor = (hedgeRatio: number) => {
    if (hedgeRatio > 0.9) return 'text-green-400';
    if (hedgeRatio > 0.7) return 'text-yellow-400';
    return 'text-orange-400';
  };

  // Calculate profit/loss
  const completeSets = position.complete_sets;
  const profitPerSet = position.edge; // edge is already 1 - combined_price
  const totalProfit = completeSets * profitPerSet;

  // Parse market time from slug (e.g., btc-updown-15m-1768071600)
  const slugParts = position.market_slug.split('-');
  const marketTimestamp = parseInt(slugParts[slugParts.length - 1]);
  const marketEndTime = new Date((marketTimestamp + 15 * 60) * 1000); // 15 min after start
  const isEnded = new Date() > marketEndTime;

  return (
    <div className={`rounded-lg p-4 mb-3 ${isEnded ? 'bg-gray-700/30 border border-gray-600' : 'bg-gray-700/50'}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-white">{position.wallet_name}</h3>
            {isEnded ? (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-600 text-gray-300">Ended</span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400 animate-pulse">Live</span>
            )}
          </div>
          <p className="text-xs text-gray-400 truncate max-w-[200px]" title={position.market_slug}>
            {position.market_slug}
          </p>
        </div>
        <div className="text-right">
          <div className={`text-sm font-medium ${getEdgeColor(position.edge)}`}>
            Edge: {formatPercent(position.edge)}
          </div>
          <div className={`text-xs ${getHedgeColor(position.hedge_ratio)}`}>
            Hedge: {formatPercent(position.hedge_ratio)}
          </div>
        </div>
      </div>

      {/* Coverage & Resolution Info */}
      {marketInfo && (
        <div className="mb-3 p-2 bg-gray-800/50 rounded text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="text-gray-400">Coverage:</span>
            <span className={`font-medium ${
              (marketInfo.coverage_percent || 0) >= 80 ? 'text-green-400' :
              (marketInfo.coverage_percent || 0) >= 40 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {marketInfo.coverage_percent?.toFixed(0) || 0}%
            </span>
          </div>
          {/* Coverage bar */}
          <div className="w-full bg-gray-700 rounded-full h-1 mb-2">
            <div
              className={`h-1 rounded-full ${
                (marketInfo.coverage_percent || 0) >= 80 ? 'bg-green-500' :
                (marketInfo.coverage_percent || 0) >= 40 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${Math.min(100, marketInfo.coverage_percent || 0)}%` }}
            />
          </div>
          {marketInfo.resolved && (
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Result:</span>
              <span className={`font-medium ${
                marketInfo.winning_outcome === 'Up' ? 'text-blue-400' : 'text-orange-400'
              }`}>
                {marketInfo.winning_outcome} Won
              </span>
            </div>
          )}
        </div>
      )}

      {/* Shares Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-blue-500/10 rounded p-2">
          <div className="text-xs text-blue-400 mb-1">UP</div>
          <div className="text-white font-medium">{formatShares(position.up_shares)}</div>
          <div className="text-xs text-gray-400">@ {formatPrice(position.avg_up_price)}</div>
        </div>
        <div className="bg-orange-500/10 rounded p-2">
          <div className="text-xs text-orange-400 mb-1">DOWN</div>
          <div className="text-white font-medium">{formatShares(position.down_shares)}</div>
          <div className="text-xs text-gray-400">@ {formatPrice(position.avg_down_price)}</div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="flex justify-between text-xs text-gray-400 mb-2">
        <span>Complete sets: {formatShares(position.complete_sets)}</span>
        <span>Trades: {position.total_trades}</span>
      </div>

      {/* Profit/Loss */}
      <div className={`text-center py-2 rounded ${
        totalProfit > 0 ? 'bg-green-500/10' : totalProfit < 0 ? 'bg-red-500/10' : 'bg-gray-600/30'
      }`}>
        <span className="text-xs text-gray-400">Est. P/L: </span>
        <span className={`font-medium ${
          totalProfit > 0 ? 'text-green-400' : totalProfit < 0 ? 'text-red-400' : 'text-gray-400'
        }`}>
          {totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(2)} USDC
        </span>
      </div>
    </div>
  );
}

export function PositionsPanel() {
  const { state, selectWallet } = useTracker();
  const [trackingInfo, setTrackingInfo] = useState<TrackingInfo | null>(null);

  useEffect(() => {
    const fetchTrackingInfo = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/tracking-info`);
        if (res.ok) {
          setTrackingInfo(await res.json());
        }
      } catch (e) {
        console.error('Failed to fetch tracking info');
      }
    };
    fetchTrackingInfo();
    const interval = setInterval(fetchTrackingInfo, 10000);
    return () => clearInterval(interval);
  }, []);

  const positions = Object.values(state.positions);
  const filteredPositions = state.selectedWallet
    ? positions.filter((p) => p.wallet.toLowerCase() === state.selectedWallet?.toLowerCase())
    : positions;

  // Sort: live markets first, then by trades count
  const sortedPositions = [...filteredPositions].sort((a, b) => {
    const aTimestamp = parseInt(a.market_slug.split('-').pop() || '0');
    const bTimestamp = parseInt(b.market_slug.split('-').pop() || '0');
    const aEndTime = (aTimestamp + 15 * 60) * 1000;
    const bEndTime = (bTimestamp + 15 * 60) * 1000;
    const now = Date.now();
    const aIsLive = now < aEndTime;
    const bIsLive = now < bEndTime;

    if (aIsLive && !bIsLive) return -1;
    if (!aIsLive && bIsLive) return 1;
    return b.total_trades - a.total_trades;
  });

  // Get market info for each position
  const getMarketInfo = (slug: string): MarketInfo | undefined => {
    return trackingInfo?.markets.find(m => m.slug === slug);
  };

  // Calculate totals
  const totalProfit = positions.reduce((sum, p) => sum + (p.complete_sets * p.edge), 0);
  const totalTrades = positions.reduce((sum, p) => sum + p.total_trades, 0);

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white">Positions</h2>
        {state.selectedWallet && (
          <button
            onClick={() => selectWallet(null)}
            className="text-xs text-gray-400 hover:text-white"
          >
            Clear filter
          </button>
        )}
      </div>

      {/* Summary */}
      {positions.length > 0 && (
        <div className="mb-4 p-3 bg-gray-700/30 rounded-lg flex justify-between text-sm">
          <div>
            <span className="text-gray-400">Markets: </span>
            <span className="text-white font-medium">{positions.length}</span>
          </div>
          <div>
            <span className="text-gray-400">Trades: </span>
            <span className="text-white font-medium">{totalTrades}</span>
          </div>
          <div>
            <span className="text-gray-400">Total P/L: </span>
            <span className={`font-medium ${
              totalProfit > 0 ? 'text-green-400' : totalProfit < 0 ? 'text-red-400' : 'text-gray-400'
            }`}>
              {totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(2)} USDC
            </span>
          </div>
        </div>
      )}

      {sortedPositions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No positions yet
        </div>
      ) : (
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {sortedPositions.map((position) => (
            <PositionCard
              key={`${position.wallet}:${position.market_slug}`}
              position={position}
              marketInfo={getMarketInfo(position.market_slug)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

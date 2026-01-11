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

function TimeRemaining({ endTime }: { endTime: Date }) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const diff = endTime.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeLeft('Ended');
        return;
      }

      const mins = Math.floor(diff / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      setTimeLeft(`${mins}:${secs.toString().padStart(2, '0')}`);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [endTime]);

  const isEnded = timeLeft === 'Ended';

  return (
    <span className={`font-mono ${isEnded ? 'text-gray-400' : 'text-green-400'}`}>
      {timeLeft}
    </span>
  );
}

function PositionCard({ position, marketInfo }: { position: WalletPosition; marketInfo?: MarketInfo }) {
  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatShares = (value: number) => value.toFixed(2);
  const formatPrice = (value: number) => `$${value.toFixed(3)}`;
  const formatUSDC = (value: number) => `$${value.toFixed(2)}`;

  // Parse market time from slug (e.g., btc-updown-15m-1768071600)
  const slugParts = position.market_slug.split('-');
  const marketTimestamp = parseInt(slugParts[slugParts.length - 1]);
  const marketEndTime = new Date((marketTimestamp + 15 * 60) * 1000);
  const isEnded = new Date() > marketEndTime;

  // Calculate financials
  const totalCost = position.up_cost + position.down_cost;
  const completeSets = position.complete_sets;
  const profitPerSet = position.edge;
  const estimatedProfit = completeSets * profitPerSet;
  const profitMargin = totalCost > 0 ? (estimatedProfit / totalCost) * 100 : 0;

  // Get market type from slug
  const marketType = position.market_slug.includes('btc') ? 'BTC' :
                     position.market_slug.includes('eth') ? 'ETH' : 'OTHER';

  return (
    <div className={`rounded-xl border ${
      isEnded
        ? 'bg-gray-800/40 border-gray-700/50'
        : 'bg-gray-800/80 border-gray-600/50'
    }`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700/50">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm ${
              marketType === 'BTC' ? 'bg-orange-500/20 text-orange-400' :
              marketType === 'ETH' ? 'bg-blue-500/20 text-blue-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {marketType}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-white font-medium">{position.wallet_name}</span>
                {!isEnded && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                    Live
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 font-mono">{position.market_slug}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400 mb-1">Time Left</div>
            <TimeRemaining endTime={marketEndTime} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4">
        {/* Key Metrics Row */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">Edge</div>
            <div className={`text-lg font-bold ${
              position.edge > 0.02 ? 'text-green-400' :
              position.edge > 0 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {formatPercent(position.edge)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">Hedge</div>
            <div className={`text-lg font-bold ${
              position.hedge_ratio > 0.9 ? 'text-green-400' :
              position.hedge_ratio > 0.7 ? 'text-yellow-400' : 'text-orange-400'
            }`}>
              {formatPercent(position.hedge_ratio)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">Volume</div>
            <div className="text-lg font-bold text-white">
              {formatUSDC(totalCost)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-400 mb-1">Trades</div>
            <div className="text-lg font-bold text-white">
              {position.total_trades}
            </div>
          </div>
        </div>

        {/* Shares Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-medium text-blue-400">UP</span>
              <span className="text-xs text-gray-400">{formatPrice(position.avg_up_price)}</span>
            </div>
            <div className="text-xl font-bold text-white">{formatShares(position.up_shares)}</div>
            <div className="text-xs text-gray-500 mt-1">Cost: {formatUSDC(position.up_cost)}</div>
          </div>
          <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-medium text-orange-400">DOWN</span>
              <span className="text-xs text-gray-400">{formatPrice(position.avg_down_price)}</span>
            </div>
            <div className="text-xl font-bold text-white">{formatShares(position.down_shares)}</div>
            <div className="text-xs text-gray-500 mt-1">Cost: {formatUSDC(position.down_cost)}</div>
          </div>
        </div>

        {/* P/L Breakdown */}
        <div className={`rounded-lg p-3 ${
          estimatedProfit > 0 ? 'bg-green-500/10 border border-green-500/20' :
          estimatedProfit < 0 ? 'bg-red-500/10 border border-red-500/20' :
          'bg-gray-700/30 border border-gray-600/30'
        }`}>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-400">P/L Breakdown</span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              profitMargin > 0 ? 'bg-green-500/20 text-green-400' :
              profitMargin < 0 ? 'bg-red-500/20 text-red-400' :
              'bg-gray-600 text-gray-400'
            }`}>
              {profitMargin >= 0 ? '+' : ''}{profitMargin.toFixed(1)}% ROI
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <div className="text-xs text-gray-500">Cost Basis</div>
              <div className="text-white font-medium">{formatUSDC(totalCost)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Complete Sets</div>
              <div className="text-white font-medium">{formatShares(completeSets)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Est. Profit</div>
              <div className={`font-bold ${
                estimatedProfit > 0 ? 'text-green-400' :
                estimatedProfit < 0 ? 'text-red-400' : 'text-gray-400'
              }`}>
                {estimatedProfit >= 0 ? '+' : ''}{formatUSDC(estimatedProfit)}
              </div>
            </div>
          </div>
        </div>

        {/* Coverage bar (if tracking info available) */}
        {marketInfo && (
          <div className="mt-3 pt-3 border-t border-gray-700/50">
            <div className="flex justify-between items-center text-xs mb-1">
              <span className="text-gray-500">Coverage</span>
              <span className={`font-medium ${
                (marketInfo.coverage_percent || 0) >= 80 ? 'text-green-400' :
                (marketInfo.coverage_percent || 0) >= 40 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {marketInfo.coverage_percent?.toFixed(0) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all ${
                  (marketInfo.coverage_percent || 0) >= 80 ? 'bg-green-500' :
                  (marketInfo.coverage_percent || 0) >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, marketInfo.coverage_percent || 0)}%` }}
              />
            </div>
          </div>
        )}
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

  const getMarketInfo = (slug: string): MarketInfo | undefined => {
    return trackingInfo?.markets.find(m => m.slug === slug);
  };

  // Calculate totals
  const totalProfit = positions.reduce((sum, p) => sum + (p.complete_sets * p.edge), 0);
  const totalTrades = positions.reduce((sum, p) => sum + p.total_trades, 0);
  const totalVolume = positions.reduce((sum, p) => sum + p.up_cost + p.down_cost, 0);
  const avgEdge = positions.length > 0
    ? positions.reduce((sum, p) => sum + p.edge, 0) / positions.length
    : 0;

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

      {/* Enhanced Summary */}
      {positions.length > 0 && (
        <div className="mb-4 p-4 bg-gradient-to-r from-gray-700/50 to-gray-700/30 rounded-xl border border-gray-600/30">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <div className="text-xs text-gray-400 mb-1">Markets</div>
              <div className="text-xl font-bold text-white">{positions.length}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Trades</div>
              <div className="text-xl font-bold text-white">{totalTrades}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Volume</div>
              <div className="text-xl font-bold text-white">${totalVolume.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Avg Edge</div>
              <div className={`text-xl font-bold ${
                avgEdge > 0.02 ? 'text-green-400' : avgEdge > 0 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {(avgEdge * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Total P/L</div>
              <div className={`text-xl font-bold ${
                totalProfit > 0 ? 'text-green-400' : totalProfit < 0 ? 'text-red-400' : 'text-gray-400'
              }`}>
                {totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      )}

      {sortedPositions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-2">📊</div>
          <div>No positions yet</div>
          <div className="text-xs mt-1">Positions will appear when trades are detected</div>
        </div>
      ) : (
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
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

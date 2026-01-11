import { useEffect, useState } from 'react';
import { useTracker } from '../context/TrackerContext';
import { WalletPosition, MarketContext } from '../types';

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

  return <span className="font-mono text-gray-300">{timeLeft}</span>;
}

function PositionCard({ position, market }: { position: WalletPosition; market?: MarketContext }) {
  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatShares = (value: number) => value.toFixed(2);
  const formatPrice = (value: number) => `$${value.toFixed(3)}`;
  const formatUSDC = (value: number) => `$${value.toFixed(2)}`;

  // Parse market time from slug
  const slugParts = position.market_slug.split('-');
  const marketTimestamp = parseInt(slugParts[slugParts.length - 1]);
  const marketEndTime = new Date((marketTimestamp + 15 * 60) * 1000);
  const isLive = new Date() < marketEndTime;

  // Calculate financials
  const totalCost = position.up_cost + position.down_cost;
  const completeSets = position.complete_sets;
  const estimatedProfit = completeSets * position.edge;
  const profitMargin = totalCost > 0 ? (estimatedProfit / totalCost) * 100 : 0;

  // Calculate coverage percentage (how much of the position is hedged)
  const maxShares = Math.max(position.up_shares, position.down_shares);
  const coveragePercent = maxShares > 0 ? (completeSets / maxShares) * 100 : 0;

  // Get market type
  const marketType = position.market_slug.includes('btc') ? 'BTC' :
                     position.market_slug.includes('eth') ? 'ETH' : '???';

  // Determine win/loss for ended markets
  const isResolved = market?.resolved && market?.winning_outcome;
  const winningOutcome = market?.winning_outcome?.toLowerCase();

  // For hedged positions (complete_sets), we always profit from the edge
  // For unhedged positions, check if the dominant side won
  let resultStatus: 'won' | 'lost' | 'partial' | null = null;
  if (!isLive && isResolved) {
    const dominantSide = position.up_shares > position.down_shares ? 'up' : 'down';
    const unhedgedShares = Math.abs(position.up_shares - position.down_shares);

    if (unhedgedShares < 0.01) {
      // Fully hedged - won the edge
      resultStatus = 'won';
    } else if (dominantSide === winningOutcome) {
      // Unhedged side won
      resultStatus = 'won';
    } else {
      // Unhedged side lost
      resultStatus = completeSets > 0 ? 'partial' : 'lost';
    }
  }

  return (
    <div className="rounded-lg border border-gray-700">
      {/* Header Row */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center gap-3">
          {/* Live pulse indicator or ended dot */}
          {isLive ? (
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          ) : (
            <div className="w-2 h-2 rounded-full bg-gray-500" />
          )}
          <span className="text-xs font-bold text-gray-400 w-8">{marketType}</span>
          <span className="text-sm text-white">{position.wallet_name}</span>
          <span className="text-xs text-gray-500 font-mono">{position.market_slug}</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          {isLive ? (
            <span className="text-green-400 font-medium">
              <TimeRemaining endTime={marketEndTime} />
            </span>
          ) : (
            <div className="flex items-center gap-2">
              {isResolved ? (
                <>
                  <span className="text-gray-400">
                    Won: <span className={winningOutcome === 'up' ? 'text-blue-400' : 'text-orange-400'}>
                      {winningOutcome?.toUpperCase()}
                    </span>
                  </span>
                  {resultStatus === 'won' && (
                    <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">WIN</span>
                  )}
                  {resultStatus === 'lost' && (
                    <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">LOSS</span>
                  )}
                  {resultStatus === 'partial' && (
                    <span className="px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400">PARTIAL</span>
                  )}
                </>
              ) : (
                <span className="text-gray-500">Ended</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Content - Compact Grid */}
      <div className="px-4 py-3">
        <div className="grid grid-cols-6 gap-4 text-sm">
          {/* UP */}
          <div>
            <div className="text-xs text-gray-500 mb-1">UP</div>
            <div className="text-white">{formatShares(position.up_shares)}</div>
            <div className="text-xs text-gray-500">{formatPrice(position.avg_up_price)}</div>
          </div>

          {/* DOWN */}
          <div>
            <div className="text-xs text-gray-500 mb-1">DOWN</div>
            <div className="text-white">{formatShares(position.down_shares)}</div>
            <div className="text-xs text-gray-500">{formatPrice(position.avg_down_price)}</div>
          </div>

          {/* Volume */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Volume</div>
            <div className="text-white">{formatUSDC(totalCost)}</div>
            <div className="text-xs text-gray-500">{position.total_trades} trades</div>
          </div>

          {/* Edge & Coverage */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Edge</div>
            <div className={position.edge > 0 ? 'text-green-400' : 'text-red-400'}>
              {formatPercent(position.edge)}
            </div>
            <div className="text-xs text-gray-500">
              Hedge: {formatPercent(position.hedge_ratio)} | Cov: {coveragePercent.toFixed(0)}%
            </div>
          </div>

          {/* Complete Sets */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Sets</div>
            <div className="text-white">{formatShares(completeSets)}</div>
            <div className="text-xs text-gray-500">matched</div>
          </div>

          {/* P/L */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Est. P/L</div>
            <div className={estimatedProfit >= 0 ? 'text-green-400' : 'text-red-400'}>
              {estimatedProfit >= 0 ? '+' : ''}{formatUSDC(estimatedProfit)}
            </div>
            <div className="text-xs text-gray-500">
              {profitMargin >= 0 ? '+' : ''}{profitMargin.toFixed(1)}% ROI
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function PositionsPanel() {
  const { state, selectWallet } = useTracker();
  const [expanded, setExpanded] = useState(false);
  const LIMIT = 10;

  const positions = Object.values(state.positions);

  // Count live positions
  const now = Date.now();
  const liveCount = positions.filter((p) => {
    const timestamp = parseInt(p.market_slug.split('-').pop() || '0');
    const endTime = (timestamp + 15 * 60) * 1000;
    return now < endTime;
  }).length;

  const filteredPositions = state.selectedWallet
    ? positions.filter((p) => p.wallet.toLowerCase() === state.selectedWallet?.toLowerCase())
    : positions;

  // Sort: live markets first, then by timestamp (most recent to oldest)
  const sortedPositions = [...filteredPositions].sort((a, b) => {
    const aTimestamp = parseInt(a.market_slug.split('-').pop() || '0');
    const bTimestamp = parseInt(b.market_slug.split('-').pop() || '0');
    const aEndTime = (aTimestamp + 15 * 60) * 1000;
    const bEndTime = (bTimestamp + 15 * 60) * 1000;
    const aIsLive = now < aEndTime;
    const bIsLive = now < bEndTime;

    // Live markets first
    if (aIsLive && !bIsLive) return -1;
    if (!aIsLive && bIsLive) return 1;
    // Then by timestamp descending (most recent first)
    return bTimestamp - aTimestamp;
  });

  // Apply limit unless expanded
  const displayedPositions = expanded ? sortedPositions : sortedPositions.slice(0, LIMIT);
  const hasMore = sortedPositions.length > LIMIT;

  // Calculate totals (for all positions)
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

      {/* Summary Row */}
      {positions.length > 0 && (
        <div className="mb-4 flex items-center gap-6 text-sm border-b border-gray-700 pb-3">
          <div>
            <span className="text-gray-500">Markets:</span>
            <span className="text-white ml-2">{positions.length}</span>
            <span className="text-green-400 ml-1">({liveCount} live)</span>
          </div>
          <div>
            <span className="text-gray-500">Trades:</span>
            <span className="text-white ml-2">{totalTrades}</span>
          </div>
          <div>
            <span className="text-gray-500">Volume:</span>
            <span className="text-white ml-2">${totalVolume.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-gray-500">Avg Edge:</span>
            <span className={`ml-2 ${avgEdge > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(avgEdge * 100).toFixed(1)}%
            </span>
          </div>
          <div className="ml-auto">
            <span className="text-gray-500">Total P/L:</span>
            <span className={`ml-2 font-medium ${totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {sortedPositions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No positions yet
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {displayedPositions.map((position) => (
              <PositionCard
                key={`${position.wallet}:${position.market_slug}`}
                position={position}
                market={state.markets[position.market_slug]}
              />
            ))}
          </div>
          {hasMore && (
            <div className="mt-3 text-center">
              <button
                onClick={() => setExpanded(!expanded)}
                className="px-4 py-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                {expanded
                  ? 'Show less'
                  : `Show all ${sortedPositions.length} positions`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

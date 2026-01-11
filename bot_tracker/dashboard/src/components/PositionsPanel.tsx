import { useEffect, useState } from 'react';
import { useTracker } from '../context/TrackerContext';
import { WalletPosition } from '../types';

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

function PositionCard({ position }: { position: WalletPosition }) {
  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatShares = (value: number) => value.toFixed(2);
  const formatPrice = (value: number) => `$${value.toFixed(3)}`;
  const formatUSDC = (value: number) => `$${value.toFixed(2)}`;

  // Parse market time from slug
  const slugParts = position.market_slug.split('-');
  const marketTimestamp = parseInt(slugParts[slugParts.length - 1]);
  const marketEndTime = new Date((marketTimestamp + 15 * 60) * 1000);
  const isEnded = new Date() > marketEndTime;

  // Calculate financials
  const totalCost = position.up_cost + position.down_cost;
  const completeSets = position.complete_sets;
  const estimatedProfit = completeSets * position.edge;
  const profitMargin = totalCost > 0 ? (estimatedProfit / totalCost) * 100 : 0;

  // Get market type
  const marketType = position.market_slug.includes('btc') ? 'BTC' :
                     position.market_slug.includes('eth') ? 'ETH' : '???';

  return (
    <div className={`rounded-lg border border-gray-700 ${isEnded ? 'opacity-60' : ''}`}>
      {/* Header Row */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-gray-400 w-8">{marketType}</span>
          <span className="text-sm text-white">{position.wallet_name}</span>
          <span className="text-xs text-gray-500 font-mono">{position.market_slug}</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="text-gray-400">
            {isEnded ? 'Ended' : <TimeRemaining endTime={marketEndTime} />}
          </span>
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

          {/* Edge */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Edge</div>
            <div className={position.edge > 0 ? 'text-green-400' : 'text-red-400'}>
              {formatPercent(position.edge)}
            </div>
            <div className="text-xs text-gray-500">Hedge: {formatPercent(position.hedge_ratio)}</div>
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

      {/* Summary Row */}
      {positions.length > 0 && (
        <div className="mb-4 flex items-center gap-6 text-sm border-b border-gray-700 pb-3">
          <div>
            <span className="text-gray-500">Markets:</span>
            <span className="text-white ml-2">{positions.length}</span>
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
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {sortedPositions.map((position) => (
            <PositionCard
              key={`${position.wallet}:${position.market_slug}`}
              position={position}
            />
          ))}
        </div>
      )}
    </div>
  );
}

import { useState } from 'react';
import { useTracker } from '../context/TrackerContext';

const TRADES_PER_PAGE = 25;

export function LiveTradesFeed() {
  const { state, selectWallet } = useTracker();
  const [showAll, setShowAll] = useState(false);

  const formatTime = (ts: number) => {
    return new Date(ts * 1000).toLocaleTimeString();
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(3)}`;
  };

  const formatShares = (shares: number) => {
    return shares.toFixed(2);
  };

  const displayedTrades = showAll ? state.trades : state.trades.slice(0, TRADES_PER_PAGE);
  const hasMore = state.trades.length > TRADES_PER_PAGE;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Live Trades</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            Showing {displayedTrades.length} of {state.trades.length}
          </span>
          {hasMore && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              {showAll ? 'Show Less' : 'Show All'}
            </button>
          )}
        </div>
      </div>

      <div className={`overflow-x-auto ${showAll ? 'max-h-[600px] overflow-y-auto' : ''}`}>
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-800">
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left py-2 px-2">Time</th>
              <th className="text-left py-2 px-2">Side</th>
              <th className="text-left py-2 px-2">Outcome</th>
              <th className="text-right py-2 px-2">Shares</th>
              <th className="text-right py-2 px-2">Price</th>
              <th className="text-right py-2 px-2">USDC</th>
            </tr>
          </thead>
          <tbody>
            {displayedTrades.map((trade, index) => (
              <tr
                key={trade.id}
                className={`border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer ${
                  index === 0 ? 'bg-gray-700/20' : ''
                }`}
                onClick={() => selectWallet(trade.wallet)}
              >
                <td className="py-2 px-2 text-gray-300 font-mono text-xs">
                  {formatTime(trade.timestamp)}
                </td>
                <td className="py-2 px-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      trade.side === 'BUY'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}
                  >
                    {trade.side}
                  </span>
                </td>
                <td className="py-2 px-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      trade.outcome === 'Up'
                        ? 'bg-blue-500/20 text-blue-400'
                        : trade.outcome === 'Down'
                        ? 'bg-orange-500/20 text-orange-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}
                  >
                    {trade.outcome}
                  </span>
                </td>
                <td className="py-2 px-2 text-right text-gray-300 font-mono">
                  {formatShares(trade.shares)}
                </td>
                <td className="py-2 px-2 text-right text-gray-300 font-mono">
                  {formatPrice(trade.price)}
                </td>
                <td className="py-2 px-2 text-right text-green-400 font-mono">
                  ${trade.usdc.toFixed(2)}
                </td>
              </tr>
            ))}
            {state.trades.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-500">
                  Waiting for trades...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Quick Stats Bar */}
      {state.trades.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-700 flex items-center gap-6 text-xs">
          <div className="text-gray-400">
            Last trade: <span className="text-white font-mono">{formatTime(state.trades[0]?.timestamp)}</span>
          </div>
          <div className="text-gray-400">
            Avg price: <span className="text-white font-mono">
              ${(state.trades.reduce((sum, t) => sum + t.price, 0) / state.trades.length).toFixed(3)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

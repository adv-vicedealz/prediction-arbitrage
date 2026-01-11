import { useState, useEffect, useRef, useMemo } from 'react';
import { useTracker } from '../context/TrackerContext';
import { getAssetType } from '../utils/formatMarket';

const TRADES_PER_PAGE = 100;

type AssetFilter = 'all' | 'btc' | 'eth';

// Parse market slug to get readable date/time info
function parseMarketSlug(slug: string): { asset: string; dateTime: string; fullId: string } {
  if (!slug) return { asset: '???', dateTime: '', fullId: '' };

  const parts = slug.split('-');
  const timestamp = parseInt(parts[parts.length - 1]);
  const asset = getAssetType(slug);

  if (!isNaN(timestamp) && timestamp > 1000000000) {
    const date = new Date(timestamp * 1000);
    const dateStr = date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      timeZone: 'America/New_York'
    });
    const timeStr = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/New_York'
    });
    return {
      asset,
      dateTime: `${dateStr} ${timeStr} ET`,
      fullId: slug
    };
  }

  return { asset, dateTime: slug, fullId: slug };
}

export function LiveTradesFeed() {
  const { state, selectWallet } = useTracker();
  const [currentPage, setCurrentPage] = useState(1);
  const [assetFilter, setAssetFilter] = useState<AssetFilter>('all');
  const [selectedMarket, setSelectedMarket] = useState<string>('all');
  const prevTradesLengthRef = useRef(state.trades.length);

  // Get unique markets from trades, sorted by timestamp (newest first)
  const uniqueMarkets = useMemo(() => {
    const marketMap = new Map<string, number>();
    state.trades.forEach(t => {
      if (t.market_slug && !marketMap.has(t.market_slug)) {
        // Extract timestamp from slug
        const parts = t.market_slug.split('-');
        const ts = parseInt(parts[parts.length - 1]) || 0;
        marketMap.set(t.market_slug, ts);
      }
    });
    // Sort by timestamp descending
    return [...marketMap.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([slug]) => slug);
  }, [state.trades]);

  // Reset to page 1 when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [assetFilter, selectedMarket]);

  // Reset to page 1 when new trades arrive (length increases)
  useEffect(() => {
    if (state.trades.length > prevTradesLengthRef.current && currentPage === 1) {
      // Already on page 1, no action needed
    } else if (state.trades.length > prevTradesLengthRef.current) {
      // New trades arrived and we're not on page 1 - optionally reset
      // For now, stay on current page to not disrupt viewing
    }
    prevTradesLengthRef.current = state.trades.length;
  }, [state.trades.length, currentPage]);

  // Filter trades by asset type and specific market
  const filteredTrades = useMemo(() => {
    return state.trades.filter(t => {
      // Asset filter
      if (assetFilter !== 'all' && !t.market_slug?.toLowerCase().includes(assetFilter)) {
        return false;
      }
      // Specific market filter
      if (selectedMarket !== 'all' && t.market_slug !== selectedMarket) {
        return false;
      }
      return true;
    });
  }, [state.trades, assetFilter, selectedMarket]);

  const formatTimeET = (ts: number) => {
    return new Date(ts * 1000).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'America/New_York'
    });
  };

  const formatTimeUTC1 = (ts: number) => {
    return new Date(ts * 1000).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'Europe/Paris'
    });
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(3)}`;
  };

  const formatShares = (shares: number) => {
    return shares.toFixed(2);
  };

  // Pagination (based on filtered trades)
  const totalPages = Math.max(1, Math.ceil(filteredTrades.length / TRADES_PER_PAGE));
  const startIndex = (currentPage - 1) * TRADES_PER_PAGE;
  const endIndex = Math.min(startIndex + TRADES_PER_PAGE, filteredTrades.length);
  const displayedTrades = filteredTrades.slice(startIndex, endIndex);

  // Ensure current page is valid
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(Math.max(1, totalPages));
    }
  }, [currentPage, totalPages]);

  // Download CSV for last 20 markets
  const downloadCSV = () => {
    if (state.trades.length === 0) return;

    // Get unique market slugs (in order of appearance) and take last 20
    const recentMarkets = [...new Set(state.trades.map(t => t.market_slug))].slice(0, 20);

    // Filter trades to only those markets
    const filteredTrades = state.trades.filter(t => recentMarkets.includes(t.market_slug));

    // Build CSV with proper escaping
    const headers = ['Time', 'Market', 'Side', 'Outcome', 'Shares', 'Price', 'USDC', 'Wallet', 'TxHash'];
    const rows = filteredTrades.map(t => [
      new Date(t.timestamp * 1000).toISOString(),
      t.market_slug,
      t.side,
      t.outcome,
      t.shares.toFixed(4),
      t.price.toFixed(4),
      t.usdc.toFixed(2),
      t.wallet_name,
      t.tx_hash
    ]);

    const csv = [headers, ...rows].map(row =>
      row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ).join('\n');

    // Download file
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex flex-col gap-3 mb-4">
        {/* Header Row */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Trades</h2>
          <div className="flex items-center gap-3">
            {/* Asset Type Filter */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setAssetFilter('all'); setSelectedMarket('all'); }}
                className={`px-2 py-1 text-xs rounded ${
                  assetFilter === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                All
              </button>
              <button
                onClick={() => { setAssetFilter('btc'); setSelectedMarket('all'); }}
                className={`px-2 py-1 text-xs rounded ${
                  assetFilter === 'btc'
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                BTC
              </button>
              <button
                onClick={() => { setAssetFilter('eth'); setSelectedMarket('all'); }}
                className={`px-2 py-1 text-xs rounded ${
                  assetFilter === 'eth'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                ETH
              </button>
            </div>

            {/* Count */}
            <span className="text-sm text-gray-400">
              {filteredTrades.length > 0
                ? `${startIndex + 1}-${endIndex} of ${filteredTrades.length}`
                : '0 trades'}
            </span>

            {/* CSV Download */}
            {state.trades.length > 0 && (
              <button
                onClick={downloadCSV}
                className="px-2 py-1 text-xs rounded bg-gray-700 text-white hover:bg-gray-600 flex items-center gap-1"
                title="Download CSV (last 20 markets)"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                CSV
              </button>
            )}
          </div>
        </div>

        {/* Market Selector Row */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-400">Market:</label>
          <select
            value={selectedMarket}
            onChange={(e) => setSelectedMarket(e.target.value)}
            className="bg-gray-700 text-white text-sm rounded px-3 py-1.5 border border-gray-600 focus:border-blue-500 focus:outline-none max-w-md"
          >
            <option value="all">All Markets ({uniqueMarkets.length})</option>
            {uniqueMarkets
              .filter(slug => assetFilter === 'all' || slug.toLowerCase().includes(assetFilter))
              .map(slug => {
                const parsed = parseMarketSlug(slug);
                const tradeCount = state.trades.filter(t => t.market_slug === slug).length;
                return (
                  <option key={slug} value={slug}>
                    {parsed.asset} {parsed.dateTime} ({tradeCount} trades)
                  </option>
                );
              })}
          </select>

          {/* Pagination */}
          <div className="flex items-center gap-2 ml-auto">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => p - 1)}
              className={`px-2 py-1 text-xs rounded ${
                currentPage === 1
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              Prev
            </button>
            <span className="text-sm text-gray-300">
              {currentPage} / {totalPages}
            </span>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
              className={`px-2 py-1 text-xs rounded ${
                currentPage === totalPages
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-700 text-white hover:bg-gray-600'
              }`}
            >
              Next
            </button>
          </div>
        </div>

        {/* Selected Market Info */}
        {selectedMarket !== 'all' && (
          <div className="text-xs text-gray-500 font-mono bg-gray-900 px-2 py-1 rounded">
            ID: {selectedMarket}
          </div>
        )}
      </div>

      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-800">
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left py-2 px-2">Time (ET)</th>
              <th className="text-left py-2 px-2">UTC+1</th>
              <th className="text-left py-2 px-2">Market</th>
              <th className="text-left py-2 px-2">Side</th>
              <th className="text-left py-2 px-2">Outcome</th>
              <th className="text-right py-2 px-2">Shares</th>
              <th className="text-right py-2 px-2">Price</th>
              <th className="text-right py-2 px-2">USDC</th>
            </tr>
          </thead>
          <tbody>
            {displayedTrades.map((trade, index) => {
              const marketInfo = parseMarketSlug(trade.market_slug);
              return (
                <tr
                  key={trade.id}
                  className={`border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer ${
                    index === 0 ? 'bg-gray-700/20' : ''
                  }`}
                  onClick={() => selectWallet(trade.wallet)}
                >
                  <td className="py-2 px-2 text-gray-300 font-mono text-xs">
                    {formatTimeET(trade.timestamp)}
                  </td>
                  <td className="py-2 px-2 text-yellow-400 font-mono text-xs">
                    {formatTimeUTC1(trade.timestamp)}
                  </td>
                  <td className="py-2 px-2" title={trade.market_slug}>
                    <div className="flex flex-col">
                      <span className={`text-xs font-medium ${
                        marketInfo.asset === 'BTC' ? 'text-orange-400' : 'text-purple-400'
                      }`}>
                        {marketInfo.asset} {marketInfo.dateTime}
                      </span>
                    </div>
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
              );
            })}
            {state.trades.length === 0 && (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-500">
                  Waiting for resolved markets...
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
            Last trade: <span className="text-white font-mono">{formatTimeET(state.trades[0]?.timestamp)}</span>
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

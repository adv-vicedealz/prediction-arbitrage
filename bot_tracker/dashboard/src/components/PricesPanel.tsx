import { useState, useEffect, useCallback } from 'react';
import { PricePoint } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

export function PricesPanel() {
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPrices = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/prices?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setPrices(data);
      }
    } catch (e) {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 5000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  const formatTime = (ts: number) => {
    return new Date(ts * 1000).toLocaleTimeString();
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(3)}`;
  };

  const formatMarketSlug = (slug: string) => {
    if (slug.length > 30) {
      return slug.substring(0, 30) + '...';
    }
    return slug;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Live Prices</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            {prices.length} price updates
          </span>
          <button
            onClick={fetchPrices}
            className="text-sm text-purple-400 hover:text-purple-300"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-800">
            <tr className="text-gray-400 border-b border-gray-700">
              <th className="text-left py-2 px-2">Time</th>
              <th className="text-left py-2 px-2">Market</th>
              <th className="text-left py-2 px-2">Outcome</th>
              <th className="text-right py-2 px-2">Price</th>
              <th className="text-right py-2 px-2">Bid</th>
              <th className="text-right py-2 px-2">Ask</th>
            </tr>
          </thead>
          <tbody>
            {prices.map((price, index) => (
              <tr
                key={`${price.timestamp}-${price.market_slug}-${price.outcome}-${index}`}
                className={`border-b border-gray-700/50 hover:bg-gray-700/30 ${
                  index === 0 ? 'bg-gray-700/20' : ''
                }`}
              >
                <td className="py-2 px-2 text-gray-300 font-mono text-xs">
                  {formatTime(price.timestamp)}
                </td>
                <td className="py-2 px-2 text-gray-300 text-xs" title={price.market_slug}>
                  {formatMarketSlug(price.market_slug)}
                </td>
                <td className="py-2 px-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      price.outcome === 'Up'
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'bg-orange-500/20 text-orange-400'
                    }`}
                  >
                    {price.outcome}
                  </span>
                </td>
                <td className="py-2 px-2 text-right text-purple-400 font-mono">
                  {formatPrice(price.price)}
                </td>
                <td className="py-2 px-2 text-right text-green-400 font-mono">
                  {formatPrice(price.best_bid)}
                </td>
                <td className="py-2 px-2 text-right text-red-400 font-mono">
                  {formatPrice(price.best_ask)}
                </td>
              </tr>
            ))}
            {loading && prices.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-500">
                  Loading prices...
                </td>
              </tr>
            )}
            {!loading && prices.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-500">
                  No price data yet. Prices will appear when markets are being tracked.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Quick Stats Bar */}
      {prices.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-700 flex items-center gap-6 text-xs">
          <div className="text-gray-400">
            Last update: <span className="text-white font-mono">{formatTime(prices[0]?.timestamp)}</span>
          </div>
          <div className="text-gray-400">
            Markets: <span className="text-white font-mono">
              {new Set(prices.map(p => p.market_slug)).size}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

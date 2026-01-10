import { useEffect, useState } from 'react';
import { useTracker } from '../context/TrackerContext';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface MarketInfo {
  slug: string;
  question: string;
  trades_captured: number;
  first_trade_time: string;
  last_trade_time: string;
  tracking_duration_mins: number;
  market_end_time?: string;
  resolved?: boolean;
  winning_outcome?: string;
  tracking_coverage?: string;
  coverage_percent?: number;
}

interface TrackingInfo {
  tracking_started: string;
  uptime_seconds: number;
  total_trades_captured: number;
  markets: MarketInfo[];
}

export function WalletsSidebar() {
  const { state, selectWallet, refreshData } = useTracker();
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

  const getWalletStats = (address: string) => {
    const walletPositions = Object.values(state.positions).filter(
      (p) => p.wallet.toLowerCase() === address.toLowerCase()
    );
    const trades = state.trades.filter(
      (t) => t.wallet.toLowerCase() === address.toLowerCase()
    );

    return {
      positions: walletPositions.length,
      trades: trades.length,
    };
  };

  // Calculate trade stats
  const upTrades = state.trades.filter(t => t.outcome === 'Up').length;
  const downTrades = state.trades.filter(t => t.outcome === 'Down').length;
  const totalShares = state.trades.reduce((sum, t) => sum + t.shares, 0);
  const totalValue = state.trades.reduce((sum, t) => sum + t.usdc, 0);

  return (
    <div className="space-y-4">
      {/* Config Status */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-white mb-3">Tracker Status</h2>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">Status</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              state.config?.running
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
            }`}>
              {state.config?.running ? 'Running' : 'Stopped'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">WebSocket</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              state.isConnected
                ? 'bg-green-500/20 text-green-400'
                : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {state.isConnected ? 'Connected' : 'Polling'}
            </span>
          </div>

          <div>
            <span className="text-gray-400 text-sm block mb-1">Market Filter</span>
            <code className="text-xs text-blue-400 bg-gray-700 px-2 py-1 rounded block">
              {state.config?.market_filter || 'None'}
            </code>
          </div>

          <button
            onClick={refreshData}
            disabled={state.isLoading}
            className={`w-full mt-2 px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center justify-center gap-2 ${
              state.isLoading
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            }`}
          >
            {state.isLoading && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {state.isLoading ? 'Loading...' : 'Refresh Data'}
          </button>
        </div>
      </div>

      {/* Tracked Wallet */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-white mb-3">Tracked Wallet</h2>

        <div className="space-y-2">
          {state.wallets.map((wallet) => {
            const stats = getWalletStats(wallet.address);
            const isSelected = state.selectedWallet?.toLowerCase() === wallet.address.toLowerCase();

            return (
              <button
                key={wallet.address}
                onClick={() => selectWallet(isSelected ? null : wallet.address)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  isSelected
                    ? 'bg-blue-600/30 border border-blue-500'
                    : 'bg-gray-700/50 hover:bg-gray-700 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      stats.trades > 0 ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
                    }`}
                  />
                  <span className="text-white font-medium truncate">{wallet.name}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1 font-mono">
                  {wallet.address.slice(0, 10)}...{wallet.address.slice(-6)}
                </div>
                <div className="flex gap-3 mt-2 text-xs text-gray-400">
                  <span>{stats.positions} positions</span>
                  <span>{stats.trades} trades</span>
                </div>
              </button>
            );
          })}

          {state.wallets.length === 0 && (
            <div className="text-gray-500 text-sm text-center py-4">
              No wallet configured
            </div>
          )}
        </div>
      </div>

      {/* Live Stats */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-white mb-3">Session Stats</h2>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Total Trades</span>
            <span className="text-white font-medium">{state.trades.length}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Up Trades</span>
            <span className="text-blue-400">{upTrades}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Down Trades</span>
            <span className="text-orange-400">{downTrades}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Total Shares</span>
            <span className="text-white">{totalShares.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Total USDC</span>
            <span className="text-green-400">${totalValue.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Market Coverage */}
      {trackingInfo && trackingInfo.markets.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Market Coverage</h2>

          <div className="text-xs text-gray-400 mb-3">
            Tracking since: {new Date(trackingInfo.tracking_started).toLocaleTimeString()}
          </div>

          <div className="space-y-3">
            {trackingInfo.markets.map((market) => (
              <div key={market.slug} className="border border-gray-700 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1 truncate" title={market.question}>
                  {market.question.replace('Bitcoin Up or Down - ', 'BTC ')}
                </div>

                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{market.trades_captured} trades</span>
                  {market.coverage_percent !== undefined && (
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      market.coverage_percent >= 80
                        ? 'bg-green-500/20 text-green-400'
                        : market.coverage_percent >= 40
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {market.coverage_percent.toFixed(0)}% covered
                    </span>
                  )}
                </div>

                {/* Coverage bar */}
                {market.coverage_percent !== undefined && (
                  <div className="w-full bg-gray-700 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${
                        market.coverage_percent >= 80
                          ? 'bg-green-500'
                          : market.coverage_percent >= 40
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(100, market.coverage_percent)}%` }}
                    />
                  </div>
                )}

                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>{market.tracking_duration_mins.toFixed(1)} min tracked</span>
                  {market.resolved && (
                    <span className="text-purple-400">
                      Won: {market.winning_outcome}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

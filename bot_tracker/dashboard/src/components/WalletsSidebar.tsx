import { useEffect, useState } from 'react';
import { useTracker } from '../context/TrackerContext';

export function WalletsSidebar() {
  const { state, selectWallet, refreshData } = useTracker();

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
        <h2 className="text-lg font-semibold text-white mb-3">Displayed Data</h2>

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

      {/* Live Markets */}
      <LiveMarketsCard />
    </div>
  );
}

// Live Markets Card Component
function LiveMarketsCard() {
  const [currentTime, setCurrentTime] = useState(Date.now());

  // Update every second for countdown
  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Calculate current 15-min slot
  const nowSec = Math.floor(currentTime / 1000);
  const interval = 15 * 60; // 15 minutes
  const currentSlotStart = Math.floor(nowSec / interval) * interval;
  const currentSlotEnd = currentSlotStart + interval;
  const timeLeftSec = currentSlotEnd - nowSec;

  // Format time remaining
  const mins = Math.floor(timeLeftSec / 60);
  const secs = timeLeftSec % 60;
  const countdown = `${mins}:${secs.toString().padStart(2, '0')}`;

  // Format slot times in ET and UTC+1
  const slotStartET = new Date(currentSlotStart * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'America/New_York'
  });
  const slotEndET = new Date(currentSlotEnd * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'America/New_York'
  });
  const slotStartUTC1 = new Date(currentSlotStart * 1000).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Europe/Paris'
  });
  const slotEndUTC1 = new Date(currentSlotEnd * 1000).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Europe/Paris'
  });

  // Market slugs
  const btcSlug = `btc-updown-15m-${currentSlotStart}`;
  const ethSlug = `eth-updown-15m-${currentSlotStart}`;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">Live Markets</h2>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-green-400 font-mono text-lg">{countdown}</span>
        </div>
      </div>

      <div className="text-xs text-gray-400 mb-4">
        {slotStartET}-{slotEndET} ET / {slotStartUTC1}-{slotEndUTC1} UTC+1
      </div>

      <div className="space-y-2">
        {/* BTC Market */}
        <a
          href={`https://polymarket.com/event/${btcSlug}/${btcSlug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="block border border-gray-700 rounded-lg p-3 hover:border-orange-500/50 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-orange-400 font-bold">BTC</span>
              <span className="text-gray-300 text-sm">15min Up/Down</span>
            </div>
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </div>
        </a>

        {/* ETH Market */}
        <a
          href={`https://polymarket.com/event/${ethSlug}/${ethSlug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="block border border-gray-700 rounded-lg p-3 hover:border-purple-500/50 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-purple-400 font-bold">ETH</span>
              <span className="text-gray-300 text-sm">15min Up/Down</span>
            </div>
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </div>
        </a>
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-green-500 h-1.5 rounded-full transition-all duration-1000"
            style={{ width: `${((interval - timeLeftSec) / interval) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}

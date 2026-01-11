import { useState } from 'react';
import { useTracker } from '../context/TrackerContext';

export function Header() {
  const { state, toggleTracker, updateWallet } = useTracker();
  const [walletInput, setWalletInput] = useState('');
  const [walletName, setWalletName] = useState('');
  const [showWalletForm, setShowWalletForm] = useState(false);

  const handleWalletSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (walletInput.trim()) {
      updateWallet(walletInput.trim(), walletName.trim() || 'CustomWallet');
      setWalletInput('');
      setWalletName('');
      setShowWalletForm(false);
    }
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-white">Bot Trading Tracker</h1>

          {/* Connection Status */}
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
              state.isConnected
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                state.isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              }`}
            />
            {state.isConnected ? 'Connected' : 'Disconnected'}
          </div>

          {/* Price Stream Status */}
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
              state.priceStreamStatus?.connected
                ? 'bg-purple-500/20 text-purple-400'
                : 'bg-red-500/20 text-red-400'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                state.priceStreamStatus?.connected ? 'bg-purple-400 animate-pulse' : 'bg-red-400'
              }`}
            />
            Prices: {state.priceStreamStatus?.connected ? 'Live' : 'Offline'}
          </div>

          {/* Tracker Toggle */}
          <button
            onClick={toggleTracker}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              state.config?.running
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                state.config?.running ? 'bg-red-400' : 'bg-green-400'
              }`}
            />
            {state.config?.running ? 'Stop Tracker' : 'Start Tracker'}
          </button>
        </div>

        <div className="flex items-center gap-6">
          {/* Current Wallet */}
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Tracking:</span>
            <span className="text-white font-mono text-sm">
              {state.config?.wallet?.name || 'None'}
            </span>
            <button
              onClick={() => setShowWalletForm(!showWalletForm)}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              {showWalletForm ? 'Cancel' : 'Change'}
            </button>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="text-gray-400">
              <span className="text-white font-medium">{state.trades.length}</span> trades
            </div>
            <div className="text-gray-400">
              Market: <span className="text-white font-mono">{state.config?.market_filter || 'All'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Wallet Change Form */}
      {showWalletForm && (
        <form onSubmit={handleWalletSubmit} className="mt-4 flex items-center gap-3">
          <input
            type="text"
            value={walletInput}
            onChange={(e) => setWalletInput(e.target.value)}
            placeholder="Wallet address (0x...)"
            className="flex-1 max-w-md bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white text-sm font-mono placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <input
            type="text"
            value={walletName}
            onChange={(e) => setWalletName(e.target.value)}
            placeholder="Wallet name (optional)"
            className="w-48 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Update Wallet
          </button>
        </form>
      )}
    </header>
  );
}

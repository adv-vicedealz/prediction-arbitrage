import { useState } from 'react';
import { TrackerProvider, useTracker } from './context/TrackerContext';
import { Header } from './components/Header';
import { WalletsSidebar } from './components/WalletsSidebar';
import { LiveTradesFeed } from './components/LiveTradesFeed';
import { PositionsPanel } from './components/PositionsPanel';
import { PricesPanel } from './components/PricesPanel';
import { TopTradersPanel } from './components/TopTradersPanel';
import { AnalyticsPage } from './components/analytics/AnalyticsPage';
import { DeepAnalysisPage } from './components/deep-analysis';

type TabType = 'trades' | 'positions' | 'prices' | 'traders' | 'analytics' | 'deep-analysis';

function LoadingOverlay() {
  const { state } = useTracker();

  if (!state.isLoading) return null;

  return (
    <div className="fixed inset-0 bg-gray-900/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-white text-lg">Loading data...</p>
      </div>
    </div>
  );
}

function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('trades');

  return (
    <div className="min-h-screen bg-gray-900">
      <LoadingOverlay />
      <Header />

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-72 p-4 border-r border-gray-800 min-h-[calc(100vh-73px)]">
          <WalletsSidebar />
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-4">
          {/* Tab Navigation */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setActiveTab('trades')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'trades'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Trades
            </button>
            <button
              onClick={() => setActiveTab('positions')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'positions'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Positions
            </button>
            <button
              onClick={() => setActiveTab('prices')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'prices'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Prices
            </button>
            <button
              onClick={() => setActiveTab('traders')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'traders'
                  ? 'bg-yellow-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Top Traders
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'analytics'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Analytics
            </button>
            <button
              onClick={() => setActiveTab('deep-analysis')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'deep-analysis'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Deep Analysis
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'trades' && <LiveTradesFeed />}
          {activeTab === 'positions' && <PositionsPanel />}
          {activeTab === 'prices' && <PricesPanel />}
          {activeTab === 'traders' && <TopTradersPanel />}
          {activeTab === 'analytics' && <AnalyticsPage />}
          {activeTab === 'deep-analysis' && <DeepAnalysisPage />}
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <TrackerProvider>
      <Dashboard />
    </TrackerProvider>
  );
}

export default App;

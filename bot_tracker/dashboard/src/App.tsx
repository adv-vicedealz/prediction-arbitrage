import { useState } from 'react';
import { TrackerProvider } from './context/TrackerContext';
import { Header } from './components/Header';
import { WalletsSidebar } from './components/WalletsSidebar';
import { LiveTradesFeed } from './components/LiveTradesFeed';
import { PositionsPanel } from './components/PositionsPanel';
import { PricesPanel } from './components/PricesPanel';

type TabType = 'trades' | 'positions' | 'prices';

function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('trades');

  return (
    <div className="min-h-screen bg-gray-900">
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
          </div>

          {/* Tab Content */}
          {activeTab === 'trades' && <LiveTradesFeed />}
          {activeTab === 'positions' && <PositionsPanel />}
          {activeTab === 'prices' && <PricesPanel />}
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

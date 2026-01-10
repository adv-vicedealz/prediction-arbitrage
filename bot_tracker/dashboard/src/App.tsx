import { TrackerProvider } from './context/TrackerContext';
import { Header } from './components/Header';
import { WalletsSidebar } from './components/WalletsSidebar';
import { LiveTradesFeed } from './components/LiveTradesFeed';
import { PositionsPanel } from './components/PositionsPanel';

function Dashboard() {
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Live Trades - Full width on small, left column on large */}
            <div className="lg:col-span-1">
              <LiveTradesFeed />
            </div>

            {/* Positions - Right column on large */}
            <div className="lg:col-span-1">
              <PositionsPanel />
            </div>
          </div>
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

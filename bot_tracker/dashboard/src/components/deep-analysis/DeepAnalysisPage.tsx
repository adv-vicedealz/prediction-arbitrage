import { useState, useEffect } from 'react';
import { ExecutionQualityChart } from './ExecutionQualityChart';
import { MarketOverlayChart } from './MarketOverlayChart';
import { PositionEvolutionChart } from './PositionEvolutionChart';
import { LossPatternAnalysis } from './LossPatternAnalysis';
import { RiskMetricsCard } from './RiskMetricsCard';
import { TradingIntensityChart } from './TradingIntensityChart';
import type { DeepAnalysisMarket } from '../../types';

type SubTab = 'execution' | 'price-trades' | 'position' | 'intensity' | 'losses' | 'risk';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function DeepAnalysisPage() {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('execution');
  const [markets, setMarkets] = useState<DeepAnalysisMarket[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
  const [isLoadingMarkets, setIsLoadingMarkets] = useState(true);

  // Fetch available markets on mount
  useEffect(() => {
    async function fetchMarkets() {
      try {
        const res = await fetch(`${API_BASE}/api/deep-analysis/markets`);
        const data = await res.json();
        setMarkets(data);
        if (data.length > 0) {
          setSelectedMarket(data[0].slug);
        }
      } catch (err) {
        console.error('Failed to fetch markets:', err);
      } finally {
        setIsLoadingMarkets(false);
      }
    }
    fetchMarkets();
  }, []);

  const tabs: { id: SubTab; label: string; requiresMarket?: boolean }[] = [
    { id: 'execution', label: 'Execution Quality' },
    { id: 'price-trades', label: 'Price/Trades', requiresMarket: true },
    { id: 'position', label: 'Position Building', requiresMarket: true },
    { id: 'intensity', label: 'Timing Patterns' },
    { id: 'losses', label: 'Loss Analysis' },
    { id: 'risk', label: 'Risk Metrics' },
  ];

  const currentTabRequiresMarket = tabs.find(t => t.id === activeSubTab)?.requiresMarket;

  return (
    <div className="space-y-4">
      {/* Header with Market Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Deep Statistical Analysis</h2>

        {/* Market Selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Market:</label>
          <select
            value={selectedMarket || ''}
            onChange={(e) => setSelectedMarket(e.target.value || null)}
            className="bg-gray-700 text-white rounded px-3 py-1.5 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none max-w-xs"
            disabled={isLoadingMarkets}
          >
            <option value="">All Markets (Aggregate)</option>
            {markets.map((m) => (
              <option key={m.slug} value={m.slug}>
                {m.slug.replace(/-/g, ' ').slice(0, 40)}... ({m.trade_count} trades)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Sub-tabs Navigation */}
      <div className="flex gap-1 border-b border-gray-700 pb-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            className={`px-3 py-2 text-sm font-medium rounded-t transition-colors ${
              activeSubTab === tab.id
                ? 'bg-gray-700 text-white border-b-2 border-cyan-500'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            {tab.label}
            {tab.requiresMarket && (
              <span className="ml-1 text-xs text-gray-500">*</span>
            )}
          </button>
        ))}
      </div>

      {/* Warning if market-specific tab but no market selected */}
      {currentTabRequiresMarket && !selectedMarket && (
        <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 text-yellow-200">
          <p className="text-sm">
            This analysis requires selecting a specific market. Please choose a market from the dropdown above.
          </p>
        </div>
      )}

      {/* Tab Content */}
      <div className="bg-gray-800 rounded-lg p-4">
        {activeSubTab === 'execution' && (
          <ExecutionQualityChart selectedMarket={selectedMarket} />
        )}

        {activeSubTab === 'price-trades' && selectedMarket && (
          <MarketOverlayChart marketSlug={selectedMarket} />
        )}

        {activeSubTab === 'position' && selectedMarket && (
          <PositionEvolutionChart marketSlug={selectedMarket} />
        )}

        {activeSubTab === 'intensity' && (
          <TradingIntensityChart />
        )}

        {activeSubTab === 'losses' && (
          <LossPatternAnalysis />
        )}

        {activeSubTab === 'risk' && (
          <RiskMetricsCard />
        )}
      </div>

      {/* Legend */}
      <div className="text-xs text-gray-500">
        * These tabs require selecting a specific market from the dropdown
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Bar,
  ReferenceLine,
} from 'recharts';
import type { MarketOverlayData } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Props {
  marketSlug: string;
}

export function MarketOverlayChart({ marketSlug }: Props) {
  const [data, setData] = useState<MarketOverlayData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/deep-analysis/market/${encodeURIComponent(marketSlug)}/overlay`
        );
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch market overlay:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [marketSlug]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  if (!data || !data.market) {
    return (
      <div className="text-center text-gray-400 py-12">
        No data available for this market.
      </div>
    );
  }

  const startTime = data.market.start_time;

  // Use downsampled prices, filter to 0-15 minutes only
  const priceData = (data.prices_downsampled || data.prices)
    .map((p) => ({
      ...p,
      minuteIntoMarket: (p.timestamp - startTime) / 60,
    }))
    .filter((p) => p.minuteIntoMarket >= 0 && p.minuteIntoMarket <= 15);

  // Calculate trade stats from raw trades
  const buyUpTrades = data.trades.filter((t) => t.side === 'BUY' && t.outcome === 'Up');
  const buyDownTrades = data.trades.filter((t) => t.side === 'BUY' && t.outcome === 'Down');
  const sellUpTrades = data.trades.filter((t) => t.side === 'SELL' && t.outcome === 'Up');
  const sellDownTrades = data.trades.filter((t) => t.side === 'SELL' && t.outcome === 'Down');

  const totalUpBuys = buyUpTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalDownBuys = buyDownTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalUpSells = sellUpTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalDownSells = sellDownTrades.reduce((sum, t) => sum + t.shares, 0);

  // Format volume bars from 10-second buckets (sparse - only buckets with trades)
  const volumeBuckets = (data.trade_volume_by_bucket || [])
    .filter((v) => v.time_seconds >= 0 && v.time_seconds < 900) // 0-15 minutes
    .map((v) => ({
      ...v,
      minuteIntoMarket: v.time_seconds / 60,
      up_net: v.buy_up_usdc - v.sell_up_usdc,
      down_net: v.buy_down_usdc - v.sell_down_usdc,
    }));

  // Merge price data with volume data for combined charts
  // Group prices by 10-second bucket for alignment with volume
  const priceByBucket: Record<number, { up_price: number | null; down_price: number | null; up_bid: number | null; up_ask: number | null; down_bid: number | null; down_ask: number | null }> = {};
  priceData.forEach((p) => {
    const bucket = Math.floor(p.minuteIntoMarket * 6); // 6 buckets per minute (10s each)
    if (bucket >= 0 && bucket < 90) {
      if (!priceByBucket[bucket]) {
        priceByBucket[bucket] = { up_price: null, down_price: null, up_bid: null, up_ask: null, down_bid: null, down_ask: null };
      }
      // Use last price in each bucket
      if (p.up_price !== null) priceByBucket[bucket].up_price = p.up_price;
      if (p.down_price !== null) priceByBucket[bucket].down_price = p.down_price;
      if (p.up_bid !== null) priceByBucket[bucket].up_bid = p.up_bid;
      if (p.up_ask !== null) priceByBucket[bucket].up_ask = p.up_ask;
      if (p.down_bid !== null) priceByBucket[bucket].down_bid = p.down_bid;
      if (p.down_ask !== null) priceByBucket[bucket].down_ask = p.down_ask;
    }
  });

  // Create combined data for UP price + UP volume chart
  const upPriceVolumeData = volumeBuckets.map((v) => ({
    bucket: v.bucket,
    minuteIntoMarket: v.minuteIntoMarket,
    up_price: priceByBucket[v.bucket]?.up_price,
    up_bid: priceByBucket[v.bucket]?.up_bid,
    up_ask: priceByBucket[v.bucket]?.up_ask,
    buy_volume: v.buy_up_usdc,
    sell_volume: v.sell_up_usdc, // Keep positive for visual clarity
    net_volume: v.up_net,
  }));

  // Create combined data for DOWN price + DOWN volume chart
  const downPriceVolumeData = volumeBuckets.map((v) => ({
    bucket: v.bucket,
    minuteIntoMarket: v.minuteIntoMarket,
    down_price: priceByBucket[v.bucket]?.down_price,
    down_bid: priceByBucket[v.bucket]?.down_bid,
    down_ask: priceByBucket[v.bucket]?.down_ask,
    buy_volume: v.buy_down_usdc,
    sell_volume: v.sell_down_usdc, // Keep positive for visual clarity
    net_volume: v.down_net,
  }));

  return (
    <div className="space-y-4">
      {/* Market Info Header */}
      <div className="bg-gray-900 rounded-lg p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-sm font-medium text-gray-300">
              {data.market.question || data.market.slug}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Winner: <span className={data.market.winning_outcome?.toLowerCase() === 'up' ? 'text-green-400' : data.market.winning_outcome?.toLowerCase() === 'down' ? 'text-red-400' : 'text-gray-400'}>
                {data.market.winning_outcome || 'Pending'}
              </span>
            </p>
          </div>
          <div className="text-right text-xs text-gray-400">
            <p>{priceData.length} price points</p>
            <p>{data.trades.length} trades in {volumeBuckets.length} buckets</p>
          </div>
        </div>
      </div>

      {/* Trade Summary */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Buy UP</p>
          <p className="text-lg font-bold text-green-400">{totalUpBuys.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{buyUpTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Buy DOWN</p>
          <p className="text-lg font-bold text-red-400">{totalDownBuys.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{buyDownTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Sell UP</p>
          <p className="text-lg font-bold text-green-300">{totalUpSells.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{sellUpTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Sell DOWN</p>
          <p className="text-lg font-bold text-red-300">{totalDownSells.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{sellDownTrades.length} trades</p>
        </div>
      </div>

      {/* Combined UP + DOWN Price Chart */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">UP & DOWN Prices (0-15 minutes)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={priceData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="minuteIntoMarket"
              type="number"
              domain={[0, 15]}
              tickFormatter={(v) => `${Math.floor(v)}m`}
              stroke="#9CA3AF"
              fontSize={11}
              label={{ value: 'Minutes', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => v.toFixed(2)}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p className="font-medium">Time: {d.minuteIntoMarket?.toFixed(1)}m</p>
                    <p className="text-green-400">UP: {d.up_price?.toFixed(4)}</p>
                    <p className="text-red-400">DOWN: {d.down_price?.toFixed(4)}</p>
                    {d.up_price && d.down_price && (
                      <p className="text-cyan-400">Combined: {(d.up_price + d.down_price).toFixed(4)}</p>
                    )}
                  </div>
                );
              }}
            />
            <ReferenceLine y={0.5} stroke="#6B7280" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="up_price"
              stroke="#10B981"
              strokeWidth={2}
              dot={false}
              connectNulls
              name="UP"
            />
            <Line
              type="monotone"
              dataKey="down_price"
              stroke="#EF4444"
              strokeWidth={2}
              dot={false}
              connectNulls
              name="DOWN"
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-2 text-xs text-gray-200">
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-green-500"></span> UP Price</span>
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-red-500"></span> DOWN Price</span>
        </div>
      </div>

      {/* UP Price + UP Volume (Dual Axis) */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">UP Price with Trade Volume (10s buckets)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={upPriceVolumeData} margin={{ top: 10, right: 50, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="minuteIntoMarket"
              type="number"
              domain={[0, 15]}
              tickFormatter={(v) => `${Math.floor(v)}m`}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <YAxis
              yAxisId="price"
              domain={['auto', 'auto']}
              tickFormatter={(v) => v.toFixed(2)}
              stroke="#10B981"
              fontSize={11}
              label={{ value: 'Price', angle: -90, position: 'insideLeft', fill: '#10B981', fontSize: 9 }}
            />
            <YAxis
              yAxisId="volume"
              orientation="right"
              stroke="#6366F1"
              fontSize={10}
              tickFormatter={(v) => `$${v.toFixed(0)}`}
              label={{ value: 'Volume ($)', angle: 90, position: 'insideRight', fill: '#6366F1', fontSize: 9 }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p className="font-medium">{d.minuteIntoMarket?.toFixed(2)}m (bucket {d.bucket})</p>
                    <p className="text-green-400">UP Price: {d.up_price?.toFixed(4)}</p>
                    <p className="text-green-500">Buy Vol: ${d.buy_volume?.toFixed(2)}</p>
                    <p className="text-orange-400">Sell Vol: ${d.sell_volume?.toFixed(2)}</p>
                    <p className={`font-bold ${d.net_volume >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      Net: ${d.net_volume?.toFixed(2)}
                    </p>
                  </div>
                );
              }}
            />
            {/* Volume bars - buy up, sell down (not stacked) */}
            <Bar yAxisId="volume" dataKey="buy_volume" fill="#22C55E" name="Buy" barSize={8} />
            <Bar yAxisId="volume" dataKey="sell_volume" fill="#F97316" name="Sell" barSize={8} />
            {/* Price line */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="up_price"
              stroke="#10B981"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-4 mt-2 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-green-500"></span> UP Price</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500"></span> Buy Vol</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500"></span> Sell Vol</span>
        </div>
      </div>

      {/* DOWN Price + DOWN Volume (Dual Axis) */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">DOWN Price with Trade Volume (10s buckets)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={downPriceVolumeData} margin={{ top: 10, right: 50, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="minuteIntoMarket"
              type="number"
              domain={[0, 15]}
              tickFormatter={(v) => `${Math.floor(v)}m`}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <YAxis
              yAxisId="price"
              domain={['auto', 'auto']}
              tickFormatter={(v) => v.toFixed(2)}
              stroke="#EF4444"
              fontSize={11}
              label={{ value: 'Price', angle: -90, position: 'insideLeft', fill: '#EF4444', fontSize: 9 }}
            />
            <YAxis
              yAxisId="volume"
              orientation="right"
              stroke="#6366F1"
              fontSize={10}
              tickFormatter={(v) => `$${v.toFixed(0)}`}
              label={{ value: 'Volume ($)', angle: 90, position: 'insideRight', fill: '#6366F1', fontSize: 9 }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p className="font-medium">{d.minuteIntoMarket?.toFixed(2)}m (bucket {d.bucket})</p>
                    <p className="text-red-400">DOWN Price: {d.down_price?.toFixed(4)}</p>
                    <p className="text-red-500">Buy Vol: ${d.buy_volume?.toFixed(2)}</p>
                    <p className="text-orange-400">Sell Vol: ${d.sell_volume?.toFixed(2)}</p>
                    <p className={`font-bold ${d.net_volume >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      Net: ${d.net_volume?.toFixed(2)}
                    </p>
                  </div>
                );
              }}
            />
            {/* Volume bars - buy up, sell down (not stacked) */}
            <Bar yAxisId="volume" dataKey="buy_volume" fill="#DC2626" name="Buy" barSize={8} />
            <Bar yAxisId="volume" dataKey="sell_volume" fill="#F97316" name="Sell" barSize={8} />
            {/* Price line */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="down_price"
              stroke="#EF4444"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-4 mt-2 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-red-500"></span> DOWN Price</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-600"></span> Buy Vol</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500"></span> Sell Vol</span>
        </div>
      </div>

      {/* Market Efficiency (UP + DOWN = 1.0) */}
      {data.efficiency && data.efficiency.by_timestamp.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Market Efficiency (UP + DOWN = 1.0 is perfect)
            <span className={`ml-2 text-xs ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
              Avg: {data.efficiency.avg_combined.toFixed(4)}
            </span>
          </h3>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg Combined</p>
              <p className={`text-lg font-bold ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
                {data.efficiency.avg_combined.toFixed(4)}
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Deviation from 1.0</p>
              <p className={`text-lg font-bold ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
                {((data.efficiency.avg_combined - 1.0) * 100).toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Arbitrage Window</p>
              <p className={`text-lg font-bold ${data.efficiency.arbitrage_seconds > 60 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.efficiency.arbitrage_seconds}s
              </p>
              <p className="text-xs text-gray-500">when combined &lt; 0.98</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spread Analysis */}
        {data.spread_analysis && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Spread Analysis</h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-gray-800 rounded-lg p-2 text-center">
                <p className="text-xs text-gray-400">Avg</p>
                <p className="text-lg font-bold text-cyan-400">{(data.spread_analysis.avg_spread * 100).toFixed(2)}¢</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-2 text-center">
                <p className="text-xs text-gray-400">Min</p>
                <p className="text-lg font-bold text-green-400">{(data.spread_analysis.min_spread * 100).toFixed(2)}¢</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-2 text-center">
                <p className="text-xs text-gray-400">Max</p>
                <p className="text-lg font-bold text-red-400">{(data.spread_analysis.max_spread * 100).toFixed(2)}¢</p>
              </div>
            </div>
          </div>
        )}

        {/* Trade Impact Analysis */}
        {data.trade_impact && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Trade Impact (30s after)</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded-lg p-2">
                <p className="text-xs text-gray-400 mb-1">BUY Impact</p>
                <div className="flex justify-between text-sm">
                  <span className="text-green-400">UP</span>
                  <span className={data.trade_impact.buy_up_impact > 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.trade_impact.buy_up_impact > 0 ? '+' : ''}{data.trade_impact.buy_up_impact.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-red-400">DOWN</span>
                  <span className={data.trade_impact.buy_down_impact > 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.trade_impact.buy_down_impact > 0 ? '+' : ''}{data.trade_impact.buy_down_impact.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-2">
                <p className="text-xs text-gray-400 mb-1">SELL Impact</p>
                <div className="flex justify-between text-sm">
                  <span className="text-green-400">UP</span>
                  <span className={data.trade_impact.sell_up_impact > 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.trade_impact.sell_up_impact > 0 ? '+' : ''}{data.trade_impact.sell_up_impact.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-red-400">DOWN</span>
                  <span className={data.trade_impact.sell_down_impact > 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.trade_impact.sell_down_impact > 0 ? '+' : ''}{data.trade_impact.sell_down_impact.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">How to Read These Charts:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Combined Price Chart</strong>: See UP and DOWN price movements together</li>
          <li><strong>Price + Volume Charts</strong>: Volume bars show trading activity at each price level</li>
          <li><strong>Green bars</strong> = Buy volume, <strong>Light bars</strong> = Sell volume</li>
          <li><strong>Net volume</strong>: Positive = more buying, Negative = more selling</li>
        </ul>
      </div>
    </div>
  );
}

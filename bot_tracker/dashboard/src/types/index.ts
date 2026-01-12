// Types matching backend models

export interface TradeEvent {
  id: string;
  tx_hash: string;
  timestamp: number;
  wallet: string;
  wallet_name: string;
  role: 'maker' | 'taker';
  side: 'BUY' | 'SELL';
  outcome: 'Up' | 'Down' | 'Unknown';
  shares: number;
  usdc: number;
  price: number;
  fee: number;
  market_slug: string;
  market_question: string;
}

export interface WalletPosition {
  wallet: string;
  wallet_name: string;
  market_slug: string;
  up_shares: number;
  down_shares: number;
  up_cost: number;
  down_cost: number;
  up_revenue: number;
  down_revenue: number;
  complete_sets: number;
  unhedged_up: number;
  unhedged_down: number;
  avg_up_price: number;
  avg_down_price: number;
  combined_price: number;
  edge: number;
  hedge_ratio: number;
  total_trades: number;
  buy_trades: number;
  sell_trades: number;
  maker_trades: number;
  taker_trades: number;
  first_trade_ts: number;
  last_trade_ts: number;
}

export interface MarketContext {
  slug: string;
  question: string;
  condition_id: string;
  token_ids: Record<string, string>;
  outcomes: string[];
  start_date: string | null;
  end_date: string | null;
  time_to_resolution_mins: number;
  resolved: boolean;
  winning_outcome: string | null;
  up_best_bid: number | null;
  up_best_ask: number | null;
  down_best_bid: number | null;
  down_best_ask: number | null;
  combined_bid: number | null;
  spread: number | null;
}

export interface TimingPattern {
  wallet: string;
  wallet_name: string;
  market_slug: string;
  time_to_start_mins: number;
  time_to_end_mins: number;
  trading_window_mins: number;
  trades_per_minute: number;
  early_trader: boolean;
  late_closer: boolean;
}

export interface PricePattern {
  wallet: string;
  wallet_name: string;
  market_slug: string;
  avg_buy_price_up: number;
  avg_buy_price_down: number;
  avg_sell_price_up: number;
  avg_sell_price_down: number;
  combined_buy_price: number;
  spread_captured: number;
  bought_below_dollar: boolean;
  maker_percentage: number;
}

export interface HedgePattern {
  wallet: string;
  wallet_name: string;
  market_slug: string;
  hedge_ratio: number;
  up_shares: number;
  down_shares: number;
  is_fully_hedged: boolean;
  is_directional: boolean;
  dominant_side: 'UP' | 'DOWN' | 'BALANCED';
  strategy_type: 'ARBITRAGE' | 'MARKET_MAKING' | 'DIRECTIONAL' | 'MIXED' | 'UNKNOWN';
}

export interface TrackerStats {
  total_wallets: number;
  total_markets: number;
  total_positions: number;
  total_trades: number;
  connected_clients: number;
}

export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
  sequence?: number;
}

export interface Wallet {
  address: string;
  name: string;
}

export interface TrackerConfig {
  wallet: {
    address: string;
    name: string;
  };
  market_filter: string;
  buy_only: boolean;
  running: boolean;
}

export interface PriceStreamStatus {
  connected: boolean;
  running: boolean;
  subscribed_assets: number;
  assets: string[];
}

export interface PricePoint {
  timestamp: number;
  timestamp_iso: string;
  market_slug: string;
  outcome: string;
  price: number;
  best_bid: number;
  best_ask: number;
  session_id?: string;
}

// Analytics Types
export interface AnalyticsSummary {
  total_pnl: number;
  win_rate: number;
  total_markets: number;
  winning_markets: number;
  losing_markets: number;
  total_volume: number;
  effective_edge: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  avg_maker_ratio: number;
  btc_pnl: number;
  eth_pnl: number;
  btc_markets: number;
  eth_markets: number;
}

export interface MarketAnalytics {
  slug: string;
  asset: 'BTC' | 'ETH' | 'OTHER';
  question: string;
  winner: 'up' | 'down' | null;
  end_time: string | null;
  pnl: number;
  trades: number;
  volume: number;
  maker_ratio: number;
  hedge_ratio: number;
  edge: number;
  up_net: number;
  down_net: number;
  net_bias: 'UP' | 'DOWN' | 'BALANCED';
  correct_bias: boolean | null;
  avg_up_price: number;
  avg_down_price: number;
  combined_price: number;
}

export interface PnLTimelinePoint {
  timestamp: string | null;
  market_slug: string;
  asset: string;
  winner: string | null;
  pnl: number;
  cumulative_pnl: number;
}

export interface MarketTradeTimeline {
  id: string;
  timestamp: number;
  timestamp_iso: string;
  side: 'BUY' | 'SELL';
  outcome: 'Up' | 'Down';
  role: 'maker' | 'taker';
  shares: number;
  price: number;
  usdc: number;
  cumulative_up: number;
  cumulative_down: number;
  net_position: number;
  cumulative_cost: number;
  cumulative_revenue: number;
}

export interface AnalyticsState {
  summary: AnalyticsSummary | null;
  markets: MarketAnalytics[];
  pnlTimeline: PnLTimelinePoint[];
  isLoading: boolean;
}

// Deep Analysis Types
export interface DeepAnalysisMarket {
  slug: string;
  question: string;
  end_time: string | null;
  winner: 'up' | 'down' | null;
  trade_count: number;
}

export interface ExecutionQualityTrade {
  id: string;
  timestamp: number;
  market_slug: string;
  outcome: 'Up' | 'Down';
  side: 'BUY' | 'SELL';
  role: 'maker' | 'taker';
  trade_price: number;
  shares: number;
  market_bid: number | null;
  market_ask: number | null;
  market_mid: number | null;
  execution_score: number | null;
}

export interface ExecutionQualitySummary {
  total_trades: number;
  matched_trades: number;
  avg_execution_score: number;
  pct_at_bid: number;
  pct_at_ask: number;
  pct_mid: number;
  maker_avg_score: number;
  taker_avg_score: number;
}

export interface ExecutionDistributionBucket {
  bucket: string;
  start: number;
  end: number;
  count: number;
}

export interface ExecutionTimePoint {
  minute: number;
  avg_score: number;
  maker_avg: number;
  taker_avg: number;
  trade_count: number;
}

export interface ExecutionTimeAnalysis {
  by_minute: ExecutionTimePoint[];
  early_avg: number;
  late_avg: number;
  degradation_pct: number;
}

export interface ExecutionSlippage {
  total_usd: number;
  by_role: { maker: number; taker: number };
  by_outcome: { up: number; down: number };
  by_side: { buy: number; sell: number };
  avg_per_trade: number;
}

export interface ExecutionSizeAnalysis {
  correlation: number;
  by_bucket: { small: number; medium: number; large: number };
}

export interface ExecutionBreakdown {
  buy_up: number;
  buy_down: number;
  sell_up: number;
  sell_down: number;
}

export interface ExecutionQualityData {
  trades: ExecutionQualityTrade[];
  summary: ExecutionQualitySummary;
  distribution: ExecutionDistributionBucket[];
  time_analysis: ExecutionTimeAnalysis;
  slippage: ExecutionSlippage;
  size_analysis: ExecutionSizeAnalysis;
  breakdown: ExecutionBreakdown;
}

export interface PriceTimelinePoint {
  timestamp: number;
  timestamp_iso: string;
  up_price: number | null;
  up_bid: number | null;
  up_ask: number | null;
  down_price: number | null;
  down_bid: number | null;
  down_ask: number | null;
}

export interface OverlayTrade {
  id: string;
  timestamp: number;
  timestamp_iso: string;
  side: 'BUY' | 'SELL';
  outcome: 'Up' | 'Down';
  role: 'maker' | 'taker';
  shares: number;
  price: number;
  usdc: number;
}

export interface SpreadPoint {
  timestamp: number;
  up_spread: number;
  down_spread: number;
}

export interface SpreadAnalysis {
  by_timestamp: SpreadPoint[];
  avg_spread: number;
  min_spread: number;
  max_spread: number;
}

export interface EfficiencyPoint {
  timestamp: number;
  combined: number;
}

export interface MarketEfficiency {
  by_timestamp: EfficiencyPoint[];
  avg_combined: number;
  arbitrage_seconds: number;
}

export interface VolatilityMinute {
  minute: number;
  volatility: number;
  trade_count: number;
}

export interface MarketVolatility {
  by_minute: VolatilityMinute[];
  vol_trade_correlation: number;
}

export interface TradeImpact {
  buy_up_impact: number;
  sell_up_impact: number;
  buy_down_impact: number;
  sell_down_impact: number;
}

export interface TradeVolumeByMinute {
  minute: number;
  buy_up_usdc: number;
  sell_up_usdc: number;
  buy_down_usdc: number;
  sell_down_usdc: number;
  buy_up_shares: number;
  sell_up_shares: number;
  buy_down_shares: number;
  sell_down_shares: number;
  trade_count: number;
}

export interface MarketOverlayData {
  prices: PriceTimelinePoint[];
  prices_downsampled: PriceTimelinePoint[];
  trades: OverlayTrade[];
  trade_volume_by_minute: TradeVolumeByMinute[];
  market: {
    slug: string;
    question: string;
    start_time: number;
    end_time: number;
    winning_outcome: string | null;
  } | null;
  spread_analysis: SpreadAnalysis;
  efficiency: MarketEfficiency;
  volatility: MarketVolatility;
  trade_impact: TradeImpact;
}

export interface PositionEvolutionPoint {
  timestamp: number;
  timestamp_iso: string;
  up_shares: number;
  down_shares: number;
  net_position: number;
  hedge_ratio: number;
  total_cost: number;
  total_revenue: number;
  // NEW: Cost basis fields
  up_avg_cost: number;
  down_avg_cost: number;
  combined_cost: number;
  // NEW: P&L fields
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  // NEW: Entry quality for this trade
  entry_edge: number;
}

export interface PositionSummary {
  final_up_shares: number;
  final_down_shares: number;
  final_up_vwap: number;
  final_down_vwap: number;
  final_combined_cost: number;
  total_cost: number;
  total_revenue: number;
  total_realized_pnl: number;
  final_pnl: number | null;
  winning_outcome: string | null;
}

export interface EntryQuality {
  avg_entry_edge: number;
  pct_positive_edge: number;
  total_edge_value: number;
  trade_count: number;
}

export interface PositionSizing {
  buy_sizes: number[];
  buy_count: number;
  avg_size: number;
  stddev: number;
  coefficient_variation: number;
  largest_pct: number;
  pattern: 'DCA' | 'Variable' | 'Concentrated';
}

export interface PricePositionTimelinePoint {
  timestamp: number;
  timestamp_iso: string;
  up_shares: number;
  down_shares: number;
  up_price: number | null;
  down_price: number | null;
}

export interface PriceCorrelation {
  up_shares_vs_up_price: number;
  down_shares_vs_down_price: number;
  pct_bought_below_avg_up: number;
  pct_bought_below_avg_down: number;
  pct_sold_above_avg_up: number;
  pct_sold_above_avg_down: number;
  avg_up_price: number;
  avg_down_price: number;
  timeline: PricePositionTimelinePoint[];
}

export interface PositionEvolutionData {
  points: PositionEvolutionPoint[];
  summary: PositionSummary;
  entry_quality: EntryQuality;
  sizing: PositionSizing;
  price_correlation: PriceCorrelation;
}

export interface TradingIntensityMinute {
  minute: number;
  trade_count: number;
  volume: number;
}

export interface TradingIntensityData {
  by_minute: TradingIntensityMinute[];
  by_phase: {
    early: number;
    middle: number;
    late: number;
  };
  total_trades: number;
}

export interface LossPatternMetrics {
  avg_hedge_ratio: number;
  avg_maker_ratio: number;
  avg_combined_price: number;
  avg_trades: number;
  avg_volume: number;
  avg_edge: number;
  pct_correct_bias: number;
  pct_balanced: number;
  avg_pnl: number;
}

export interface LossPatternComparison {
  metric: string;
  winners: number;
  losers: number;
  difference: number | null;
}

export interface BoxPlotData {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
}

export interface LossPatternDistributions {
  hedge_ratio: { winners: BoxPlotData; losers: BoxPlotData };
  maker_ratio: { winners: BoxPlotData; losers: BoxPlotData };
  combined_price: { winners: BoxPlotData; losers: BoxPlotData };
  edge: { winners: BoxPlotData; losers: BoxPlotData };
}

export interface LossPatternData {
  winners: { count: number; metrics: LossPatternMetrics };
  losers: { count: number; metrics: LossPatternMetrics };
  comparison: LossPatternComparison[];
  distributions: LossPatternDistributions;
  all_markets: MarketAnalytics[];
}

export interface RiskMetrics {
  sharpe: number;
  max_drawdown: number;
  calmar: number;
  var_5pct: number;
  win_streak: number;
  loss_streak: number;
  current_streak: number;
  current_streak_type: 'win' | 'loss' | null;
  win_rate: number;
  win_rate_ci_low: number;
  win_rate_ci_high: number;
  total_pnl: number;
  total_markets: number;
  pnl_std: number;
  mean_pnl: number;
}

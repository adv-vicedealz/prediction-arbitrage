import React, { createContext, useContext, useReducer, useCallback, useEffect, useMemo, useRef } from 'react';
import { TradeEvent, WalletPosition, MarketContext, TrackerStats, Wallet, TrackerConfig, PriceStreamStatus, PricePoint } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';

// Use relative URL when served from same origin, or fallback to localhost for dev
const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8080' : '');
const WS_URL = import.meta.env.VITE_WS_URL || (window.location.hostname === 'localhost'
  ? 'ws://localhost:8080/ws'
  : `wss://${window.location.host}/ws`);

interface State {
  trades: TradeEvent[];
  positions: Record<string, WalletPosition>;
  markets: Record<string, MarketContext>;
  stats: TrackerStats | null;
  wallets: Wallet[];
  selectedWallet: string | null;
  isConnected: boolean;
  config: TrackerConfig | null;
  isLoading: boolean;
  priceStreamStatus: PriceStreamStatus | null;
  prices: PricePoint[];
  pricesByMarket: Record<string, number>;
}

type Action =
  | { type: 'ADD_TRADE'; payload: TradeEvent }
  | { type: 'UPDATE_POSITION'; payload: WalletPosition }
  | { type: 'UPDATE_MARKET'; payload: MarketContext }
  | { type: 'UPDATE_STATS'; payload: TrackerStats }
  | { type: 'SET_WALLETS'; payload: Wallet[] }
  | { type: 'SELECT_WALLET'; payload: string | null }
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'SET_TRADES'; payload: TradeEvent[] }
  | { type: 'SET_POSITIONS'; payload: WalletPosition[] }
  | { type: 'SET_CONFIG'; payload: TrackerConfig }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_PRICE_STREAM_STATUS'; payload: PriceStreamStatus }
  | { type: 'SET_PRICES'; payload: PricePoint[] }
  | { type: 'SET_PRICES_BY_MARKET'; payload: Record<string, number> };

const initialState: State = {
  trades: [],
  positions: {},
  markets: {},
  stats: null,
  wallets: [],
  selectedWallet: null,
  isConnected: false,
  config: null,
  isLoading: false,
  priceStreamStatus: null,
  prices: [],
  pricesByMarket: {},
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'ADD_TRADE':
      return {
        ...state,
        trades: [action.payload, ...state.trades].slice(0, 2000),
      };
    case 'UPDATE_POSITION':
      return {
        ...state,
        positions: {
          ...state.positions,
          [`${action.payload.wallet}:${action.payload.market_slug}`]: action.payload,
        },
      };
    case 'UPDATE_MARKET':
      return {
        ...state,
        markets: {
          ...state.markets,
          [action.payload.slug]: action.payload,
        },
      };
    case 'UPDATE_STATS':
      return { ...state, stats: action.payload };
    case 'SET_WALLETS':
      return { ...state, wallets: action.payload };
    case 'SELECT_WALLET':
      return { ...state, selectedWallet: action.payload };
    case 'SET_CONNECTED':
      return { ...state, isConnected: action.payload };
    case 'SET_TRADES':
      return { ...state, trades: action.payload };
    case 'SET_POSITIONS':
      return {
        ...state,
        positions: action.payload.reduce((acc, pos) => {
          acc[`${pos.wallet}:${pos.market_slug}`] = pos;
          return acc;
        }, {} as Record<string, WalletPosition>),
      };
    case 'SET_CONFIG':
      return { ...state, config: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_PRICE_STREAM_STATUS':
      return { ...state, priceStreamStatus: action.payload };
    case 'SET_PRICES':
      return { ...state, prices: action.payload };
    case 'SET_PRICES_BY_MARKET':
      return { ...state, pricesByMarket: action.payload };
    default:
      return state;
  }
}

const TrackerContext = createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
  selectWallet: (wallet: string | null) => void;
  toggleTracker: () => Promise<void>;
  updateWallet: (address: string, name: string) => Promise<void>;
  refreshData: () => Promise<void>;
} | null>(null);

export function TrackerProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const lastTradeIdRef = useRef<string | null>(null);

  // Memoize WebSocket handlers to prevent reconnection loops
  const handlers = useMemo(() => ({
    trade: (data: unknown) => dispatch({ type: 'ADD_TRADE', payload: data as TradeEvent }),
    position: (data: unknown) => dispatch({ type: 'UPDATE_POSITION', payload: data as WalletPosition }),
    market: (data: unknown) => dispatch({ type: 'UPDATE_MARKET', payload: data as MarketContext }),
    stats: (data: unknown) => dispatch({ type: 'UPDATE_STATS', payload: data as TrackerStats }),
    connected: () => console.log('WebSocket connected'),
    ping: () => {}, // Keepalive ping, ignore
  }), []);

  const { isConnected } = useWebSocket(WS_URL, handlers);

  useEffect(() => {
    dispatch({ type: 'SET_CONNECTED', payload: isConnected });
  }, [isConnected]);

  // Poll for new trades every 3 seconds as fallback
  // Note: refreshDataRef is defined after refreshData callback below
  useEffect(() => {
    const pollTrades = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/trades?limit=50`);
        if (res.ok) {
          const trades = await res.json();
          if (trades.length > 0 && trades[0].id !== lastTradeIdRef.current) {
            lastTradeIdRef.current = trades[0].id;
            // Trigger full refresh to get all trades, not just 50
            refreshDataRef.current();
          }
        }
      } catch (e) {
        // Silently fail polling
      }
    };

    const interval = setInterval(pollTrades, 3000);
    return () => clearInterval(interval);
  }, []);

  // Fetch config
  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      if (res.ok) {
        const config = await res.json();
        dispatch({ type: 'SET_CONFIG', payload: config });
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
    }
  }, []);

  // Fetch all data
  const refreshData = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      // Fetch config
      await fetchConfig();

      // Fetch wallets
      const walletsRes = await fetch(`${API_BASE}/api/wallets`);
      if (walletsRes.ok) {
        const wallets = await walletsRes.json();
        dispatch({ type: 'SET_WALLETS', payload: wallets });
      }

      // Fetch recent trades (get all available)
      const tradesRes = await fetch(`${API_BASE}/api/trades?limit=2000`);
      if (tradesRes.ok) {
        const trades = await tradesRes.json();
        dispatch({ type: 'SET_TRADES', payload: trades });
      }

      // Fetch positions
      const positionsRes = await fetch(`${API_BASE}/api/positions`);
      if (positionsRes.ok) {
        const positions = await positionsRes.json();
        dispatch({ type: 'SET_POSITIONS', payload: positions });
      }

      // Fetch price counts by market
      const pricesByMarketRes = await fetch(`${API_BASE}/api/prices/by-market`);
      if (pricesByMarketRes.ok) {
        const pricesByMarket = await pricesByMarketRes.json();
        dispatch({ type: 'SET_PRICES_BY_MARKET', payload: pricesByMarket });
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [fetchConfig]);

  // Ref for polling to access latest refreshData
  const refreshDataRef = useRef(refreshData);
  refreshDataRef.current = refreshData;

  // Initial data fetch
  useEffect(() => {
    refreshData();

    // Poll for config updates every 5 seconds
    const interval = setInterval(fetchConfig, 5000);
    return () => clearInterval(interval);
  }, [refreshData, fetchConfig]);

  // Poll for price stream status every 5 seconds
  useEffect(() => {
    const pollPriceStreamStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/price-stream/status`);
        if (res.ok) {
          const status = await res.json();
          dispatch({ type: 'SET_PRICE_STREAM_STATUS', payload: status });
        }
      } catch (e) {
        // Silently fail polling
      }
    };
    pollPriceStreamStatus();
    const interval = setInterval(pollPriceStreamStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Toggle tracker on/off
  const toggleTracker = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tracker/toggle`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        dispatch({
          type: 'SET_CONFIG',
          payload: { ...state.config!, running: result.running }
        });
      }
    } catch (error) {
      console.error('Failed to toggle tracker:', error);
    }
  }, [state.config]);

  // Update tracked wallet
  const updateWallet = useCallback(async (address: string, name: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/config/wallet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, name })
      });
      if (res.ok) {
        await fetchConfig();
        // Clear trades and positions for new wallet
        dispatch({ type: 'SET_TRADES', payload: [] });
        dispatch({ type: 'SET_POSITIONS', payload: [] });
      }
    } catch (error) {
      console.error('Failed to update wallet:', error);
    }
  }, [fetchConfig]);

  const selectWallet = useCallback((wallet: string | null) => {
    dispatch({ type: 'SELECT_WALLET', payload: wallet });
  }, []);

  return (
    <TrackerContext.Provider value={{
      state,
      dispatch,
      selectWallet,
      toggleTracker,
      updateWallet,
      refreshData
    }}>
      {children}
    </TrackerContext.Provider>
  );
}

export function useTracker() {
  const context = useContext(TrackerContext);
  if (!context) {
    throw new Error('useTracker must be used within TrackerProvider');
  }
  return context;
}

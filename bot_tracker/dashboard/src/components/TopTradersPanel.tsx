import { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Trader {
  name: string;
  wallet: string;
  link: string;
  all_time_profit: number;
}

export function TopTradersPanel() {
  const [traders, setTraders] = useState<Trader[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    wallet: '',
    link: '',
    all_time_profit: ''
  });
  const [error, setError] = useState('');

  const fetchTraders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/traders`);
      if (res.ok) {
        setTraders(await res.json());
      }
    } catch (e) {
      console.error('Failed to fetch traders');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTraders();
  }, [fetchTraders]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name || !formData.wallet || !formData.link || !formData.all_time_profit) {
      setError('All fields are required');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/traders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          wallet: formData.wallet,
          link: formData.link,
          all_time_profit: parseFloat(formData.all_time_profit.replace(/,/g, ''))
        })
      });

      if (res.ok) {
        setFormData({ name: '', wallet: '', link: '', all_time_profit: '' });
        setShowForm(false);
        fetchTraders();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to add trader');
      }
    } catch (e) {
      setError('Failed to add trader');
    }
  };

  const handleDelete = async (wallet: string) => {
    if (!confirm('Are you sure you want to delete this trader?')) return;

    try {
      const res = await fetch(`${API_BASE}/api/traders/${wallet}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchTraders();
      }
    } catch (e) {
      console.error('Failed to delete trader');
    }
  };

  const formatProfit = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const truncateWallet = (wallet: string) => {
    return `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Top Bot Traders</h2>
          <p className="text-xs text-gray-500 mt-1">All-time profits are manually tracked, not live updated</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Trader'}
        </button>
      </div>

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 p-4 bg-gray-700/50 rounded-lg border border-gray-600">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., gabagool22"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Wallet Address</label>
              <input
                type="text"
                value={formData.wallet}
                onChange={(e) => setFormData({ ...formData, wallet: e.target.value })}
                placeholder="0x..."
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm font-mono placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Profile Link</label>
              <input
                type="text"
                value={formData.link}
                onChange={(e) => setFormData({ ...formData, link: e.target.value })}
                placeholder="https://polymarket.com/@..."
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">All-Time Profit ($)</label>
              <input
                type="text"
                value={formData.all_time_profit}
                onChange={(e) => setFormData({ ...formData, all_time_profit: e.target.value })}
                placeholder="e.g., 570312.90"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
          <button
            type="submit"
            className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded transition-colors"
          >
            Add Trader
          </button>
        </form>
      )}

      {/* Traders Table */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : traders.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No traders added yet. Click "Add Trader" to get started.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="text-left py-2 px-2">#</th>
                <th className="text-left py-2 px-2">Name</th>
                <th className="text-left py-2 px-2">Wallet</th>
                <th className="text-right py-2 px-2">All-Time Profit</th>
                <th className="text-right py-2 px-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {traders.map((trader, index) => (
                <tr key={trader.wallet} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-3 px-2 text-gray-400">{index + 1}</td>
                  <td className="py-3 px-2">
                    <a
                      href={trader.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 hover:underline"
                    >
                      {trader.name}
                    </a>
                  </td>
                  <td className="py-3 px-2 font-mono text-gray-400">
                    <span title={trader.wallet}>{truncateWallet(trader.wallet)}</span>
                  </td>
                  <td className="py-3 px-2 text-right text-green-400 font-medium">
                    {formatProfit(trader.all_time_profit)}
                  </td>
                  <td className="py-3 px-2 text-right">
                    <button
                      onClick={() => handleDelete(trader.wallet)}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Total */}
      {traders.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-700 flex justify-between text-sm">
          <span className="text-gray-400">{traders.length} traders tracked</span>
          <span className="text-gray-400">
            Total Profit: <span className="text-green-400 font-medium">
              {formatProfit(traders.reduce((sum, t) => sum + t.all_time_profit, 0))}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}

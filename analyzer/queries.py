"""
SQL query templates for trade analysis
"""

# Total P&L (simplified - based on buy/sell pairs)
TOTAL_PNL = """
SELECT
    w.name as wallet_name,
    w.address,
    SUM(CASE WHEN t.side = 'SELL' THEN t.usdc_amount ELSE -t.usdc_amount END) as realized_pnl,
    SUM(t.usdc_amount) as total_volume,
    COUNT(*) as trade_count
FROM trades t
JOIN wallets w ON t.wallet_id = w.id
WHERE t.wallet_address = ?
GROUP BY w.id
"""

# Trade frequency by day
TRADE_FREQUENCY = """
SELECT
    date(timestamp) as trade_date,
    COUNT(*) as num_trades,
    SUM(usdc_amount) as daily_volume,
    AVG(usdc_amount) as avg_trade_size,
    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buys,
    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sells
FROM trades
WHERE wallet_address = ?
GROUP BY date(timestamp)
ORDER BY trade_date DESC
"""

# Average trade size by category
TRADE_SIZE_BY_CATEGORY = """
SELECT
    COALESCE(m.category, 'Unknown') as category,
    AVG(t.usdc_amount) as avg_size,
    AVG(t.shares) as avg_shares,
    AVG(t.price) as avg_price,
    COUNT(*) as num_trades,
    SUM(t.usdc_amount) as total_volume
FROM trades t
LEFT JOIN markets m ON t.condition_id = m.condition_id
WHERE t.wallet_address = ?
GROUP BY m.category
ORDER BY total_volume DESC
"""

# Arbitrage detection (both sides bought in same market)
ARBITRAGE_DETECTION = """
SELECT
    m.question,
    t.condition_id,
    COUNT(DISTINCT t.outcome) as outcomes_traded,
    GROUP_CONCAT(DISTINCT t.outcome) as outcomes,
    SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as total_bought,
    SUM(CASE WHEN t.side = 'BUY' THEN t.shares ELSE 0 END) as shares_bought,
    COUNT(*) as num_trades,
    MIN(t.timestamp) as first_trade,
    MAX(t.timestamp) as last_trade,
    -- Time span in minutes
    (julianday(MAX(t.timestamp)) - julianday(MIN(t.timestamp))) * 24 * 60 as duration_minutes
FROM trades t
LEFT JOIN markets m ON t.condition_id = m.condition_id
WHERE t.wallet_address = ?
GROUP BY t.condition_id
HAVING COUNT(DISTINCT t.outcome) > 1
ORDER BY total_bought DESC
"""

# Arbitrage P&L calculation
ARBITRAGE_PNL = """
WITH market_positions AS (
    SELECT
        t.condition_id,
        m.question,
        t.outcome,
        SUM(CASE WHEN t.side = 'BUY' THEN t.shares ELSE 0 END) as bought_shares,
        SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as buy_cost,
        AVG(CASE WHEN t.side = 'BUY' THEN t.price ELSE NULL END) as avg_buy_price
    FROM trades t
    LEFT JOIN markets m ON t.condition_id = m.condition_id
    WHERE t.wallet_address = ?
    GROUP BY t.condition_id, t.outcome
)
SELECT
    condition_id,
    question,
    GROUP_CONCAT(outcome || ':' || ROUND(bought_shares, 0) || '@' || ROUND(avg_buy_price, 2)) as positions,
    SUM(bought_shares) as total_shares,
    SUM(buy_cost) as total_cost,
    MIN(bought_shares) as min_position,
    -- Guaranteed payout (min of all positions)
    MIN(bought_shares) as guaranteed_payout,
    -- Guaranteed profit
    MIN(bought_shares) - SUM(buy_cost) as guaranteed_profit
FROM market_positions
GROUP BY condition_id
HAVING COUNT(DISTINCT outcome) > 1
ORDER BY guaranteed_profit DESC
"""

# Contract distribution (CTF vs NegRisk)
CONTRACT_DISTRIBUTION = """
SELECT
    contract,
    COUNT(*) as num_trades,
    SUM(usdc_amount) as total_volume,
    AVG(usdc_amount) as avg_trade_size,
    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buys,
    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sells
FROM trades
WHERE wallet_address = ?
GROUP BY contract
"""

# Market breakdown with positions
MARKET_BREAKDOWN = """
SELECT
    m.question,
    m.category,
    t.outcome,
    SUM(CASE WHEN t.side = 'BUY' THEN t.shares ELSE -t.shares END) as net_shares,
    SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as buy_cost,
    SUM(CASE WHEN t.side = 'SELL' THEN t.usdc_amount ELSE 0 END) as sell_revenue,
    SUM(CASE WHEN t.side = 'SELL' THEN t.usdc_amount ELSE 0 END) -
    SUM(CASE WHEN t.side = 'BUY' THEN t.usdc_amount ELSE 0 END) as realized_pnl,
    AVG(t.price) as avg_price,
    COUNT(*) as num_trades,
    MIN(t.timestamp) as first_trade,
    MAX(t.timestamp) as last_trade
FROM trades t
LEFT JOIN markets m ON t.condition_id = m.condition_id
WHERE t.wallet_address = ?
GROUP BY t.condition_id, t.outcome
ORDER BY buy_cost DESC
LIMIT ?
"""

# Hourly activity pattern
HOURLY_PATTERN = """
SELECT
    strftime('%H', timestamp) as hour,
    COUNT(*) as num_trades,
    SUM(usdc_amount) as volume,
    AVG(usdc_amount) as avg_size
FROM trades
WHERE wallet_address = ?
GROUP BY strftime('%H', timestamp)
ORDER BY hour
"""

# Price distribution
PRICE_DISTRIBUTION = """
SELECT
    CASE
        WHEN price < 0.1 THEN '0.00-0.10'
        WHEN price < 0.2 THEN '0.10-0.20'
        WHEN price < 0.3 THEN '0.20-0.30'
        WHEN price < 0.4 THEN '0.30-0.40'
        WHEN price < 0.5 THEN '0.40-0.50'
        WHEN price < 0.6 THEN '0.50-0.60'
        WHEN price < 0.7 THEN '0.60-0.70'
        WHEN price < 0.8 THEN '0.70-0.80'
        WHEN price < 0.9 THEN '0.80-0.90'
        ELSE '0.90-1.00'
    END as price_range,
    side,
    COUNT(*) as num_trades,
    SUM(usdc_amount) as volume
FROM trades
WHERE wallet_address = ?
GROUP BY price_range, side
ORDER BY price_range, side
"""

# Recent trades
RECENT_TRADES = """
SELECT
    t.timestamp,
    m.question,
    t.outcome,
    t.side,
    t.shares,
    t.usdc_amount,
    t.price,
    t.contract,
    t.transaction_hash
FROM trades t
LEFT JOIN markets m ON t.condition_id = m.condition_id
WHERE t.wallet_address = ?
ORDER BY t.timestamp DESC
LIMIT ?
"""

The Algorithm

  LOOP every 1-2 seconds:

      1. Get current market mid-price
         mid_up = (best_bid_up + best_ask_up) / 2    # e.g., $0.35
         mid_down = (best_bid_down + best_ask_down) / 2  # e.g., $0.65

      2. Calculate target bid prices
         target_up = mid_up - spread       # $0.35 - $0.02 = $0.33
         target_down = mid_down - spread   # $0.65 - $0.02 = $0.63

      3. Verify combined < $1.00
         if target_up + target_down >= $1.00:
             reduce one or both bids

      4. Cancel old orders, place new orders
         cancel_all_orders()
         place_bid(UP, price=$0.33, size=1000)
         place_bid(DOWN, price=$0.63, size=1000)

      5. Check fills, rebalance if needed
         if up_position >> down_position:
             sell_excess_up()  # taker sell to rebalance

  Why It Works

  The bot follows the market - wherever the price goes, the bot places bids just below. Since UP + DOWN always = $1 at resolution, buying both for < $1 is guaranteed profit.



  This user is a high-frequency market maker running a "bid-only" strategy on both sides of a binary market.

  The Strategy in Simple Terms:

  ┌─────────────────────────────────────────────────────────────────┐
  │  1. POST BIDS ON BOTH SIDES                                     │
  │     • Place buy orders for Up at various prices                 │
  │     • Place buy orders for Down at various prices               │
  │     • Wait for sellers to hit your bids                         │
  │                                                                 │
  │  2. ACCUMULATE CHEAP INVENTORY                                  │
  │     • Buy Up + Down at combined price < $1.00                   │
  │     • They achieved avg $0.9804 combined ($0.0196 edge/set)     │
  │                                                                 │
  │  3. REBALANCE WITH ATOMIC SWAPS                                 │
  │     • When inventory gets lopsided, sell one side + buy other   │
  │     • 86 atomic swaps executed (combined price always = $1.00)  │
  └─────────────────────────────────────────────────────────────────┘

  Key Stats:
  ┌────────────────────────────┬──────────────────────────┐
  │           Metric           │          Value           │
  ├────────────────────────────┼──────────────────────────┤
  │ Trading window             │ 14 minutes               │
  ├────────────────────────────┼──────────────────────────┤
  │ Trade frequency            │ 57 trades/minute         │
  ├────────────────────────────┼──────────────────────────┤
  │ Maker trades (bids filled) │ 647 (79%) - ALL buys     │
  ├────────────────────────────┼──────────────────────────┤
  │ Taker trades (rebalancing) │ 169 (21%) - mostly sells │
  └────────────────────────────┴──────────────────────────┘
  Position Evolution:

  The market moved from 40% Up → 98% Up during trading. They ended with:
  - 3,509 Up shares (worth $1 if Up wins)
  - 3,974 Down shares (worth $1 if Down wins)
  - $3,674 invested

  P&L (ignoring fees):

  - If Up won: -$165 loss
  - If Down won: +$300 profit

  They were slightly contrarian (more Down than Up) in a market that heavily favored Up at the end. The strategy is designed to exit before resolution by selling inventory, but they got caught holding when the market closed.
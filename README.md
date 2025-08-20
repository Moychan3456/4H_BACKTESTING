# Forex Backtesting & Strategy Research 📊

This repository contains my **forex trading backtesting framework** built in Python.  
It uses real historical data from Dukascopy, applies **candlestick pattern detection**, and backtests strategies with **vectorbt**.

At the current stage, only **one bearish zone-based 4H strategy** is implemented.  
But this project is designed to scale — more strategies (weekly, daily, 4H variations, etc.) will be added over time.

---

## 🚀 Features

- ✅ Fetches tick-accurate forex data from **Dukascopy**
- ✅ Resamples raw data into DST-aware OHLC candles (IST/NY session handling)
- ✅ Detects **bearish candlestick zones**
- ✅ Automatically sets **Entry / SL / TP** with Risk:Reward logic
- ✅ Backtests trades with **vectorbt**
- ✅ Position sizing based on **fixed risk per trade**
- ✅ Plots candles with **zones, entries, exits, and trade highlights**

---

## 📊 Current Strategy (Implemented)

**Bearish Zone Rejection – 4H Timeframe**

1. Detects a bearish candle that forms a "zone" (open → low range).  
2. Confirms next 3 candles stay inside the zone.  
3. Entry = close of 4th confirming candle  
4. Stop Loss = low of 3rd candle  
5. Take Profit = based on Risk:Reward ratio (default **1:1.5**)  
6. Position size = automatically calculated from fixed risk (default **$500 risk per trade**)  

---

## 📈 Backtest Results

Run from **2020-01-01 to 2025-08-19**  
Initial Capital = **$100,000**  
Risk = **$500/trade (0.5% of account)**  

See [`output.txt`](output.txt) for full stats.

Highlights:
- ✅ **Total Return:** +82.48%  
- ✅ **Win Rate:** ~51%  
- ✅ **Profit Factor:** 1.47  
- ✅ **Sharpe Ratio:** 0.65  
- ⚠️ Max Drawdown: -32.56% (currently working on improvements)

---

## 🛠 Tech Stack

- **Python**
- [vectorbt](https://github.com/polakowo/vectorbt) – fast backtesting
- [dukascopy-python](https://github.com/Leo4815162342/dukascopy-python) – forex data
- [mplfinance](https://github.com/matplotlib/mplfinance) – financial plotting
- **pandas, numpy** – data processing

---

## 📌 Roadmap (Next Steps)

- [ ] Add **Weekly timeframe** strategy  
- [ ] Add **Daily timeframe** strategy  
- [ ] Implement more 4H variations (trend continuation, breakouts)  
- [ ] Compare performance across multiple currency pairs  
- [ ] Build a **strategy selector** to combine multiple systems  
- [ ] Export reports automatically in HTML/Notebook  

---

## ⚡ How to Run

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/forex-backtester.git
   cd forex-backtester
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python backtest.py
   ```

4. View backtest output:
   - Stats → `output.txt`
   - Visuals → Matplotlib window

---

## 📬 Contact

If you’re a recruiter, quant researcher, or trader interested in this project — feel free to reach out!

**Author:** Chinmoy S. Patir  
**Email:** chinmoypatir@example.com  
**LinkedIn:** [Chinmoy Patir](https://www.linkedin.com/in/chinmoy-patir-a24206286/)  
**GitHub:** [Moychan3456](https://github.com/Moychan3456?tab=repositories)

---

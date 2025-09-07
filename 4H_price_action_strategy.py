from datetime import datetime
import pandas as pd
import numpy as np
import pytz
import mplfinance as mpf
import dukascopy_python as dp
import vectorbt as vbt

# ================================
# CONFIGURATION
# ================================
symbol = "USD/CHF"
timeframe = "4H"
start_date = datetime(2020, 1, 1)
end_date = datetime(2025, 8, 19)
last_candles = 100  # number of candles to plot
RR_RATIO = 2      # Risk-to-Reward ratio (e.g., 2.0 for 1:2)
CAPITAL = 100000.0   # Initial capital for the backtest
RISK_PER_TRADE = 500.0  # Fixed risk per trade (0.5% of 100k)

# ================================
# FETCH & PREPARE RAW DATA
# ================================
df = dp.fetch(symbol, dp.INTERVAL_HOUR_1, dp.OFFER_SIDE_BID, start_date, end_date)
df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
df = df[['Open', 'High', 'Low', 'Close']].dropna()

df.index = df.index.tz_localize('UTC') if df.index.tz is None else df.index.tz_convert('UTC')

# ================================
# RESAMPLE (DST-aware IST logic)
# ================================
ny_index = df.index.tz_convert("America/New_York")
actual_offset = ny_index.map(lambda dt: dt.utcoffset())
standard_offset = pd.Timedelta(hours=-5)
is_dst = actual_offset != standard_offset
df["GroupKey"] = np.where(is_dst, "02:30:00", "03:30:00")

resampled = []

for key, group in df.groupby("GroupKey"):
    origin = pd.Timestamp(f"2000-01-03 {key}", tz="Asia/Kolkata")
    group_ist = group.tz_convert("Asia/Kolkata")

    resampled_group = group_ist.resample(
        rule=timeframe.lower(),
        label="left",
        closed="left",
        origin=origin
    ).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last'
    }).dropna()

    resampled.append(resampled_group)

df_resampled = pd.concat(resampled).sort_index()
df_resampled['Bearish'] = df_resampled['Open'] > df_resampled['Close']

# ================================
# PATTERN DETECTION & TRADE SETUP
# ================================
zone_patterns = []
trade_setups = []
index_list = df_resampled.index.to_list()

for i in range(len(df_resampled) - 4):
    row = df_resampled.iloc[i]

    if row['Open'] > row['Close']:  # Bearish
        open_price = row['Open']
        close_price = row['Close']
        low_price = row['Low']
        body_size = open_price - close_price
        mid_body = close_price + (body_size * 0.5)

        zone_top = open_price
        zone_bottom = low_price
        bearish_time = index_list[i]
        all_valid = True

        for j in range(1, 4):
            next_row = df_resampled.iloc[i + j]
            next_close = next_row['Close']
            next_high = next_row['High']

            close_in_zone = zone_bottom <= next_close <= zone_top
            high_respected = next_high < open_price
            weak_close = next_close <= mid_body

            if not (close_in_zone and high_respected and weak_close):
                all_valid = False
                break

        if all_valid:
            pattern_end_time = index_list[i + 3]
            entry_price = df_resampled.iloc[i + 3]['Close']
            
            # --- MODIFIED SL CONDITION ---
            sl_price = df_resampled.iloc[i+2]['High']
            
            risk = sl_price - entry_price
            tp_price = entry_price - (risk * RR_RATIO)
            
            # Store the pattern and trade setup
            zone_patterns.append({
                "Pattern_Start": bearish_time,
                "Pattern_End": pattern_end_time,
                "Zone_Top": zone_top,
                "Zone_Bottom": zone_bottom
            })
            trade_setups.append({
                "entry_time": pattern_end_time,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price
            })

# ================================
# BACKTESTING WITH VECTORBT
# ================================
if trade_setups:
    entries = pd.Series(False, index=df_resampled.index)
    exits = pd.Series(False, index=df_resampled.index)
    sizes = pd.Series(np.nan, index=df_resampled.index) # Initialize sizes series
    
    entry_marker_prices = pd.Series(np.nan, index=df_resampled.index)
    exit_marker_prices = pd.Series(np.nan, index=df_resampled.index)

    last_exit_time = pd.NaT

    for setup in trade_setups:
        entry_time = setup['entry_time']
        if entry_time <= last_exit_time:
            continue

        entries.loc[entry_time] = True
        entry_marker_prices.loc[entry_time] = setup['entry_price'] * 1.0002
        
        sl_price = setup['sl_price']
        entry_price = setup['entry_price']
        tp_price = setup['tp_price']
        
        # Calculate position size based on fixed risk per trade
        risk_per_unit_price = abs(sl_price - entry_price) 
        if risk_per_unit_price > 0:
            calculated_size = RISK_PER_TRADE / risk_per_unit_price
            sizes.loc[entry_time] = calculated_size
        
        simulation_df = df_resampled.loc[df_resampled.index > entry_time]
        
        exit_time = None
        for i in range(len(simulation_df)):
            current_bar = simulation_df.iloc[i]
            
            if current_bar['High'] >= sl_price or current_bar['Low'] <= tp_price:
                exit_time = current_bar.name
                exits.loc[exit_time] = True
                exit_marker_prices.loc[exit_time] = current_bar['Close']
                break
        
        if exit_time is not None:
            last_exit_time = exit_time
            
    # Run the backtest using vectorbt
    pf = vbt.Portfolio.from_signals(
        df_resampled['Close'],
        entries,
        exits,
        size=sizes,
        size_type='amount',
        direction='shortonly',
        init_cash=CAPITAL,
        fees=0.0001,
        freq=timeframe
    )

    print("==================================")
    print(f"BACKTESTING STATS (RR = 1:{RR_RATIO}, Risk = ${RISK_PER_TRADE})")
    print("==================================")
    print(pf.stats())

# ================================
# PLOT CANDLES + ZONES & TRADE VISUALS
# ================================
df_last = df_resampled.tail(last_candles).copy()
highlight_indices = []

# Store shaded zones
zone_patches = []

for pattern in zone_patterns:
    if pattern["Pattern_Start"] in df_last.index:
        idx_start = df_last.index.get_loc(pattern["Pattern_Start"])
        idx_end = df_last.index.get_loc(pattern["Pattern_End"])

        highlight_indices.extend(df_last.index[idx_start:idx_end + 1])

        zone_patches.append({
            "start": df_last.index[idx_start],
            "end": df_last.index[idx_end],
            "top": pattern["Zone_Top"],
            "bottom": pattern["Zone_Bottom"]
        })

# Highlight pattern candles (colored dots)
highlight_marker = pd.Series(np.nan, index=df_last.index)
highlight_marker.loc[highlight_indices] = df_last.loc[highlight_indices, 'High'] * 1.002

# Entry and Exit markers
entry_marker = pd.Series(np.nan, index=df_last.index)
entry_marker_prices_in_plot = entry_marker_prices.loc[df_last.index].dropna()
entry_marker.loc[entry_marker_prices_in_plot.index] = entry_marker_prices_in_plot.values

exit_marker = pd.Series(np.nan, index=df_last.index)
exit_marker_prices_in_plot = exit_marker_prices.loc[df_last.index].dropna()
exit_marker.loc[exit_marker_prices_in_plot.index] = exit_marker_prices_in_plot.values


addplot_list = [
    mpf.make_addplot(highlight_marker, type='scatter', markersize=60, marker='o', color='green'),
    mpf.make_addplot(entry_marker, type='scatter', markersize=100, marker='^', color='green'),
    mpf.make_addplot(exit_marker, type='scatter', markersize=100, marker='v', color='red')
]

# Create custom shading for zones
def add_zone(ax):
    for zone in zone_patches:
        # Check if the start and end times of the zone are within the plotted df_last index
        if zone['start'] in df_last.index and zone['end'] in df_last.index:
            idx_start = df_last.index.get_loc(zone['start'])
            idx_end = df_last.index.get_loc(zone['end'])
            ax.axhspan(
                zone['bottom'], zone['top'],
                xmin=(idx_start / len(df_last)),
                xmax=((idx_end + 1) / len(df_last)), # +1 to include the end candle
                color='red', alpha=0.2
            )

# Plot with shading callback, WITHOUT the alines parameter
fig, axlist = mpf.plot(
    df_last.tz_localize(None),
    type='candle',
    style='yahoo',
    title=f"{symbol} {timeframe} - Zone Pattern & Trades",
    figsize=(20, 10),
    volume=False,
    addplot=addplot_list,
    update_width_config=dict(candle_linewidth=1.2),
    tight_layout=True,
    returnfig=True
)

# Manually add horizontal lines using the returned axes object
if trade_setups and trade_setups[-1]['entry_time'] in df_last.index:
    ax = fig.axes[0]
    last_setup = trade_setups[-1]
    ax.axhline(y=last_setup['entry_price'], color='green', linestyle='--', label=f"Entry: {last_setup['entry_price']:.4f}")
    ax.axhline(y=last_setup['sl_price'], color='red', linestyle='--', label=f"SL: {last_setup['sl_price']:.4f}")
    ax.axhline(y=last_setup['tp_price'], color='blue', linestyle='--', label=f"TP: {last_setup['tp_price']:.4f}")
    ax.legend(loc='best')

# Connect the zone shading function to the plot's draw event
fig.axes[0].figure.canvas.mpl_connect('draw_event', lambda event: add_zone(event.canvas.figure.axes[0]))


mpf.show()

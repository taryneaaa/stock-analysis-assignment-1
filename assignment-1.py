import datetime as dt

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from stock import Stock

# ============================================================
# STEP 2: Page setup and cached data loader
# ============================================================
st.set_page_config(page_title="Stock Analysis", layout="wide")
st.title("Stock Analysis")


@st.cache_data
def load_stock(symbol, start, end, ma_window, ma_long):
    """Create a Stock object (this is the download). Cached so the same
    inputs don't trigger another download."""
    return Stock(symbol, start=start, end=end,
                 ma_window=ma_window, ma_long=ma_long)  # NEW: ma_long


# ============================================================
# STEP 3: Shared sidebar
# ============================================================
st.sidebar.header("Settings")
symbol = st.sidebar.text_input("Ticker symbol", "AAPL").strip().upper()

today = dt.date.today()
start = st.sidebar.date_input("Start date", today - dt.timedelta(days=365))
end = st.sidebar.date_input("End date", today)

ma_window = st.sidebar.slider("Short moving average window (days)", 5, 200, 20)
# NEW: second (long) moving average slider
ma_long = st.sidebar.slider("Long moving average window (days)", 5, 200, 50)
if ma_window >= ma_long:
    st.sidebar.warning("Short MA window should be smaller than long MA window.")

if st.sidebar.button("Fetch data", type="primary"):
    st.session_state["fetched"] = True

if start >= end:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

# ============================================================
# Create the two tabs
# ============================================================
tab1, tab2 = st.tabs(["Single Stock Analysis", "Portfolio Comparison"])

# ============================================================
# STEP 4: Tab 1 - Single Stock Analysis
# ============================================================
with tab1:
    if not st.session_state.get("fetched"):
        st.info("Choose a ticker in the sidebar and click **Fetch data**.")
    else:
        with st.spinner(f"Downloading {symbol}..."):
            stock = load_stock(symbol, start, end, ma_window, ma_long)  # NEW: ma_long

        if stock.data is None:
            st.error(stock.message)
        else:
            st.success(stock.message)
            df = stock.data

            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Last close", f"${df['Close'].iloc[-1]:,.2f}",
                      f"{df['change'].iloc[-1]:+.2f}")
            c2.metric("Cumulative return",
                      f"{np.exp(df['return'].sum()) - 1:.2%}")
            c3.metric("Trading days", len(df))

            # Close + moving average chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close"))
            fig.add_trace(go.Scatter(x=df.index, y=df["MA"],
                                     name=f"{ma_window}-day MA"))
            # NEW: long moving average line
            fig.add_trace(go.Scatter(x=df.index, y=df["MA_long"],
                                     name=f"{ma_long}-day MA"))
            fig.update_layout(title=f"{symbol} Close and Moving Averages",
                              xaxis_title="Date", yaxis_title="Price ($)",
                              hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # Charts provided by the Stock class
            st.plotly_chart(stock.plot_performance(), use_container_width=True)
            st.plotly_chart(stock.plot_return_dist(), use_container_width=True)

            # Statistics table
            st.subheader("Return statistics")
            st.dataframe(df["return"].describe().to_frame())


            # Temporary: daily data for the two-stock write-up
            with st.expander("Daily data"):
                st.dataframe(df[["Close", "change", "return"]])

# ============================================================
# STEP 5: Tab 2 - Portfolio Comparison
# ============================================================
with tab2:
    tickers_text = st.text_input("Tickers (comma-separated)", "AAPL, MSFT, GOOG")

    if st.button("Compare"):
        st.session_state["compare"] = True

    if st.session_state.get("compare"):
        tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]
        tickers = list(dict.fromkeys(tickers))  # remove duplicates, keep order

        fig = go.Figure()
        for t in tickers:
            with st.spinner(f"Downloading {t}..."):
                s = load_stock(t, start, end, ma_window, ma_long)  # NEW: ma_long

            if s.data is None:
                st.error(f"{t}: {s.message}")
                continue  # skip the failed ticker, keep going

            cum = s.data["return"].cumsum()
            cum = cum - cum.iloc[0]  # make every line start at exactly 0.0
            fig.add_trace(go.Scatter(x=cum.index, y=cum, mode="lines", name=t))

        fig.update_layout(title="Zero-based cumulative performance",
                          xaxis_title="Date",
                          yaxis_title="Cumulative log return",
                          legend_title="Ticker",
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
# app.py
import streamlit as st
import pandas as pd
from db import read_df, read_value, table_min_max_date
from queries import PREDEFINED

st.set_page_config(page_title="Cross-Market Analysis", layout="wide")
st.title("💰🛢️📈 Cross-Market Analysis: Crypto, Oil & Stocks")

# --------- Utility functions ---------
@st.cache_data(ttl=600)
def get_top3_coins():
    sql = """
        SELECT id, name, market_cap_rank
        FROM cryptocurrencies
        WHERE market_cap_rank IS NOT NULL
        ORDER BY market_cap_rank
        LIMIT 3;
    """
    return read_df(sql)

@st.cache_data(ttl=600)
def get_overlap_dates():
    # Overlap among BTC, Oil, S&P (^GSPC), NIFTY (^NSEI)
    btc_min, btc_max = table_min_max_date("crypto_prices", "coin_id='bitcoin'")
    oil_min, oil_max = table_min_max_date("oil_prices")
    sp_min, sp_max = table_min_max_date("stock_prices", "ticker='^GSPC'")
    ni_min, ni_max = table_min_max_date("stock_prices", "ticker='^NSEI'")

    mins = [d for d in [btc_min, oil_min, sp_min, ni_min] if d]
    maxs = [d for d in [btc_max, oil_max, sp_max, ni_max] if d]
    if not mins or not maxs:
        return None, None
    start = max(mins)
    end = min(maxs)
    return start, end

# Sidebar navigation
page = st.sidebar.radio("Navigate", [
    "Filters & Data Exploration",
    "SQL Query Runner",
    "Top 3 Crypto Analysis",
])

# --------- Page 1: Filters & Data Exploration ---------
if page == "Filters & Data Exploration":
    st.subheader("🔹 Filters & Data Exploration")
    start_default, end_default = get_overlap_dates()
    if not start_default:
        st.error("No overlapping dates across BTC, Oil, S&P, and NIFTY. Load data first.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date", value=pd.to_datetime(start_default).date())
    with col2:
        end_date = st.date_input("End date", value=pd.to_datetime(end_default).date())

    if start_date > end_date:
        st.warning("Start date must be before end date.")
        st.stop()

    # KPIs: Averages
    kpi_sqls = {
        "Bitcoin Avg Price": ("SELECT ROUND(AVG(price_usd), 2) FROM crypto_prices WHERE coin_id=? AND date BETWEEN ? AND ?", ("bitcoin", start_date, end_date)),
        "Oil Avg Price": ("SELECT ROUND(AVG(price_usd), 2) FROM oil_prices WHERE date BETWEEN ? AND ?", (start_date, end_date)),
        "S&P 500 Avg Close": ("SELECT ROUND(AVG(close), 2) FROM stock_prices WHERE ticker='^GSPC' AND date BETWEEN ? AND ?", (start_date, end_date)),
        "NIFTY (^NSEI) Avg Close": ("SELECT ROUND(AVG(close), 2) FROM stock_prices WHERE ticker='^NSEI' AND date BETWEEN ? AND ?", (start_date, end_date)),
    }

    k1, k2, k3, k4 = st.columns(4)
    kcols = [k1, k2, k3, k4]
    for i, (label, (sql, params)) in enumerate(kpi_sqls.items()):
        val = read_value(sql, params)
        kcols[i].metric(label, f"{val if val is not None else '—'}")

    st.markdown("---")
    st.markdown("**📅 Daily Market Snapshot (JOIN on Date)**")
    snapshot_sql = """
        SELECT c.date AS date,
               c.price_usd AS btc_price,
               o.price_usd AS oil_price,
               sp.close     AS sp500_close,
               ni.close     AS nifty_close
        FROM crypto_prices c
        JOIN oil_prices o  ON c.date=o.date
        JOIN stock_prices sp ON c.date=sp.date AND sp.ticker='^GSPC'
        JOIN stock_prices ni ON c.date=ni.date AND ni.ticker='^NSEI'
        WHERE c.coin_id='bitcoin' AND c.date BETWEEN ? AND ?
        ORDER BY c.date;
    """
    snapshot_df = read_df(snapshot_sql, (start_date, end_date))

    if snapshot_df.empty:
        st.info("No snapshot rows for the selected date range.")
    else:
        st.dataframe(snapshot_df, use_container_width=True)
        with st.expander("Line Chart: BTC vs Oil vs S&P vs NIFTY"):
            chart_df = snapshot_df.set_index("date")[
                ["btc_price", "oil_price", "sp500_close", "nifty_close"]
            ]
            st.line_chart(chart_df)

# --------- Page 2: SQL Query Runner ---------
elif page == "SQL Query Runner":
    st.subheader("🔹 SQL Query Runner")
    query_name = st.selectbox("Choose a predefined query", list(PREDEFINED.keys()))
    st.code(PREDEFINED[query_name]["sql"], language="sql")
    if st.button("Run Query", type="primary"):
        try:
            df = read_df(PREDEFINED[query_name]["sql"])  # all predefined here are parameterless
            if df.empty:
                st.info("Query returned 0 rows.")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error executing query: {e}")

# --------- Page 3: Top 3 Crypto Analysis ---------
else:
    st.subheader("🔹 Top 3 Crypto Analysis")
    top3 = get_top3_coins()
    if top3.empty:
        st.error("Top 3 coins not found. Ensure 'cryptocurrencies' table is populated.")
        st.stop()

    coin_map = {f"{row['name']} ({row['id']})": row['id'] for _, row in top3.iterrows()}
    coin_label = st.selectbox("Select coin", list(coin_map.keys()))
    coin_id = coin_map[coin_label]

    cmin, cmax = table_min_max_date("crypto_prices", "coin_id=?", (coin_id,))
    if not cmin:
        st.error(f"No price data for {coin_id}.")
        st.stop()

    d1 = st.date_input("Start date", value=pd.to_datetime(cmin).date(), key="cstart")
    d2 = st.date_input("End date", value=pd.to_datetime(cmax).date(), key="cend")

    if d1 > d2:
        st.warning("Start date must be before end date.")
        st.stop()

    sql = """
        SELECT date, price_usd
        FROM crypto_prices
        WHERE coin_id=? AND date BETWEEN ? AND ?
        ORDER BY date;
    """
    df = read_df(sql, (coin_id, d1, d2))

    if df.empty:
        st.info("No rows for the selected range.")
    else:
        st.line_chart(df.set_index("date"))
        st.dataframe(df, use_container_width=True)


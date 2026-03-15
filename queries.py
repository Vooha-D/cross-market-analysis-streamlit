# queries.py

# NOTE: SQLite dialect (uses strftime). If you move to Postgres/MySQL, adjust date functions accordingly.

PREDEFINED = {
    # 1) cryptocurrencies
    "Top 3 cryptocurrencies by market cap": {
        "sql": """
            SELECT id, symbol, name, market_cap, market_cap_rank
            FROM cryptocurrencies
            ORDER BY market_cap DESC
            LIMIT 3;
        """
    },
    "Circulating supply > 90% of total": {
        "sql": """
            SELECT id, name, circulating_supply, total_supply,
                   ROUND(100.0 * circulating_supply / NULLIF(total_supply,0), 2) AS pct_circulating
            FROM cryptocurrencies
            WHERE total_supply IS NOT NULL AND total_supply > 0
              AND circulating_supply / total_supply > 0.9
            ORDER BY pct_circulating DESC;
        """
    },
    "Within 10% of ATH": {
        "sql": """
            SELECT id, name, current_price, ath,
                   ROUND(100.0 * (ath - current_price) / ath, 2) AS pct_below_ath
            FROM cryptocurrencies
            WHERE ath IS NOT NULL AND ath > 0
              AND current_price >= ath * 0.9
            ORDER BY pct_below_ath ASC;
        """
    },
    "Avg market cap rank (volume > $1B)": {
        "sql": """
            SELECT ROUND(AVG(market_cap_rank), 2) AS avg_rank
            FROM cryptocurrencies
            WHERE total_volume > 1000000000;
        """
    },
    "Most recently updated coin": {
        "sql": """
            SELECT id, name, date
            FROM cryptocurrencies
            ORDER BY date DESC
            LIMIT 1;
        """
    },

    # 2) crypto_prices
    "Highest daily price of Bitcoin (last 365 days)": {
        "sql": """
            SELECT MAX(price_usd) AS max_btc
            FROM crypto_prices
            WHERE coin_id='bitcoin' AND date >= DATE((SELECT MAX(date) FROM crypto_prices WHERE coin_id='bitcoin'), '-365 day');
        """
    },
    "Average daily price of Ethereum (last 1 year)": {
        "sql": """
            SELECT ROUND(AVG(price_usd), 4) AS avg_eth
            FROM crypto_prices
            WHERE coin_id='ethereum' AND date >= DATE((SELECT MAX(date) FROM crypto_prices WHERE coin_id='ethereum'), '-365 day');
        """
    },
    "Coin with highest average price (last 1 year among top 3)": {
        "sql": """
            WITH top3 AS (
                SELECT id FROM cryptocurrencies ORDER BY market_cap DESC LIMIT 3
            ), yearly AS (
                SELECT coin_id, AVG(price_usd) AS avg_price
                FROM crypto_prices
                WHERE date >= DATE((SELECT MAX(date) FROM crypto_prices), '-365 day')
                  AND coin_id IN (SELECT id FROM top3)
                GROUP BY coin_id
            )
            SELECT * FROM yearly ORDER BY avg_price DESC LIMIT 1;
        """
    },

    # 3) oil_prices
    "Highest oil price (last 5 years)": {
        "sql": """
            SELECT MAX(price_usd) AS max_oil
            FROM oil_prices
            WHERE date >= DATE((SELECT MAX(date) FROM oil_prices), '-5 year');
        """
    },
    "Average oil price per year": {
        "sql": """
            SELECT strftime('%Y', date) AS year, ROUND(AVG(price_usd), 2) AS avg_oil
            FROM oil_prices
            GROUP BY year
            ORDER BY year;
        """
    },
    "Oil prices during COVID crash (Mar–Apr 2020)": {
        "sql": """
            SELECT * FROM oil_prices
            WHERE date BETWEEN '2020-03-01' AND '2020-04-30'
            ORDER BY date;
        """
    },
    "Lowest oil price (last 10 years)": {
        "sql": """
            SELECT MIN(price_usd) AS min_oil
            FROM oil_prices
            WHERE date >= DATE((SELECT MAX(date) FROM oil_prices), '-10 year');
        """
    },
    "Oil price volatility per year (max-min)": {
        "sql": """
            SELECT strftime('%Y', date) AS year,
                   ROUND(MAX(price_usd) - MIN(price_usd), 2) AS volatility
            FROM oil_prices
            GROUP BY year
            ORDER BY year;
        """
    },

    # 4) stock_prices
    "All stock prices for a ticker (sample: ^GSPC)": {
        "sql": """
            SELECT * FROM stock_prices WHERE ticker='^GSPC' ORDER BY date;
        """
    },
    "Highest closing price for NASDAQ (^IXIC)": {
        "sql": """
            SELECT MAX(close) AS max_ixic FROM stock_prices WHERE ticker='^IXIC';
        """
    },
    "Top 5 days with highest (high - low) for S&P 500 (^GSPC)": {
        "sql": """
            SELECT date, ROUND(high-low, 4) AS intraday_spread
            FROM stock_prices
            WHERE ticker='^GSPC'
            ORDER BY intraday_spread DESC
            LIMIT 5;
        """
    },
    "Monthly average closing price for each ticker": {
        "sql": """
            SELECT ticker, strftime('%Y-%m', date) AS year_month,
                   ROUND(AVG(close), 4) AS avg_close
            FROM stock_prices
            GROUP BY ticker, year_month
            ORDER BY ticker, year_month;
        """
    },
    "Average trading volume of NSEI in 2024": {
        "sql": """
            SELECT ROUND(AVG(volume), 2) AS avg_vol_2024
            FROM stock_prices
            WHERE ticker='^NSEI' AND strftime('%Y', date)='2024';
        """
    },

    # 5) Join queries (cross-market)
    "Compare BTC vs Oil average price in 2025": {
        "sql": """
            SELECT (
                SELECT ROUND(AVG(price_usd), 2) FROM crypto_prices
                WHERE coin_id='bitcoin' AND strftime('%Y', date)='2025'
            ) AS avg_btc_2025,
            (
                SELECT ROUND(AVG(price_usd), 2) FROM oil_prices
                WHERE strftime('%Y', date)='2025'
            ) AS avg_oil_2025;
        """
    },
    "BTC vs S&P 500 (daily close join)": {
        "sql": """
            SELECT c.date, c.price_usd AS btc_price, s.close AS sp500_close
            FROM crypto_prices c
            JOIN stock_prices s ON c.date = s.date
            WHERE c.coin_id='bitcoin' AND s.ticker='^GSPC'
            ORDER BY c.date;
        """
    },
    "ETH vs NASDAQ (^IXIC) daily (2025)": {
        "sql": """
            SELECT c.date, c.price_usd AS eth_price, s.close AS nasdaq_close
            FROM crypto_prices c
            JOIN stock_prices s ON c.date=s.date
            WHERE c.coin_id='ethereum' AND s.ticker='^IXIC' AND strftime('%Y', c.date)='2025'
            ORDER BY c.date;
        """
    },
    "Oil spike days vs BTC daily change": {
        "sql": """
            WITH oil_change AS (
                SELECT date,
                       price_usd,
                       price_usd - LAG(price_usd) OVER (ORDER BY date) AS d_oil
                FROM oil_prices
            ), btc AS (
                SELECT date,
                       price_usd,
                       price_usd - LAG(price_usd) OVER (ORDER BY date) AS d_btc
                FROM crypto_prices
                WHERE coin_id='bitcoin'
            )
            SELECT o.date, o.d_oil, b.d_btc
            FROM oil_change o
            JOIN btc b ON o.date=b.date
            WHERE o.d_oil IS NOT NULL AND ABS(o.d_oil) >= (
                SELECT 0.95 * MAX(ABS(price_usd - LAG(price_usd) OVER (ORDER BY date))) FROM oil_prices
            )
            ORDER BY ABS(o.d_oil) DESC
            LIMIT 25;
        """
    },
    "BTC + Oil + S&P (daily multi-join)": {
        "sql": """
            SELECT c.date, c.price_usd AS btc, o.price_usd AS oil, s.close AS sp500
            FROM crypto_prices c
            JOIN oil_prices o ON c.date=o.date
            JOIN stock_prices s ON c.date=s.date
            WHERE c.coin_id='bitcoin' AND s.ticker='^GSPC'
            ORDER BY c.date;
        """
    },
}


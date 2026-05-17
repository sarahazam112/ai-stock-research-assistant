import os
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import yfinance as yf
import fitz
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import pandas as pd


def extract_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.read()
    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    text = ""
    for page in document:
        text += page.get_text()

    return text

def generate_groq_summary(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

HEADERS = {
    "User-Agent": "AI Stock Research Assistant sarahazam@example.com"
}

def get_cik_from_ticker(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    companies = response.json()

    for company in companies.values():

        if company["ticker"].lower() == ticker.lower():

            return str(company["cik_str"]).zfill(10)

    return None

def search_company(query):
    url = "https://www.sec.gov/files/company_tickers.json"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    companies = response.json()

    query = query.lower()

    for company in companies.values():

        ticker = company["ticker"]
        name = company["title"]

        if query == ticker.lower() or query in name.lower():

            return ticker, name

    return None, None


def get_latest_filing_url(ticker, form_type="10-K"):
    cik = get_cik_from_ticker(ticker)

    if not cik:
        return None

    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(submissions_url, headers=HEADERS)
    response.raise_for_status()

    data = response.json()
    recent = data["filings"]["recent"]

    for i, form in enumerate(recent["form"]):
        if form == form_type:
            accession = recent["accessionNumber"][i].replace("-", "")
            primary_doc = recent["primaryDocument"][i]
            cik_no_zeros = str(int(cik))

            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession}/{primary_doc}"
            return filing_url

    return None

st.set_page_config(
    page_title="AI Stock Research Assistant",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #f5f7fb;
}

.stButton button p {
    color: white !important;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

h1, h2, h3 {
    color: #111827;
}

p, label {
    color: #111827;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    color: #111827 !important;
}

[data-testid="stMetricValue"] {
    font-size: 2rem;
    color: #2563eb;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    font-size: 1rem;
    color: #6b7280;
}

code {
    background-color: transparent !important;
    color: #111827 !important;
}
pre {
    background-color: transparent !important;
}

</style>
""", unsafe_allow_html=True)

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Research Assistant",
        "Stock Comparison",
        "Portfolio vs S&P 500"
    ]
)

if page == "Research Assistant":
    st.title("AI Stock Research Assistant")

    st.write(
        "Upload financial documents or enter a stock ticker to generate an AI-powered research summary."
    )

    company_input = st.text_input(
        "Enter company name or stock ticker",
        placeholder="Example: Apple, Tesla, Air Canada, AAPL, TSLA"
    )

    uploaded_file = st.file_uploader(
        "Upload an earnings report, 10-K, or financial statement",
        type=["pdf", "csv", "txt"]
    )

    ticker = None
    company_name = None

    if company_input:
        ticker, company_name = search_company(company_input)

        if ticker:
            st.info(f"Using {company_name} ({ticker})")
        else:
            st.warning("Could not find that company. Try the official ticker.")

    if st.button("Analyze"):
        if not ticker and not uploaded_file:
            st.warning("Please enter a ticker or upload a file.")

        else:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Company Overview",
                "Financials",
                "Ratios",
                "AI Research Memo",
                "Uploaded Document"
            ])
        if ticker:
            stock = yf.Ticker(ticker)
            info = stock.info
            total_debt = info.get("totalDebt")
            total_cash = info.get("totalCash")
            market_cap = info.get("marketCap")
            current_ratio = info.get("currentRatio")
            profit_margin = info.get("profitMargins")
            revenue_growth = info.get("revenueGrowth")
            hist = stock.history(period="1y")
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet

            summary_prompt = f"""
You are an educational equity research assistant.

Create a professional stock research report for:

Company: {info.get("longName", ticker)}
Ticker: {ticker}
Business Summary: {info.get("longBusinessSummary", "N/A")}
Current Price: {info.get("currentPrice", "N/A")}
Market Cap: {info.get("marketCap", "N/A")}
PE Ratio: {info.get("trailingPE", "N/A")}
Total Debt: {info.get("totalDebt", "N/A")}
Total Cash: {info.get("totalCash", "N/A")}
Revenue Growth: {info.get("revenueGrowth", "N/A")}

Use this exact structure:

# Stock Research Report

## 1. Company Overview
## 2. Business Model
## 3. Revenue and Growth Trends
## 4. Debt and Liquidity
## 5. Key Risks
## 6. Growth Opportunities
## 7. Bull Case
## 8. Bear Case
## 9. Final Educational Summary
## 10. Sentiment Score
Give:
- Bullish Score (1-10)
- Risk Score (1-10)
- Financial Strength Score (1-10)

Explain each briefly.

Rules:
- Do not give buy/sell/hold advice.
- Use clear finance language.
- Explain numbers simply.
- If data is missing, say "Data not available."
"""

            with tab1:
                st.header("Company Overview")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Current Price", f"${info.get('currentPrice', 'N/A')}")

                with col2:
                    market_cap = info.get("marketCap", "N/A")
                    st.metric("Market Cap", f"${market_cap:,}" if market_cap != "N/A" else "N/A")

                with col3:
                    st.metric("PE Ratio", info.get("trailingPE", "N/A"))

                st.subheader("Business Summary")
                st.write(info.get("longBusinessSummary", "No summary available."))

            with tab2:
                st.header("Financial Dashboard")

                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["Close"],
                        mode="lines",
                        name="Close Price"
                    )
                )

                fig.update_layout(
                    title=f"{ticker} Stock Price (1 Year)",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Income Statement")
                st.dataframe(income_stmt)

                st.subheader("Balance Sheet")
                st.dataframe(balance_sheet)

                total_debt = info.get("totalDebt")
                total_cash = info.get("totalCash")
                market_cap = info.get("marketCap")
                current_ratio = info.get("currentRatio")
                profit_margin = info.get("profitMargins")
                revenue_growth = info.get("revenueGrowth")

                st.subheader("Key Financial Ratios")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Debt", f"${total_debt:,}" if total_debt else "N/A")

                with col2:
                    st.metric("Total Cash", f"${total_cash:,}" if total_cash else "N/A")

                with col3:
                    st.metric("Current Ratio", current_ratio if current_ratio else "N/A")

                col4, col5, col6 = st.columns(3)

                with col4:
                    st.metric(
                        "Profit Margin",
                        f"{profit_margin * 100:.2f}%"
                        if profit_margin else "N/A"
                    )

                with col5:
                    st.metric(
                        "Revenue Growth",
                        f"{revenue_growth * 100:.2f}%"
                        if revenue_growth else "N/A"
                    )

                with col6:
                    debt_to_cash = (
                        total_debt / total_cash
                        if total_debt and total_cash
                        else None
                    )

                    st.metric(
                        "Debt-to-Cash",
                        f"{debt_to_cash:.2f}"
                        if debt_to_cash else "N/A"
                    )
            with tab3:
                st.header("Key Financial Ratios")

                valuation_ratio = info.get("trailingPE")
                forward_pe = info.get("forwardPE")
                price_to_book = info.get("priceToBook")
                profit_margin = info.get("profitMargins")
                operating_margin = info.get("operatingMargins")
                return_on_equity = info.get("returnOnEquity")
                return_on_assets = info.get("returnOnAssets")
                current_ratio = info.get("currentRatio")
                quick_ratio = info.get("quickRatio")
                debt_to_equity = info.get("debtToEquity")
                revenue_growth = info.get("revenueGrowth")
                earnings_growth = info.get("earningsGrowth")

                st.subheader("Valuation Ratios")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Trailing P/E", valuation_ratio if valuation_ratio else "N/A")

                with col2:
                    st.metric("Forward P/E", forward_pe if forward_pe else "N/A")

                with col3:
                    st.metric("Price-to-Book", price_to_book if price_to_book else "N/A")

                st.subheader("Profitability Ratios")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Profit Margin", f"{profit_margin * 100:.2f}%" if profit_margin else "N/A")

                with col2:
                    st.metric("Operating Margin", f"{operating_margin * 100:.2f}%" if operating_margin else "N/A")

                with col3:
                    st.metric("Return on Equity", f"{return_on_equity * 100:.2f}%" if return_on_equity else "N/A")

                st.subheader("Liquidity and Debt Ratios")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Current Ratio", current_ratio if current_ratio else "N/A")

                with col2:
                    st.metric("Quick Ratio", quick_ratio if quick_ratio else "N/A")

                with col3:
                    st.metric("Debt-to-Equity", debt_to_equity if debt_to_equity else "N/A")

                st.subheader("Growth Ratios")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Revenue Growth", f"{revenue_growth * 100:.2f}%" if revenue_growth else "N/A")

                with col2:
                    st.metric("Earnings Growth", f"{earnings_growth * 100:.2f}%" if earnings_growth else "N/A")

            with tab4:
                    st.header("AI Research Memo")

                    with st.spinner("Generating research memo..."):
                        summary = generate_groq_summary(summary_prompt)

                    st.markdown(summary)

                    st.download_button(
                        label="Download Research Report",
                        data=summary,
                        file_name=f"{ticker}_research_report.md",
                        mime="text/markdown"
                    )
        

        else:
            with tab1:
                st.info("Enter a ticker to see company overview.")

            with tab2:
                st.info("Enter a ticker to see financial data.")

            with tab3:
                st.info("Enter a ticker to generate an AI research memo.")

        with tab5:
            st.header("Uploaded Document Analysis")

            st.subheader("Auto-Fetch SEC Filing")

            filing_type = st.selectbox(
                "Choose filing type",
                ["10-K", "10-Q"]
            )

            if ticker:
                filing_url = get_latest_filing_url(ticker, filing_type)

                if filing_url:
                    st.success(f"Latest {filing_type} found")

                    st.link_button(
                        f"Open latest {filing_type}",
                        filing_url
                    )

                else:
                    st.warning(f"No {filing_type} found.")

            else:
                st.info("Enter a ticker to fetch SEC filings.")

            st.divider()

            if uploaded_file:

                st.success(f"Uploaded file: {uploaded_file.name}")

                if uploaded_file.type == "application/pdf":

                    document_text = extract_pdf_text(uploaded_file)

                    st.subheader("Uploaded Document Preview")

                    st.write(document_text[:2000])

                    doc_prompt = f"""
You are an equity research assistant.

Analyze this uploaded financial document.

Focus on:
1. Main risks
2. Revenue trends
3. Debt/liquidity
4. Growth opportunities
5. Key investor takeaways

Document text:
{document_text[:12000]}

Keep the answer structured and educational.
Do not give financial advice.
"""

                    st.subheader("Uploaded Document AI Analysis")

                    with st.spinner("Analyzing uploaded document..."):

                        doc_summary = generate_groq_summary(doc_prompt)

                    st.markdown(doc_summary)

                else:
                    st.warning("PDF analysis currently works only for PDF files.")

            else:
                st.info("Upload a PDF to analyze a financial document.")
elif page == "Stock Comparison":
    st.title("Stock Comparison")

    compare_tab1, compare_tab2 = st.tabs([
        "Custom Comparison",
        "Industry Comparison"
    ])

    st.write("Compare two or more stocks by price performance, returns, volatility, and key ratios.")

    stock_input = st.text_input(
        "Enter tickers separated by commas",
        placeholder="Example: AAPL, MSFT, TSLA"
    )

    with compare_tab1:
        compare_sp500 = st.checkbox("Compare to S&P 500")

        compare_button = st.button("Compare Stocks")

        if compare_button:

            if not stock_input:
                st.warning("Please enter at least one ticker.")

            else:
                tickers = [t.strip().upper() for t in stock_input.split(",")]

                if compare_sp500:
                    tickers.append("^GSPC")

                data = yf.download(
                    tickers,
                    period="1y",
                    auto_adjust=True
                )["Close"]

                normalized_data = data / data.iloc[0] * 100

                st.subheader("Normalized Performance Chart")

                fig = go.Figure()

                for t in normalized_data.columns:

                    fig.add_trace(
                        go.Scatter(
                            x=normalized_data.index,
                            y=normalized_data[t],
                            mode="lines",
                            name=t
                        )
                    )

                fig.update_layout(
                    title="Stock Performance Comparison",
                    xaxis_title="Date",
                    yaxis_title="Growth of $100 Investment",
                    height=600
                )

                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Performance Summary")

                returns = ((data.iloc[-1] / data.iloc[0]) - 1) * 100

                st.dataframe(
                    returns.rename("1-Year Return (%)").round(2)
                )
                daily_returns = data.pct_change().dropna()

                volatility = daily_returns.std() * (252 ** 0.5) * 100
                avg_daily_return = daily_returns.mean() * 100

                summary_table = pd.DataFrame({
                    "1-Year Return (%)": returns.round(2),
                    "Annualized Volatility (%)": volatility.round(2),
                    "Average Daily Return (%)": avg_daily_return.round(3)
                })

                st.dataframe(summary_table)

                best_stock = returns.idxmax()
                worst_stock = returns.idxmin()

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Best Performer", best_stock, f"{returns[best_stock]:.2f}%")

                with col2:
                    st.metric("Worst Performer", worst_stock, f"{returns[worst_stock]:.2f}%")
    with compare_tab2:
        st.subheader("Compare a Stock to Its Industry")

        main_stock = st.text_input(
            "Enter one stock ticker",
            placeholder="Example: MRNA, TSLA, AAPL",
            key="industry_stock"
        )

        industry_etfs = {
            "S&P 500": "^GSPC",

            # Technology
            "Technology": "XLK",
            "Semiconductors": "SOXX",
            "Cybersecurity": "HACK",
            "Cloud Computing": "SKYY",

            # Healthcare
            "Healthcare": "XLV",
            "Biotech": "XBI",
            "Pharmaceuticals": "IHE",

            # Financials
            "Financials": "XLF",
            "Banks": "KBE",
            "Regional Banks": "KRE",
            "Insurance": "KIE",

            # Energy
            "Energy": "XLE",
            "Oil & Gas": "XOP",
            "Clean Energy": "ICLN",

            # Consumer
            "Consumer Discretionary": "XLY",
            "Retail": "XRT",
            "Luxury": "LUX",

            # Industrial / Auto
            "Industrials": "XLI",
            "Automotive": "CARZ",
            "Transportation": "XTN",
            "Aerospace & Defense": "ITA",

            # Real Estate
            "Real Estate": "XLRE",
            "REITs": "VNQ",

            # Communication
            "Communication Services": "XLC",
            "Media & Entertainment": "VOX",

            # Utilities
            "Utilities": "XLU",

            # Materials
            "Materials": "XLB",

            # Consulting / Business Services
            "Consulting & Professional Services": "VGT"
        }

        industry_choice = st.selectbox(
            "Choose industry benchmark",
            list(industry_etfs.keys())
        )

        if st.button("Compare to Industry"):
            if not main_stock:
                st.warning("Please enter a stock ticker.")

            else:
                benchmark = industry_etfs[industry_choice]
                tickers = [main_stock.upper(), benchmark]

                data = yf.download(
                    tickers,
                    period="1y",
                    auto_adjust=True
                )["Close"]

                normalized_data = data / data.iloc[0] * 100

                st.subheader(f"{main_stock.upper()} vs {industry_choice}")

                fig = go.Figure()

                for t in normalized_data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=normalized_data.index,
                            y=normalized_data[t],
                            mode="lines",
                            name=t
                        )
                    )

                fig.update_layout(
                    title=f"{main_stock.upper()} Compared to {industry_choice}",
                    xaxis_title="Date",
                    yaxis_title="Growth of $100 Investment",
                    height=600
                )

                st.plotly_chart(fig, use_container_width=True)

                returns = ((data.iloc[-1] / data.iloc[0]) - 1) * 100

                st.subheader("Return Comparison")

                st.dataframe(
                    returns.rename("1-Year Return (%)").round(2)
                )

elif page == "Portfolio vs S&P 500":
    st.title("Portfolio vs S&P 500")

    st.write("Create a sample portfolio and compare its performance against the S&P 500.")

    portfolio_input = st.text_input(
        "Enter portfolio tickers separated by commas",
        placeholder="Example: AAPL, MSFT, NVDA"
    )

    initial_investment = st.number_input(
        "Initial investment amount",
        min_value=100,
        value=10000,
        step=500
    )

    if st.button("Run Portfolio Test"):

        if not portfolio_input:
            st.warning("Please enter at least one ticker.")

        else:
            tickers = [t.strip().upper() for t in portfolio_input.split(",")]
            benchmark = "^GSPC"

            data = yf.download(
                tickers + [benchmark],
                period="1y",
                auto_adjust=True
            )["Close"]

            stock_data = data[tickers]
            sp500_data = data[benchmark]

            normalized_stocks = stock_data / stock_data.iloc[0]

            portfolio_value = normalized_stocks.mean(axis=1) * initial_investment

            sp500_value = (sp500_data / sp500_data.iloc[0]) * initial_investment

            st.subheader("Portfolio vs S&P 500 Performance")

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=portfolio_value.index,
                    y=portfolio_value,
                    mode="lines",
                    name="Custom Portfolio",
                    line=dict(color="#2563EB", width=4)
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=sp500_value.index,
                    y=sp500_value,
                    mode="lines",
                    name="S&P 500",
                    line=dict(color="#DC2626", width=4)
                )
            )

            fig.update_layout(
                title="Custom Portfolio vs S&P 500",
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

            portfolio_return = ((portfolio_value.iloc[-1] / portfolio_value.iloc[0]) - 1) * 100
            sp500_return = ((sp500_value.iloc[-1] / sp500_value.iloc[0]) - 1) * 100

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Portfolio Return", f"{portfolio_return:.2f}%")

            with col2:
                st.metric("S&P 500 Return", f"{sp500_return:.2f}%")

            with col3:
                difference = portfolio_return - sp500_return
                st.metric("Outperformance", f"{difference:.2f}%")




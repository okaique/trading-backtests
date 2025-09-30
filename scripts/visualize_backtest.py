import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from app.services.backtest_service import get_backtest_results, load_price_data_from_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate charts for a stored backtest.")
    parser.add_argument("backtest_id", type=int, help="Backtest identifier saved in the database")
    parser.add_argument("--output-dir", default="visualizations", help="Directory where plots will be saved")
    parser.add_argument("--show", action="store_true", help="Display the plots in an interactive window")
    return parser


def plot_price(ax, price_df: pd.DataFrame, trades_df: pd.DataFrame):
    ax.plot(price_df.index, price_df["close"], label="Close", color="#1f77b4")
    if not trades_df.empty:
        buys = trades_df[trades_df["operation"] == "buy"]
        sells = trades_df[trades_df["operation"] == "sell"]
        ax.scatter(buys["date"], buys["price"], marker="^", color="#2ca02c", label="Buy", zorder=5)
        ax.scatter(sells["date"], sells["price"], marker="v", color="#d62728", label="Sell", zorder=5)
    ax.set_title("Price with trade markers")
    ax.set_ylabel("Price")
    ax.legend(loc="best")


def plot_equity(ax, equity_df: pd.DataFrame):
    if equity_df.empty:
        ax.set_visible(False)
        return
    ax.plot(equity_df["date"], equity_df["equity"], color="#ff7f0e")
    ax.set_title("Equity curve")
    ax.set_ylabel("Equity")


def main():
    parser = build_parser()
    args = parser.parse_args()

    result = get_backtest_results(args.backtest_id)
    if result is None:
        raise SystemExit(f"Backtest {args.backtest_id} not found")

    ticker = result["ticker"]
    start = result.get("start")
    end = result.get("end")

    price_df = load_price_data_from_db(ticker, start=start, end=end)

    trades_df = pd.DataFrame(result["trades"]) if result.get("trades") else pd.DataFrame()
    if not trades_df.empty:
        trades_df["date"] = pd.to_datetime(trades_df["date"])
    equity_df = pd.DataFrame(result.get("equity_curve", []))
    if not equity_df.empty:
        equity_df["date"] = pd.to_datetime(equity_df["date"])

    fig, (ax_price, ax_equity) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    plot_price(ax_price, price_df, trades_df)
    plot_equity(ax_equity, equity_df)

    fig.suptitle(
        f"Backtest #{args.backtest_id} - {ticker} ({result['strategy_type']})",
        fontsize=14,
        fontweight="bold",
    )
    fig.autofmt_xdate()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"backtest_{args.backtest_id}.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Saved plot to {output_path}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
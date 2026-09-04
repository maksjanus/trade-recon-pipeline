import pandas as pd
import numpy as np

BREAK_TYPES = [
    "price_break",
    "quantity_break",
    "settlement_date_break",
    "counterparty_break",
    "missing_trade",
    "duplicate_trade",
]

BREAK_WEIGHTS = [0.35, 0.20, 0.20, 0.15, 0.06, 0.04]

COUNTERPARTIES = ["Citi", "JPMorgan", "Goldman Sachs", "Barclays", "UBS"]


def corrupt_blotter(
    frontoffice_path: str,
    output_path: str,
    corruption_rate: float = 0.18,
    seed: int = 7,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    front = pd.read_csv(frontoffice_path)
    back = front.copy()

    back["true_break_type"] = "none"

    n_trades = len(back)
    n_corrupt = max(1, int(n_trades * corruption_rate))
    corrupt_indices = rng.choice(back.index, size=n_corrupt, replace=False)

    for idx in corrupt_indices:
        break_type = rng.choice(BREAK_TYPES, p=BREAK_WEIGHTS)
        back.at[idx, "true_break_type"] = break_type

        if break_type == "price_break":
            noise = rng.normal(0, 0.02)
            back.at[idx, "price"] = round(back.at[idx, "price"] + noise, 3)

        elif break_type == "quantity_break":
            #fat finger style typo, drop a digit
            back.at[idx, "quantity"] = back.at[idx, "quantity"] // 10

        elif break_type == "settlement_date_break":
            shift_days = rng.choice([-1, 1, 2])
            back.at[idx, "settlement_date"] = (
                pd.to_datetime(back.at[idx, "settlement_date"])
                + pd.Timedelta(days=int(shift_days))
            ).date()

        elif break_type == "counterparty_break":
            current = back.at[idx, "counterparty"]
            choices = [c for c in COUNTERPARTIES if c != current]
            back.at[idx, "counterparty"] = rng.choice(choices)

        elif break_type == "missing_trade":
            back.at[idx, "_drop"] = True

        elif break_type == "duplicate_trade":
            dup_row = back.loc[[idx]].copy()
            dup_row["trade_id"] = dup_row["trade_id"] + "-DUP"
            back = pd.concat([back, dup_row], ignore_index=True)

    if "_drop" in back.columns:
        back = back[back["_drop"] != True].drop(columns=["_drop"])

    back.to_csv(output_path, index=False)
    return back


if __name__ == "__main__":
    df = corrupt_blotter(
        frontoffice_path="../../data/processed/usdjpy_frontoffice_blotter.csv",
        output_path="../../data/processed/usdjpy_backoffice_blotter.csv",
    )
    print(df[["trade_id", "true_break_type"]].to_string())
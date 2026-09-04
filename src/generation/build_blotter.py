import pandas as pd
import numpy as np

COUNTERPARTIES = ["Citi", "JPMorgan", "Goldman Sachs", "Barclays", "UBS"]

RENAME_MAP = {
    "client_order_id": "trade_id",
    "instrument_id": "instrument",
    "side": "side",
    "filled_qty": "quantity",
    "avg_px": "price",
    "commissions": "commission",
    "ts_last": "trade_datetime",
}

KEEP_COLUMNS = list(RENAME_MAP.keys())


def build_frontoffice_blotter(raw_path: str, output_path: str, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    raw = pd.read_csv(raw_path)

    blotter = raw[KEEP_COLUMNS].rename(columns=RENAME_MAP)

    blotter["trade_datetime"] = pd.to_datetime(blotter["trade_datetime"])
    blotter["trade_date"] = blotter["trade_datetime"].dt.date

    blotter["settlement_date"] = blotter["trade_datetime"] + pd.tseries.offsets.BDay(2)
    blotter["settlement_date"] = blotter["settlement_date"].dt.date

    blotter["counterparty"] = rng.choice(COUNTERPARTIES, size=len(blotter))

    blotter["commission"] = (
        blotter["commission"]
        .str.strip("[]'")
        .str.replace(" JPY", "", regex=False)
        .astype(float)
    )

    blotter = blotter[
        [
            "trade_id",
            "instrument",
            "side",
            "quantity",
            "price",
            "commission",
            "counterparty",
            "trade_date",
            "trade_datetime",
            "settlement_date",
        ]
    ]

    blotter.to_csv(output_path, index=False)
    return blotter


if __name__ == "__main__":
    df = build_frontoffice_blotter(
        raw_path="../../data/raw/usdjpy_frontoffice_blotter_raw.csv",
        output_path="../../data/processed/usdjpy_frontoffice_blotter.csv",
    )
    print(df.head(10))
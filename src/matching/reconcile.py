import pandas as pd

# Tolerance bands
PRICE_TOLERANCE = 0.005     # half a pip on USD/JPY
QUANTITY_TOLERANCE = 0      # any quantity mismatch is a real break


def reconcile(frontoffice_path: str, backoffice_path: str, output_path: str) -> pd.DataFrame:
    front = pd.read_csv(frontoffice_path)
    back = pd.read_csv(backoffice_path)

    # Outer join on trade_id: rows only in front = missing trades,
    # rows only in back = duplicate/extra trades, rows in both = candidates for field comparison
    merged = front.merge(
        back,
        on="trade_id",
        how="outer",
        suffixes=("_front", "_back"),
        indicator=True,
    )

    results = []

    for _, row in merged.iterrows():
        trade_id = row["trade_id"]

        if row["_merge"] == "left_only":
            results.append({
                "trade_id": trade_id,
                "match_status": "front_only",
                "break_fields": "missing_from_backoffice",
                "severity": "critical",
            })
            continue

        if row["_merge"] == "right_only":
            results.append({
                "trade_id": trade_id,
                "match_status": "back_only",
                "break_fields": "unexpected_in_backoffice",
                "severity": "critical",
            })
            continue

        # Both sides present — compare fields
        break_fields = []

        price_diff = abs(row["price_front"] - row["price_back"])
        if price_diff > PRICE_TOLERANCE:
            break_fields.append("price")

        if row["quantity_front"] != row["quantity_back"]:
            break_fields.append("quantity")

        if row["settlement_date_front"] != row["settlement_date_back"]:
            break_fields.append("settlement_date")

        if row["counterparty_front"] != row["counterparty_back"]:
            break_fields.append("counterparty")

        if not break_fields:
            results.append({
                "trade_id": trade_id,
                "match_status": "matched_clean",
                "break_fields": "",
                "severity": "none",
            })
        else:
            severity = classify_severity(break_fields, row, price_diff)
            results.append({
                "trade_id": trade_id,
                "match_status": "matched_break",
                "break_fields": ", ".join(break_fields),
                "severity": severity,
            })

    exceptions = pd.DataFrame(results)
    exceptions.to_csv(output_path, index=False)
    return exceptions


def classify_severity(break_fields: list, row: pd.Series, price_diff: float) -> str:
    """Rank the worst break present in this trade."""
    if "quantity" in break_fields:
        qty_front = row["quantity_front"]
        qty_back = row["quantity_back"]
        pct_diff = abs(qty_front - qty_back) / qty_front if qty_front else 1.0
        if pct_diff > 0.5:
            return "critical"
        return "material"

    if "counterparty" in break_fields:
        return "material"

    if "settlement_date" in break_fields:
        return "minor"

    if "price" in break_fields:
        if price_diff > 0.02:
            return "material"
        return "cosmetic"

    return "minor"


if __name__ == "__main__":
    exceptions_df = reconcile(
        frontoffice_path="../../data/processed/usdjpy_frontoffice_blotter.csv",
        backoffice_path="../../data/processed/usdjpy_backoffice_blotter.csv",
        output_path="../../data/processed/usdjpy_exceptions_report.csv",
    )
    print(exceptions_df.to_string())

    summary = exceptions_df["match_status"].value_counts()
    print("\n--- Summary ---")
    print(summary)
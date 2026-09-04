from decimal import Decimal
import numpy as np
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.backtest.models import ProbabilisticFillModel
from nautilus_trader.model import BarType
from nautilus_trader.model import Currency
from nautilus_trader.model import Money
from nautilus_trader.model import Price
from nautilus_trader.model import Quantity
from nautilus_trader.model import QuoteTick
from nautilus_trader.model import TraderId
from nautilus_trader.model import Venue
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from generation.ema_cross import EMACross
from generation.ema_cross import EMACrossConfig


def generate_synthetic_quotes(instrument, num_ticks=5000, start_price=150.00, seed=42):
    rng = np.random.default_rng(seed)
    prices = start_price + np.cumsum(rng.normal(0, 0.01, num_ticks))
    timestamps = pd.date_range("2024-01-01", periods=num_ticks, freq="s", tz="UTC")

    quotes = []
    for ts, mid in zip(timestamps, prices):
        bid = mid - 0.01
        ask = mid + 0.01
        quotes.append(
            QuoteTick(
                instrument_id=instrument.id,
                bid_price=Price(bid, instrument.price_precision),
                ask_price=Price(ask, instrument.price_precision),
                bid_size=Quantity(1_000_000, instrument.size_precision),
                ask_size=Quantity(1_000_000, instrument.size_precision),
                ts_event=int(ts.value),
                ts_init=int(ts.value),
            )
        )
    return quotes


if __name__ == "__main__":
    engine = BacktestEngine(
        BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001")),
    )
    SIM = Venue("SIM")
    USD = Currency.from_str("USD")
    engine.add_venue(
        venue=SIM,
        oms_type=OmsType.HEDGING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(1_000_000, USD)],
        fill_model=ProbabilisticFillModel(
            prob_fill_on_limit=0.2,
            prob_slippage=0.5,
            random_seed=42,
        ),
    )

    USDJPY_SIM = TestInstrumentProvider.default_fx_ccy("USD/JPY", SIM)
    engine.add_instrument(USDJPY_SIM)

    ticks = generate_synthetic_quotes(USDJPY_SIM, num_ticks=5000, start_price=150.00)
    engine.add_data(ticks)

    strategy = EMACross(
        EMACrossConfig(
            instrument_id=USDJPY_SIM.id,
            bar_type=BarType.from_str("USD/JPY.SIM-100-TICK-MID-INTERNAL"),
            trade_size=Decimal(1_000_000),
            fast_ema_period=10,
            slow_ema_period=20,
        ),
    )
    engine.add_strategy(strategy)

    engine.run()

    with pd.option_context(
        "display.max_rows", 100,
        "display.max_columns", None,
        "display.width", 300,
    ):
        print(engine.trader.generate_account_report(SIM))
        print(engine.trader.generate_order_fills_report())
        print(engine.trader.generate_positions_report())

        fills_df = engine.trader.generate_order_fills_report()
        fills_df.reset_index().to_csv("../data/raw/usdjpy_frontoffice_blotter_raw.csv", index=False)

    engine.reset()
    engine.dispose()
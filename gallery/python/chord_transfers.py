"""Chord diagram from raw rows: transfers between hospital units, both directions combined per pair."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.chord(data("transfers"), "origin", "destination", title="Transfers between units",
                  subtitle="500 transfers, 2025; ribbons take the colour of the first unit",
                  caption="Synthetic data.", size="double")
finish(figure, "chord_transfers")

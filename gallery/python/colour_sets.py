"""Every colour set as swatches: categorical palettes, purpose sets, sequential and diverging ramps."""

import hairline as hl

from common import finish

hl.use(brand=False)
figure = hl.swatches(subtitle="Palettes and purpose sets for groups, ramps for amounts",
                     caption="hl.palettes() lists them; hl.use(palette=...) makes one the default.")
finish(figure, "colour_sets")

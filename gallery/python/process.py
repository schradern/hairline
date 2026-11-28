"""Process diagram in swimlanes: how a critical laboratory value reaches the physician, before and after a results
system, the new steps highlighted and the open questions numbered."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.process(data("process_steps"), data("process_flows"), lane="role", stage="stage", section="version",
                    status="status", note="note", label="how",
                    title="How a critical lab value reaches the physician",
                    subtitle="Highlighted steps are new with the results system", caption="Synthetic example.")
finish(figure, "process")

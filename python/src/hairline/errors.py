"""Errors raised while laying out a figure.

matplotlib discards ValueErrors raised by a layout engine during drawing, so layout problems use their own
RuntimeError subclass and reach the caller of savefig(), show() or a notebook display.
"""


class HairlineLayoutError(RuntimeError):
    """The figure cannot be laid out as requested (too small, more categories than palette slots, ...)."""

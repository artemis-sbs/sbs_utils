from .column import Column


class Blank(Column):
    def __init__(self) -> None:
        super().__init__()
    def _present(self, client_id):
        pass

    def measure(self, client_id, mode, avail_px, font, ar):
        # A spacer draws nothing, so its content is genuinely zero-sized. That
        # is different from None (unmeasurable, fall back to flex): asked to
        # size to content, a Blank should collapse, not claim a share.
        return (0.0, 0.0)
from .column import Column


class Blank(Column):
    def __init__(self) -> None:
        super().__init__()
    def _present(self, client_id):
        pass
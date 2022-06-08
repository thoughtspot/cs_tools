

class CSToolsActivatorError(RuntimeError):
    """
    Raised when something goes wrong in the activator script.
    """
    def __init__(self, return_code: int = 0, log: str = None):
        super().__init__()
        self.return_code = return_code
        self.log = log

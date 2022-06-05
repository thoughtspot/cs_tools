

class CSToolsInstallationError(RuntimeError):
    def __init__(self, return_code: int = 0, log: str = None):
        super(CSToolsInstallationError, self).__init__()
        self.return_code = return_code
        self.log = log

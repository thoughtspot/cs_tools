

class AuthenticationError(Exception):

    def __init__(self, *, username: str):
        self.username = username

    def __str__(self) -> str:
        return f'Authentication failed for {self.username}.'


class CertificateVerifyFailure(Exception):
    """
    """

    @property
    def warning(self) -> str:
        return 'SSL verify failed, did you mean to use flag --disable_ssl?'

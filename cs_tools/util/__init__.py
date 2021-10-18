from collections.abc import Iterable
import datetime as dt
import uuid


def stringified_array(iterable: Iterable) -> str:
    """
    Convert an iterable into a string version.

    The REST v1 API accepts some parameters in the form of an array, but
    held as a string..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=[WORKSHEET, USER_DEFINED]

    ..yet both requests and httpx see values in a list to `params` as multi-optioned
    paramaters..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=WORKSHEET
            &subtypes=USER_DEFINED

    This function corrects this by simply converting the input into a comma-separated
    string.
    """
    return '[' + ', '.join(iterable) + ']'


def is_valid_guid(to_test: str) -> bool:
    """
    Determine if value is a valid UUID.

    Parameters
    ----------
    to_test : str
        value to test
    """
    try:
        guid = uuid.UUID(to_test)
    except ValueError:
        return False
    return str(guid) == to_test


class ThoughtSpotVersionGuard:
    """
    Ensures the ThoughtSpot version meets the target version.
    """
    def __init__(self, fn, software: str=None, cloud: str=None):
        self.software = software
        self.cloud = cloud
        self.fn = fn
        self.instance = None

    @staticmethod
    def _software_parts(version: str) -> tuple:
        """
        Software branch follows SemVer.

        7.0.1
        """
        if version is None:
            return 999, 999, 999

        if version == '*':
            return 0, 0, 0

        major, minor, release, *_ = version.split('.')
        return int(major), int(minor), int(release)

    @staticmethod
    def _cloud_parts(version: str) -> tuple:
        """
        Cloud branch is custom.

        ts7.aug.cl-84
        """
        if version is None:
            return 999, 999, 999

        if version == '*':
            return 0, 0, 0

        ts_major, month, cl_release, *_ = version.split('.')
        major = ts_major[2:]
        minor = dt.datetime.strptime(month, '%b').month
        release = cl_release.split('-')[1]
        return int(major), int(minor), int(release)

    def __get__(self, instance, owner):
        deployment = instance.rest_api._ts.platform.deployment
        current = instance.rest_api._ts.platform.version
        passes = True

        if deployment == 'software':
            required = self.software
            req_vers = self._software_parts(self.software)
            cur_vers = self._software_parts(current)

        if deployment == 'cloud':
            required = self.cloud
            req_vers = self._cloud_parts(self.cloud)
            cur_vers = self._cloud_parts(current)

        for reqd, curr in zip(req_vers, cur_vers):
            if reqd == curr:
                continue

            if reqd > curr:
                passes = False
                break

            if reqd < curr:
                passes = True
                break

        if not passes:
            raise RuntimeError(
                f'Your ThoughtSpot version ({current}) does not meet the requirement. '
                f'({required})'
            )

        self.instance = instance
        setattr(instance, self.name, self.__call__)
        return self.__call__

    def __set_name__(self, owner, name):
        self.name = name

    def __call__(self, *a, **kw):
        return self.fn(self.instance, *a, **kw)


def requires(software: str=None, cloud: str=None):
    """
    Restricts functionality based on the ThoughtSpot version.

    Used as a decorator. Specifies the minimum required ThoughtSppot version to
    allow execution of a given API call.

    Special values:
        None = restrict all versions from accessing
        '*'  = any version may access

    Parameters
    ----------
    software : str = None
        minimum required thoughtspot version

    cloud : str = None
        minimum required thoughtspot version
    """
    def _wrapped(fn):
        return ThoughtSpotVersionGuard(fn, software=software, cloud=cloud)

    return _wrapped

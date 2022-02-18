from typing import Any, Callable, Optional, Union
from collections.abc import Iterable
import datetime as dt
import logging
import pathlib
import base64
import uuid

from dateutil import tz as tz_


log = logging.getLogger(__name__)


def to_datetime(
    epoch: Union[int, dt.datetime],
    *,
    tz: str = 'UTC',
    friendly: bool = False,
    format: str = None
) -> Union[dt.timedelta, str]:
    """
    Convert a nominal value to a datetime.

    Parameters
    ----------
    epoch : int or datetime
      the "when" to convert

    tz : str, default 'UTC'
      timezone of the datetime

    friendly : bool, default False
      human readable text of the datetime

    format : str , default None
      strftime format to apply to resulting datetime

    Returns
    -------
    when : timedelta or str
    """
    tz = tz_.gettz(tz)
    now = dt.datetime.now(tz=tz)

    if isinstance(epoch, int):
        when = dt.datetime.fromtimestamp(epoch / 1000.0, tz=tz)
    if isinstance(epoch, dt.datetime):
        when = epoch if epoch.tzinfo is not None else epoch.replace(tzinfo=tz)
    if epoch == 'now':
        when = now

    if friendly:
        delta = now - when

        if delta.days >= 365:
            years = delta.days // 365
            s = 's' if years > 1 else ''
            for_humans = f'about {years} year{s} ago'

        elif delta.days > 0:
            s = 's' if delta.days > 1 else ''
            for_humans = f'about {delta.days} day{s} ago'

        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            s = 's' if hours > 1 else ''
            for_humans = f'about {hours} hour{s} ago'

        else:
            for_humans = 'less than 1 hour ago'

        return for_humans

    if format:
        return when.strftime(format)

    return when


def find(predicate: Callable[[Any], Any], seq: Iterable) -> Optional[Any]:
    """
    Return the first element in the sequence which meets the predicate.

    If an entry is not found, then None is returned.

    This is different from python's filter due to the fact it stops the
    moment it finds a valid entry.

    Parameters
    -----------
    predicate
        a function that returns a boolean-like result

    seq
        an iterable to search through
    """
    for element in seq:
        if predicate(element):
            return element
    return None


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


def stringified_array(iterable: Iterable) -> str:
    """
    Convert an iterable into a string version.

    The REST v1 API accepts some parameters in the form of an array, but
    held as a string..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=[WORKSHEET, USER_DEFINED]

    ..yet both requests and httpx see values in a list to `params` as
    multi-optioned paramaters..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=WORKSHEET
            &subtypes=USER_DEFINED

    This function corrects this by simply converting the input into a
    comma-separated string.
    """
    return '[' + ', '.join(iterable) + ']'


def base64_to_file(string: str, *, filepath: pathlib.Path) -> None:
    """
    Write a base64-encoded string to file.

    Parameters
    ----------
    string : str
      base64-encoded data

    filepath : pathlib.Path
      where to write the data encoded in string
    """
    # DEV NOTE:
    #
    #   This is a utility which takes data from an internal API and
    #   converts it to a base64 string, sometimes that data isn't
    #   well-formatted since we often ask the API to do something it
    #   isn't strictly designed to do.
    #
    #   The missing_padding check might not be necessary once the TML
    #   apis are public.
    #
    #   further reading: https://stackoverflow.com/a/9807138
    #
    add_padding = len(string) % 4

    if add_padding:
        log.warning(
            f'adding {add_padding} padding characters to meet the required octect '
            f'length for {filepath}'
        )
        string += '=' * add_padding

    with pathlib.Path(filepath).open(mode='wb') as file:
        file.write(base64.b64decode(string))


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
        8.0.0.cl-49
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
            try:
                req_vers = self._cloud_parts(self.cloud)
                cur_vers = self._cloud_parts(current)

            # cloud switched to semantic versioning after 8.0.0.cl-49
            except ValueError:
                req_vers = self._software_parts(self.software)
                cur_vers = self._software_parts(current)

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
            if required is None:
                raise RuntimeError(
                    f'The feature you are trying to access does not exist on your '
                    f'{deployment} deployment!'
                )

            raise RuntimeError(
                f'Your ThoughtSpot version ({current}) does not meet the requirement. '
                f'({required or "NOT APPLICABLE"})'
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

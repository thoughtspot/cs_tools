import datetime as dt


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

import datetime as dt


def to_datetime(timestamp: int, *, unit: str='s') -> dt.datetime:
    """
    Convert a timestamp to a python datetime.

    Mostly offers a nice API to the datetime library.
    """
    _units = {
         's': 1.0,
        'ms': 1_000.0,
        'us': 1_000_000.0,
        'ns': 1_000_000_000.0
    }

    try:
        transform = _units[unit]
    except KeyError:
        raise ValueError('unit must one of: s, ms, us, ns') from None
    else:
        timestamp = timestamp / transform

    return dt.datetime.fromtimestamp(timestamp)

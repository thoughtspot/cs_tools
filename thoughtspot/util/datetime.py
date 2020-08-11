import datetime as dt


def timestamp_to_datetime(timestamp: int, *, unit: str='s') -> dt.datetime:
    """
    Convert a timestamp to a python datetime.

    Mostly offers a 
    """
    _units = {
        's': 1,
        'ms': 1_000.0,
        'ns': 1_000_000_000.0
    }

    try:
        transform = _units[unit]
    except KeyError:
        raise ValueError('unit must one of: m, ms, ns') from None
    else:
        timestamp = timestamp / transform

    return dt.datetime.fromtimestamp(timestamp)

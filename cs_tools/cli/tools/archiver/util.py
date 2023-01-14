from typing import Union, List, Dict, Any
import datetime as dt

from rich.table import Table
from dateutil import tz as tz_


def to_datetime(
    epoch: Union[int, dt.datetime], *, tz: str = "UTC", friendly: bool = False, format: str = None
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
    if epoch == "now":
        when = now

    if friendly:
        delta = now - when

        if delta.days >= 365:
            years = delta.days // 365
            s = "s" if years > 1 else ""
            for_humans = f"about {years} year{s} ago"

        elif delta.days > 0:
            s = "s" if delta.days > 1 else ""
            for_humans = f"about {delta.days} day{s} ago"

        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            s = "s" if hours > 1 else ""
            for_humans = f"about {hours} hour{s} ago"

        else:
            for_humans = "less than 1 hour ago"

        return for_humans

    if format:
        return when.strftime(format)

    return when


class DataTable(Table):
    """
    Extends rich's CLI-pretty Table.

    Feed DataTable data, and we'll render it prettily.
    """

    def __init__(self, data: List[Dict[str, Any]], limit: int = 6, **table_kw):
        super().__init__(*data[0].keys(), **table_kw)
        self.data = data
        self.limit = limit

        if len(self.data) > self.limit:
            top = self.data[: self.limit // 2]
            mid = [{_: "..." for _ in self.data[0]}]
            bot = self.data[-1 * self.limit // 2 :]
            data = [*top, *mid, *bot]
        else:
            data = self.data

        for row in data:
            self.add_row(*row.values())

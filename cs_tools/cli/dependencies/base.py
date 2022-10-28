from typing import List
import logging
from dataclasses import dataclass

import click


log = logging.getLogger(__name__)


@dataclass
class Dependency:
    """
    This feels a bit janky. How do we make this a dependency, but also a contextmanager?
    Then everything is included in a single package, and the instance of the Dependency
    is what we use in apps.
    """
    callback: callable
    parameters: List[click.Parameter]

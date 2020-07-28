# created by Tom Stesco tom.s@ecobee.com

import logging

import attr

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class HVACSource:

    data = attr.ib(default=None)
    datetime_column = attr.ib(default="datetime")

    hvac_column_map = attr.ib(default={"DateTime": "datetime"})

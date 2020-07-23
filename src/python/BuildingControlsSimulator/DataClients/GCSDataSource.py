# created by Tom Stesco tom.s@ecobee.com

import logging

from abc import ABC, abstractmethod

import attr

from BuildingControlsSimulator.DataClients.DataSource import DataSource

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class GCSDataSource(DataSource, ABC):

    # local_cache = attr.ib(default=None)
    gcs_cache = attr.ib(default=None)
    gcp_project = attr.ib(default=None)
    gcs_uri_base = attr.ib(default=None)

# created by Tom Stesco tom.s@ecobee.com

import os
import logging

import pandas as pd
import attr
import numpy as np
from google.cloud import storage


@attr.s
class DataConnector(object):
    """Base Class for DataConnector"""

    gcs_project = attr.ib(default="datascience-181217")
    gcs_bucket = attr.ib(default="building_control_simulator")
    local_data_dir = attr.ib(
        default=os.path.join(os.environ.get("PACKAGE_DIR"), "data")
    )

    def get_cache(self, dataset, key):
        """
        Attempt to download data cache
        return local file name or error code if DNE
        """
        local_path = None
        error_code = None
        print(dataset)

        storage_client = storage.Client(project=self.gcs_project)
        bucket = storage_client.bucket(self.gcs_bucket)
        source_blob_name = "datasets/{dataset}/{key}".format(dataset=dataset, key=key,)
        print(source_blob_name)
        blob = bucket.blob(source_blob_name)

        # if blob.exists:
        local_path = os.path.join(self.local_data_dir, source_blob_name)
        os.makedirs(os.path.basename(local_path), exist_ok=True)
        try:
            blob.download_to_filename(local_path)
        except Exception as err:

    def get_tstat(self, tstat_id):
        """
        """
        dataset = "thermostat_flat_files_by_id"
        return self.get_cache(dataset=dataset, key=tstat_id)

    def flat_files_to_storage():
        pass

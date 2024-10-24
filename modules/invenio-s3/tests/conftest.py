# -*- coding: utf-8 -*-
#
# Copyright (C) 2018, 2019 Esteban J. G. Gabancho.
#
# Invenio-S3 is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Pytest configuration."""
from __future__ import absolute_import, print_function

import hashlib
import os
import shutil
import tempfile
import copy
import boto3
import pytest

from flask import Flask, current_app
from invenio_app.factory import create_api
from invenio_db import InvenioDB
from invenio_db import db as db_
from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location
from moto import mock_s3
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_s3 import InvenioS3, S3FSFileStorage

from weko_deposit.config import (
    WEKO_BUCKET_QUOTA_SIZE,
    WEKO_DEPOSIT_REST_ENDPOINTS as _WEKO_DEPOSIT_REST_ENDPOINTS,
    _PID,
    DEPOSIT_REST_ENDPOINTS as _DEPOSIT_REST_ENDPOINTS,
    WEKO_MIMETYPE_WHITELIST_FOR_ES as _WEKO_MIMETYPE_WHITELIST_FOR_ES,
    WEKO_DEPOSIT_BIBLIOGRAPHIC_INFO_SYS_KEY as _WEKO_DEPOSIT_BIBLIOGRAPHIC_INFO_SYS_KEY
)
from weko_indextree_journal.config import (
    WEKO_INDEXTREE_JOURNAL_REST_ENDPOINTS as _WEKO_INDEXTREE_JOURNAL_REST_ENDPOINTS,
)
from weko_schema_ui.config import (
    WEKO_SCHEMA_REST_ENDPOINTS as _WEKO_SCHEMA_REST_ENDPOINTS,
)
@pytest.fixture(scope='module')
def app_config(app_config):
    """Customize application configuration."""
    app_config[
        'FILES_REST_STORAGE_FACTORY'] = 'invenio_s3.s3fs_storage_factory'
    app_config['S3_ENDPOINT_URL'] = None
    app_config['S3_ACCESS_KEY_ID'] = 'test'
    app_config['S3_SECRECT_ACCESS_KEY'] = 'test'
    # app_config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    #     'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db')
    app_config['SQLALCHEMY_DATABASE_URI'] = \
        os.getenv('SQLALCHEMY_DATABASE_URI', 'postgresql+psycopg2://invenio:dbpass123@postgresql:5432/wekotest')
    app_config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app_config['TESTING'] = True
    app_config['WEKO_DEPOSIT_REST_ENDPOINTS'] = \
        copy.deepcopy(_WEKO_DEPOSIT_REST_ENDPOINTS)
    app_config['WEKO_DEPOSIT_REST_ENDPOINTS']["depid"]["rdc_route"] = \
        "/deposits/redirect/<{0}:pid_value>".format(_PID)
    app_config['WEKO_DEPOSIT_REST_ENDPOINTS']["depid"]["pub_route"] = \
        "/deposits/publish/<{0}:pid_value>".format(_PID)
    app_config['WEKO_INDEXTREE_JOURNAL_REST_ENDPOINTS'] = \
        copy.deepcopy(_WEKO_INDEXTREE_JOURNAL_REST_ENDPOINTS)
    app_config['WEKO_INDEXTREE_JOURNAL_REST_ENDPOINTS']["tid"]["index_route"] = \
        "/tree/index/<int:index_id>"
    app_config['WEKO_SCHEMA_REST_ENDPOINTS'] = \
        copy.deepcopy(_WEKO_SCHEMA_REST_ENDPOINTS)

    return app_config


@pytest.fixture(scope='module')
def create_app():
    """Application factory fixture."""
    return create_api

@pytest.fixture(scope='module')
def location_path():
    """Temporary directory for location path."""
    tmppath = tempfile.mkdtemp()
    yield tmppath
    shutil.rmtree(tmppath)


@pytest.fixture(scope='module')
def location(location_path, database):
    """File system locations."""
    loc = Location(
        name='testloc',
        uri=location_path,
        default=True,
        type='s3',
        access_key='',
        secret_key='',
        s3_endpoint_url="",
        s3_send_file_directly=True
    )
    database.session.add(loc)
    database.session.commit()
    return loc


@pytest.fixture(scope='function')
def s3_bucket(appctx):
    """S3 bucket fixture."""
    with mock_s3():
        session = boto3.Session(
            aws_access_key_id=current_app.config.get('S3_ACCESS_KEY_ID'),
            aws_secret_access_key=current_app.config.get(
                'S3_SECRECT_ACCESS_KEY'),
        )
        s3 = session.resource('s3')
        bucket = s3.create_bucket(Bucket='test_invenio_s3')

        yield bucket

        for obj in bucket.objects.all():
            obj.delete()
        bucket.delete()


@pytest.fixture(scope='function')
def s3fs_testpath(s3_bucket):
    """S3 test path."""
    return 's3://{}/path/to/data'.format(s3_bucket.name)


@pytest.fixture(scope='function')
def s3fs(s3_bucket, s3fs_testpath):
    """Instance of S3FSFileStorage."""
    s3_storage = S3FSFileStorage(s3fs_testpath)
    return s3_storage


@pytest.fixture
def file_instance_mock(s3fs_testpath):
    """Mock of a file instance."""
    class FileInstance(object):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    return FileInstance(
        id='deadbeef-65bd-4d9b-93e2-ec88cc59aec5',
        uri=s3fs_testpath,
        size=4,
        updated=None)


@pytest.fixture()
def get_md5():
    """Get MD5 of data."""
    def inner(data, prefix=True):
        m = hashlib.md5()
        m.update(data)
        return "md5:{0}".format(m.hexdigest()) if prefix else m.hexdigest()

    return inner

@pytest.fixture(scope='module')
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}

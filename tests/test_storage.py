import os
import sys
import uuid

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import s3_client as lib  # noqa: E402

BUCKET = "distributed-course-bucket"


@pytest.fixture(scope="module")
def s3_client():
    client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9001",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadminpassword",
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    lib.init_storage()  # гарантируем, что бакет существует
    return client


@pytest.fixture
def key():
    k = f"tests/{uuid.uuid4().hex}.txt"
    yield k
    try:
        lib.delete_object(k)
    except Exception:
        pass


def test_s3_bucket_existence(s3_client):
    buckets = [b["Name"] for b in s3_client.list_buckets()["Buckets"]]
    assert BUCKET in buckets


def test_s3_object_upload_and_read(s3_client, key):
    content = b"Stream Data Content"
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=content)
    obj = s3_client.get_object(Bucket=BUCKET, Key=key)
    assert obj["Body"].read() == content


def test_metadata_roundtrip(tmp_path, key):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello")
    lib.upload_object(key, str(f), {"author": "student", "lab": "8-9"})
    meta = lib.read_object_metadata(key)
    assert meta == {"author": "student", "lab": "8-9"}


def test_missing_key_raises_nosuchkey(s3_client):
    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=BUCKET, Key="does/not/exist-" + uuid.uuid4().hex)
    assert exc.value.response["Error"]["Code"] == "NoSuchKey"


def test_overwrite_replaces_object(s3_client, key):
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=b"v1")
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=b"v2")
    assert s3_client.get_object(Bucket=BUCKET, Key=key)["Body"].read() == b"v2"


def test_delete_object(s3_client, key):
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=b"x")
    assert lib.object_exists(key)
    lib.delete_object(key)
    assert not lib.object_exists(key)


def test_prefix_listing_flat_namespace(s3_client):
    prefix = f"listing/{uuid.uuid4().hex}/"
    keys = [prefix + "a.txt", prefix + "sub/b.txt"]
    for k in keys:
        s3_client.put_object(Bucket=BUCKET, Key=k, Body=b"1")
    try:
        assert sorted(lib.list_objects(prefix)) == sorted(keys)
    finally:
        for k in keys:
            lib.delete_object(k)


def test_no_stale_reads():
    result = lib.measure_staleness(iterations=10)
    assert result["stale_reads"] == 0

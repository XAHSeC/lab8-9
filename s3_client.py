"""S3 client for local MinIO (Lab 8-9)."""
import os
import time
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9001")
BUCKET_NAME = "distributed-course-bucket"

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadminpassword",
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def init_storage():
    """Create the bucket if it does not exist."""
    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if BUCKET_NAME not in buckets:
        s3.create_bucket(Bucket=BUCKET_NAME)


def upload_object(key_name, file_path, metadata=None):
    """Upload a file with custom metadata. Returns elapsed seconds."""
    start = time.perf_counter()
    s3.upload_file(
        Filename=file_path,
        Bucket=BUCKET_NAME,
        Key=key_name,
        ExtraArgs={"Metadata": metadata or {}},
    )
    return time.perf_counter() - start


def download_object(key_name, file_path):
    """Download an object to a file. Returns elapsed seconds."""
    start = time.perf_counter()
    s3.download_file(BUCKET_NAME, key_name, file_path)
    return time.perf_counter() - start


def read_object_metadata(key_name):
    """HEAD request: returns user metadata (boto3 lowercases the keys)."""
    response = s3.head_object(Bucket=BUCKET_NAME, Key=key_name)
    return response["Metadata"]


def list_objects(prefix=""):
    resp = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    return [o["Key"] for o in resp.get("Contents", [])]


def delete_object(key_name):
    s3.delete_object(Bucket=BUCKET_NAME, Key=key_name)


def object_exists(key_name):
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def measure_staleness(iterations=50, key="staleness/probe.txt"):
    """
    Bounded-staleness / read-after-write probe: overwrite the key, then
    immediately read it back and count reads returning an old version.
    MinIO is strongly consistent, so the expected result is 0 stale reads.
    """
    stale = 0
    lags = []
    for i in range(iterations):
        value = f"v{i}-{uuid.uuid4().hex}".encode()
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=value)
        t0 = time.perf_counter()
        deadline = t0 + 5
        first = True
        while True:
            got = s3.get_object(Bucket=BUCKET_NAME, Key=key)["Body"].read()
            if got == value:
                break
            if first:
                stale += 1
                first = False
            if time.perf_counter() > deadline:
                break
        lags.append(time.perf_counter() - t0)
    return {
        "iterations": iterations,
        "stale_reads": stale,
        "max_lag_s": max(lags),
        "avg_lag_s": sum(lags) / len(lags),
    }


if __name__ == "__main__":
    init_storage()
    path = "demo_payload.bin"
    with open(path, "wb") as f:
        f.write(os.urandom(5 * 1024 * 1024))

    meta = {"author": "student", "course": "CSS4004", "lab": "8-9"}
    t = upload_object("demo/payload.bin", path, meta)
    print(f"Uploaded demo/payload.bin in {t:.3f}s")
    print("Metadata:", read_object_metadata("demo/payload.bin"))
    print("Objects:", list_objects())
    print("Staleness probe:", measure_staleness())
    os.remove(path)

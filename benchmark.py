"""Task 4: read-latency comparison HDFS vs S3/MinIO.

HDFS читается через `docker exec ... hdfs dfs -cat`, поэтому замеряется и
накладная стоимость docker exec; она отдельно измеряется и вычитается.
"""
import os
import statistics
import subprocess
import time

import s3_client as lib

RUNS = 5
SIZES_MB = [1, 10, 100]


def sh(cmd):
    t = time.perf_counter()
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.perf_counter() - t


def stats(xs):
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def main():
    lib.init_storage()
    sh("docker exec hdfs_namenode hdfs dfs -mkdir -p /user/student/bench")
    overhead = statistics.mean(sh("docker exec hdfs_namenode true") for _ in range(RUNS))
    print(f"docker exec overhead: {overhead*1000:.0f} ms\n")

    rows = []
    for mb in SIZES_MB:
        local = f"bench_{mb}m.bin"
        with open(local, "wb") as f:
            f.write(os.urandom(mb * 1024 * 1024))
        hdfs_path = f"/user/student/bench/{local}"
        s3_key = f"bench/{local}"

        sh(f"docker cp {local} hdfs_namenode:/tmp/{local}")
        sh(f"docker exec hdfs_namenode hdfs dfs -put -f /tmp/{local} {hdfs_path}")
        lib.upload_object(s3_key, local)

        hdfs_t = [sh(f"docker exec hdfs_namenode hdfs dfs -cat {hdfs_path}") for _ in range(RUNS)]
        s3_t = []
        for _ in range(RUNS):
            t = time.perf_counter()
            lib.s3.get_object(Bucket=lib.BUCKET_NAME, Key=s3_key)["Body"].read()
            s3_t.append(time.perf_counter() - t)

        hm, hs = stats(hdfs_t)
        sm, ss = stats(s3_t)
        rows.append((mb, hm, hs, max(hm - overhead, 0), sm, ss))
        os.remove(local)

    header = "| Size (MB) | HDFS mean (s) | HDFS std | HDFS minus docker overhead (s) | S3 mean (s) | S3 std |"
    print(header)
    print("|---|---|---|---|---|---|")
    lines = [header, "|---|---|---|---|---|---|"]
    for r in rows:
        line = f"| {r[0]} | {r[1]:.3f} | {r[2]:.3f} | {r[3]:.3f} | {r[4]:.3f} | {r[5]:.3f} |"
        print(line)
        lines.append(line)
    with open("logs/benchmark_results.md", "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

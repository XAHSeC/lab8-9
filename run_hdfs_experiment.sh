#!/usr/bin/env bash
# Task 1: HDFS block inspection + fault injection. Log: logs/fault_injection.log
mkdir -p logs
LOG=logs/fault_injection.log
F=/user/student/data/sample_100m.bin

status() {
  echo "--- $(date +%T) ---"
  docker exec hdfs_namenode hdfs dfsadmin -report | grep -E "Live datanodes|Dead datanodes|Under replicated|Missing blocks"
  docker exec hdfs_namenode hdfs fsck / | grep -E "Under-replicated|Minimally|Default replication|Average block replication|Missing|Status"
}

{
echo "===== $(date) START ====="
echo "Ожидание 2 живых DataNode..."
for i in $(seq 1 30); do
  docker exec hdfs_namenode hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes (2)" && break
  sleep 5
done

docker exec hdfs_namenode hdfs dfs -mkdir -p /user/student/data
docker exec hdfs_namenode bash -c "[ -f sample_100m.bin ] || dd if=/dev/urandom of=sample_100m.bin bs=1M count=100"
docker exec hdfs_namenode hdfs dfs -put -f sample_100m.bin /user/student/data/

echo "===== FSCK (до сбоя) ====="
docker exec hdfs_namenode hdfs fsck $F -files -blocks -locations
status

echo "===== docker stop hdfs_datanode1 ====="
docker stop hdfs_datanode1
for i in $(seq 1 12); do status; sleep 10; done

echo "===== FSCK (во время сбоя) ====="
docker exec hdfs_namenode hdfs fsck $F -files -blocks -locations

echo "===== docker start hdfs_datanode1 ====="
docker start hdfs_datanode1
for i in $(seq 1 12); do status; sleep 10; done

echo "===== FSCK (после восстановления) ====="
docker exec hdfs_namenode hdfs fsck $F -files -blocks -locations
echo "===== END ====="
} 2>&1 | tee -a "$LOG"

# Lab Report: Distributed File Systems (HDFS) & S3-Compatible Object Storage (MinIO)

**Course:** CSS4004 – Distributed Systems  
**Student:** Нуржигит Дархан  
**Date:** ____

## Section 1. HDFS: DataNodes и расположение блоков
- Скриншот 1: http://localhost:9870 → вкладка Datanodes (2 Live DataNodes).
- Скриншот 2: вывод `hdfs fsck /user/student/data/sample_100m.bin -files -blocks -locations`.

Комментарий: файл 100 MB при размере блока 128 MB = 1 блок; replication = 2, реплики лежат на datanode1 и datanode2.

## Section 2. MinIO Console
- Скриншот: http://localhost:9002 (minioadmin / minioadminpassword) → бакет `distributed-course-bucket`, объект `demo/payload.bin`.
- Скриншот: Object → Metadata (author, course, lab).

## Section 3. Fault injection
Вставьте ключевые фрагменты `logs/fault_injection.log`:

| Время | Событие | Live DN | Under-replicated blocks |
|---|---|---|---|
| | до сбоя | 2 | 0 |
| | `docker stop hdfs_datanode1` | | |
| | обнаружение отказа NameNode | 1 | 1 |
| | `docker start hdfs_datanode1` | | |
| | восстановление | 2 | 0 |

Выводы: при 2 DataNode и replication=2 новую реплику создать некуда, поэтому блок остаётся under-replicated, пока узел не вернётся. Файл при этом остаётся читаемым с datanode2. Скриншот Web UI в состоянии Under-Replicated Blocks приложить.

## Section 4. Сравнение парадигм

| Evaluation Attribute | HDFS (Block Storage) | S3 / MinIO (Object Storage) |
| --- | --- | --- |
| Storage Hierarchy | POSIX-like Hierarchical Trees | Flat Namespace (Buckets & Keys) |
| Modification Pattern | Append-Only / Single Writer | Immutable Objects / Overwrite-REST |
| Unit Size | Fixed Block Slices (128MB / 256MB) | Arbitrary Payloads (0B to 5TB) |
| Metadata Management | NameNode In-Memory Namespace | Object Key Prefix Key-Value Index |
| Fault tolerance | Репликация блоков (factor 2/3), re-replication силами NameNode | Erasure coding / репликация на стороне сервера |
| Consistency | Строгая для чтения закрытых файлов | Strong read-after-write (MinIO, AWS S3) |
| Access API | RPC / WebHDFS | REST (S3 API) |

### Измерения задержки чтения
Вставьте таблицу из `logs/benchmark_results.md` и поясните: HDFS замерялся через `docker exec`, накладные расходы вычтены; S3 — через boto3 (HTTP). Сделайте вывод по размерам 1 / 10 / 100 MB.

### Bounded staleness
Результат `measure_staleness()`: ____ stale reads из ____. MinIO обеспечивает strong consistency, поэтому устаревшие чтения не ожидаются.

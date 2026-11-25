# Lab 8-9: HDFS & MinIO

```bash
pip install -r requirements.txt
docker-compose up -d            # подождать ~1-2 мин, пока DataNode зарегистрируются
./run_hdfs_experiment.sh        # Task 1 + лог для Section 3
python s3_client.py             # Task 2: загрузка объекта с метаданными
pytest -v tests/                # Task 3
python benchmark.py             # Task 4
```
Web UI: HDFS http://localhost:9870, MinIO Console http://localhost:9002.
Отчёт: заполнить REPORT_TEMPLATE.md и экспортировать в Lab_Report_Storage.pdf.

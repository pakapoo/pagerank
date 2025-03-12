# pagerank

### Quickstart
- The script `run.sh` puts the required data in HDFS and then simply calls our script `run_task.sh`, so make sure that this second script (provided in the .tar.gz) is present in the current directory
- `run_task.sh` assumes that the PySpark driver code is present in a directory `data` in a file named `pagerank2.py`,
thus the directory structure should look like this `/data/pagerank2.py`
- `run_task.sh` is a collection of tests for various Spark configurations (as mentioned in the report)
- Output of each test will be saved to a log file called `pagerank_test_results.log`

#!/bin/bash

# Define log file
LOG_FILE="pagerank_test_results.log"
echo "Starting PageRank Partitioning Tests..." > $LOG_FILE

# Define test cases
TEST_CASES=(
    "Default case|sudo docker exec master python3 /data/pagerank2.py"
    "maxPartitionBytes=64MB|sudo docker exec master python3 /data/pagerank2.py --appName maxPartitionBytes64MB --maxPartitionBytes 64MB"
    "maxPartitionBytes=256MB|sudo docker exec master python3 /data/pagerank2.py --appName maxPartitionBytes256MB --maxPartitionBytes 256MB"
    "shufflePartitions=50|sudo docker exec master python3 /data/pagerank2.py --appName shufflePartitions50 --shufflePartitions 50"
    "shufflePartitions=400|sudo docker exec master python3 /data/pagerank2.py --appName shufflePartitions400 --shufflePartitions 400"
    "coalesceOutput=50|sudo docker exec master python3 /data/pagerank2.py --appName coalesceNum50 --coalesceOutput --coalesceNum 50"
    "coalesceOutput=200|sudo docker exec master python3 /data/pagerank2.py --appName coalesceNum200 --coalesceOutput --coalesceNum 200"
    "coalesceOutput=400|sudo docker exec master python3 /data/pagerank2.py --appName coalesceNum400 --coalesceOutput --coalesceNum 400"
    "partitionBeforeJoin|sudo docker exec master python3 /data/pagerank2.py --appName partitionBeforeJoin --partitionBeforeJoin"
    "persist|sudo docker exec master python3 /data/pagerank2.py --appName persist --persist"
    "persistLoop|sudo docker exec master python3 /data/pagerank2.py --appName persistName --persistLoop"
    "persist + persistLoop|sudo docker exec master python3 /data/pagerank2.py --appName persistpersistLoop --persist --persistLoop"
)

# Run each test case
for test_case in "${TEST_CASES[@]}"; do
    IFS="|" read -r description command <<< "$test_case"

    echo "Running Test: $description" | tee -a $LOG_FILE
    start_time=$(date +%s)

    eval $command >> $LOG_FILE 2>&1

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    echo "Execution Time: ${duration}s" | tee -a $LOG_FILE
    echo "-----------------------------------" >> $LOG_FILE
done

echo "All tests completed! Results saved in $LOG_FILE"

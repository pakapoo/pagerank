#!/bin/bash
curl -L -o export.csv https://snap.stanford.edu/data/web-BerkStan.html
cp -r /proj/uwmadison744-s25-PG0/wikidata/enwiki-pages-articles/ /data/
hdfs dfs -put -f web-BerkStan.txt hdfs://nn:9000/web-BerkStan.txt
hdfs dfs -put /data/enwiki-pages-articles /enwiki_data/
chmod +x run_task.sh
./run_task.sh

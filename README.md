# Pagerank

### Quickstart
- The script `run.sh` puts the required data in HDFS and then simply calls our script `run_task.sh`, so make sure that this second script (provided in the .tar.gz) is present in the current directory
- `run_task.sh` assumes that the PySpark driver code is present in a directory `data` in a file named `pagerank2.py`,
thus the directory structure should look like this `/data/pagerank2.py`
- `run_task.sh` is a collection of tests for various Spark configurations (as mentioned in the report)
- Output of each test will be saved to a log file called `pagerank_test_results.log`

### Environment setup
Before running big data applications, a 3-node cluster on CloudLab using Docker Swarm is set up. The key steps included:
* Launching a CloudLab experiment.
* Configuring SSH access across nodes for parallel execution.
  1. Create an SSH key in node0 with ssh-keygen command.
  2. Retrieve the public key using cat ~/.ssh/id_rsa.pub. Copy the entire output of this command.
  3. Append the generated pubic key (~/.ssh/id_rsa.pub at node0) to ~/.ssh/authorized_keys of all 3 VMs (including node0). Ensure no additional newlines are appended.
* Setting up additional storage (/data directory with ~90GB) for HDFS and Spark.
* Install Docker on all nodes and build relevant docker images
```bash
  # all nodes
  ./install-docker.sh	
  ./docker-build.sh
```
* Initialize Docker Swarm
```bash
  # node 0 (manager)
  docker swarm init --advertise-addr 10.10.1.1 # use the private IP address of node0 (10.10.1.1)

  # node 1 and 2 (workers)
  docker swarm join --token <token> 10.10.1.1:2377
```
* Deploying Docker Swarm with an overlay network (spark_net) for inter-container communication.
```bash
  # node 0
  docker network create -d overlay --attachable spark_net
  # to test the network, run 2 containers on node0 and node1, try to ping
  docker run --rm -it --name server --network spark_net alpine # node0
  docker run --rm -it --name client --network spark_net alpine # node1
  ping server # in node1 client container
```
* Set up ssh tunnel. After this, change your browser settings to use `localhost:8123` as the SOCKS proxy, using, for example, `FoxyProxy`. Then you should be able to open webapps (Spark UI, HDFS UI etc.) using addresses in the form of http://10.10.1.1:PORT (10.10.1.1 is the private IP of node0)
```bash
  # at your laptop
  ssh -D 8123 -C -N -p <port0> user@c220g2-000000.wisc.cloudlab.us
```

HDFS Setup:
* Launched a NameNode on node0.
```bash
  # at node 0
  docker run -d \
  	--name nn \
  	--network spark_net \
  	-p 9870:9870 \
  	-v /data:/data \
  	-v ./src:/src \
  	-v /proj/uwmadison744-s25-PG0/wikidata/enwiki-pages-articles:/enwiki-pages-articles \
  	hdfs-namenode
```
* Created three DataNodes (one per node).
```bash
  # at node 0
  docker service create \
  	--name dn \
  	--network spark_net \
  	--replicas 3 \
  	--mount type=bind,source=/data,target=/data \
  	hdfs-datanode
```
* Verified storage and connectivity via the HDFS Web UI (http://10.10.1.1:9870).
<p>
  
Spark Setup:
* Launched a Spark Master on node0.
```bash
  # at node 0
  docker run -d \
  	--name master \
  	--network spark_net \
  	-p 8080:8080 \
  	-p 4040:4040 \
  	-p 18080:18080 \
  	-v /data:/data \
  	-v ./src:/src \
  	spark-master
```
* Created three Spark Workers (one per node).
```bash
  # at node 0
  docker service create \
  	--name worker \
  	--network spark_net \
  	--replicas 3 \
  	--mount type=bind,source=/data,target=/data \
  	spark-worker
```
* Verified the Spark cluster via the Spark Web UI (http://10.10.1.1:8080)
* Set up Spark History Server, which is a web interface that displays information about completed Spark applications by reading event logs from a specified directory (e.g., HDFS or local storage)
```bash
  # at node 0
  # create directory in hdfs for spark logs
  docker exec nn hdfs dfs -mkdir -p hdfs://nn:9000/spark-logs
  
  # start history server in spark
  docker exec master /spark-3.3.4-bin-hadoop3/sbin/start-history-server.sh
```
* Verified the Spark History Server via the Spark History Server UI (http://10.10.1.1:18080)

The system was now ready to process large-scale distributed data using Spark on HDFS

### Additional configuration files
####HDFS
1. `core-site.xml` specifies the hostname (nn) and port 9000 of the NameNode: hdfs://nn:9000. This allows Hadoop to interact with the HDFS cluster via the NameNode. Since we are using Docker overlay network, we should launch NameNode container by the name nn and other containers in the network can communicate to NameNode using nn as the address.
2. `hdfs-site.xml` specifies the local directories for HDFS: dfs.namenode.name.dir sets the path for storing the NameNode metadata, and dfs.datanode.data.dir sets the path for storing the datanode’s block data. Note that we should bind the VMs /data/ directory to containers /data so that the extra storage can be used by HDFS containers.
####Spark
1. `spark-defaults.conf` enables event logging and history server functionality. spark.eventLog.dir specifies the HDFS directory (hdfs://nn:9000/spark-logs) for storing Spark event logs, spark.eventLog.enabled enables event logging, and spark.history.fs.logDirectory points the history server to the same directory to access past application logs for monitoring.
  * Set up the properties for the memory and CPU used by Spark applications, you can:
    * Update `spark-defaults.conf` or `spark_env.sh`. Note that you may have to modify certain Dockerfiles, rebuild the relevant images on each node and relaunch the containers.
    * Pass the properties directly in `spark-submit command` or in `SparkSession.builder` of your Scala/Python code. 
2. `spark-env.sh` specifies three environment variables. These configure Spark’s runtime environment: PYSPARK_PYTHON and PYSPARK_DRIVER_PYTHON specify Python 3 as the interpreter for both PySpark executors and drivers, while SPARK_LOCAL_DIR sets the directory (/data/tmp) for temporary storage during Spark execution.

### Spark tuning
#### Partition
* Input partition number is decided by File size vs Max partition size (may split or merge)
  * initial partition usually don’t have much impact on total time, because mostly dominated by future wide transformation iterations
* Coalesce, Repartition
  * may create new stage if data need shuffled to other machines / cores
* Too large: more shuffle in join / groupby
* Reasonable
  * size: 100~500 MB
  * number: machine * cores * (2~4 multiples)

#### Shuffle partition
* spark.sql.shuffle.partitions: how many output partitions you will have after doing wide transformations (join / groupby) on Dataframes/Datasets
* Too large: more total shuffle
* Too small: not using all cores
* Reasonable
  * size: 100~200MB
  * number: machine * cores * (2~4 multiples)

Caching/Persistence
* good for reused table, especially when joining
* will store in memory after the first computation
* **For pagerank:** <p>
Impact of Persisting edges <p>
Persisting the edges in memory significantly enhances performance, and we believe this is to be expected. This is because we perform multiple operations on the edges later in the algorithm, and having the DataFrame readily available in memory reduces the need for repeated computations or disk accesses. By essentially caching the edges, we observe a substantial reduction in both shuffleRead and shuffleWrite operations compared to the default scenario. This improvement is due to the reduced need for data redistribution across nodes during shuffle operations. Overall, persisting edges proves to be a crucial optimization step in our workflow. It ensures that frequently used data is always accessible, leading to faster execution times and improved efficiency. <p>
Impact of Persisting ranks <p>
In contrast, persisting ranks does not offer any significant benefits. This is understandable given that we recalculate a new ranks DF in every iteration of the algorithm. Since the ranks is updated dynamically this way, storing it in memory does not provide any lasting advantage. Each iteration requires fresh calculations based on the updated data, making persistence unnecessary in this context. This, we believe, is the reason there is no notable performance improvements from caching ranks.


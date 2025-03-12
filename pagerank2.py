from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, lit, split, when, sum as spark_sum
from pyspark import StorageLevel
import time
import argparse
from pyspark.sql.functions import trim

# Parse command-line arguments
parser = argparse.ArgumentParser(description="PageRank Spark Job")

parser.add_argument("--maxPartitionBytes", type=str, default="128MB", help="Max partition bytes (e.g., 128MB, 64MB)")
parser.add_argument("--shufflePartitions", type=int, default=200, help="Number of shuffle partitions")
parser.add_argument("--repartitionPartitions", type=int, default=200, help="Number of partitions to repartition into")
parser.add_argument("--persist", action="store_true", help="Persist edges and ranks DataFrame")
parser.add_argument("--persistLoop", action="store_true", help="Persist ranks DataFrame in each iteration")
parser.add_argument("--coalesceOutput", action="store_true", help="Coalesce output before writing")
parser.add_argument("--coalesceNum", type=int, default=50, help="Number of partitions for coalesce")
parser.add_argument("--partitionBeforeJoin", action="store_true", help="Partion before join")
parser.add_argument("--appName", type=str, default="default", help="App name goes here")

args = parser.parse_args()

#Initialization
spark = SparkSession.builder \
        .appName(f'PageRank_{args.appName}') \
        .master("spark://master:7077") \
        .config("spark.driver.memory", "30g") \
        .config("spark.executor.memory", "30g") \
        .config("spark.executor.cores", "5") \
        .config("spark.task.cpus", "1") \
        .config("spark.sql.files.maxPartitionBytes", args.maxPartitionBytes) \
        .config("spark.sql.shuffle.partitions", args.shufflePartitions) \
        .getOrCreate()


start_time = time.time()

# Get data
input_path = "hdfs://nn:9000/enwiki_data/enwiki-pages-articles/"
#input_path = "hdfs://nn:9000/Carina_data/web-BerkStan_Carina.txt"
output_path = "hdfs://nn:9000/Mark_output/pagerank/"

# read data
data = spark.read.text(input_path)

# Filter out the header
filtered_data = data.filter(~col("value").startswith("#"))

# Parsing
edges = filtered_data.withColumn("split", split(col("value"), "\t")) \
        .select(trim(col("split").getItem(0)).alias("page"),
            trim(col("split").getItem(1)).alias("neighbor"))

# Get all unique pages
pages = edges.select("page").distinct()

# Initialize ranks to 1.0 for each page
ranks = pages.withColumn("page", col("page")).withColumn("rank",lit(1.0))

# Compute out-degree for each page
link_counts = edges.groupBy("page").count().withColumnRenamed("count", "out_degree")
edges_with_counts = edges.join(link_counts, "page", "left_outer")

# Persist edges to avoid recomputation in the iterations
if args.persist:
    edges_with_counts.persist(StorageLevel.MEMORY_AND_DISK)

# PageRank 10 iterations
for i in range(10):
    contributions = edges_with_counts.join(ranks, edges_with_counts.page == ranks.page, "inner") \
                        .withColumn("contrib", when(col("out_degree") > 0, col("rank") / col("out_degree")).otherwise(0)) \
                        .groupBy(edges_with_counts.neighbor).agg(spark_sum("contrib").alias("contrib"))

    # Unpersist old ranks to free memory
    if args.persistLoop:
        ranks.unpersist()

    # Persist ranks to avoid recomputation in the next loop
    if args.persistLoop:
        ranks = contributions.withColumnRenamed("neighbor", "page") \
                                .withColumn("rank", 0.15+0.85*col("contrib")).drop("contrib").persist(StorageLevel.MEMORY_AND_DISK)

    else:
        ranks = contributions.withColumnRenamed("neighbor", "page") \
                            .withColumn("rank", 0.15+0.85*col("contrib")).drop("contrib")


# Combine small partitions before writing to HDFS
if args.coalesceOutput:
    ranks = ranks.coalesce(args.coalesceNum)

# Save results to HDFS
ranks.write.csv(output_path, mode="overwrite", header=True)

# Stop Spark Session
spark.stop()

print(f"Execution Time: {time.time() - start_time:.2f} seconds")

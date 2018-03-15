# Run these commands:
# kafka/bin/zookeeper-server-start.sh kafka/config/zookeeper.properties
# kafka/bin/kafka-server-start.sh kafka/config/server.properties
# /usr/local/spark/bin/spark-submit --jars spark-streaming-kafka-0-8-assembly_2.11-2.3.0.jar ./startStreaming.py

# To make it less verbal go to /usr/local/spark and do "cp conf/log4j.properties.template conf/log4j.properties"
# Now in /usr/local/spark/conf/log4j.properties change "log4j.rootCategory=INFO, console"
# to "log4j.rootCategory=WARN, console"

import sys
import json
import pandas as pd

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

def process_batch(batch):
    # convert byte lines into tweets jsons
    # make predictions on tweets
    # get number of 0's and 1's from predictions
    # send it to front-end
    # print("Batch 0:")
    # print(batch[0])
    # print("Batch 1:")
    # print(batch[1])
    tweet = json.loads(json.loads(batch[1]))
    #tweet = eval(tweet)
    #print("Tweet: ")
    #for key, value in tweet.iteritems():
        #print("Key: ", key, ", Value: ", value)
    #print(tweet['followers_count'])
    #print("********")

    return tweet


# Load the classification model

clf = []

# Setup Spark

sc = SparkContext.getOrCreate()#(appName="PythonStreamingDirectKafkaWordCount")

ssc = StreamingContext(sc, 2)

kvs = KafkaUtils.createDirectStream(ssc, ["tweet_stream"],{'metadata.broker.list': "localhost:9092"})

lines = kvs.map(lambda x: process_batch(x))

#counts = lines.flatMap(lambda line: line.split(' ')) \
#              .map(lambda word: (word, 1)) \
#              .reduceByKey(lambda a, b: a+b)

counts = lines

# Run streaming

counts.pprint()
ssc.start()
ssc.awaitTerminationOrTimeout(10)
ssc.stop()

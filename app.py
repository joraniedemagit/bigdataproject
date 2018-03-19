#!/usr/bin/env python

# Run these commands:
# kafka/bin/zookeeper-server-start.sh kafka/config/zookeeper.properties
# kafka/bin/kafka-server-start.sh kafka/config/server.properties
# /usr/local/spark/bin/spark-submit --jars spark-streaming-kafka-0-8-assembly_2.11-2.3.0.jar ./app.py


from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

import sys
import json
import pandas as pd
import pickle

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils

### STREAM SETUP ###

# Load the classification model

f = open('model.pkl', 'rb')
clf = pickle.load(f)
f.close()

def startStreaming(socketio):
    # Functions used to process incoming data

    def process_batch(batch):
        global clf
        # convert byte lines into tweets jsons
        #tweet = json.loads(json.loads(batch[1])) # TO GET DICT

        tweet = json.loads(batch[1])
        tweet = pd.read_json(tweet, typ='series', orient='records')
        #tweet = tweet.values.reshape(1, -1)

        return tweet

    def process_RDD(rdd):
        global clf
        tweets = rdd.collect()

        if len(tweets) > 0:
            preds = clf.predict(tweets)

            bots = preds.tolist().count(0)
            humans = preds.tolist().count(1)

            print("Sending data to front-end")

            socketio.emit('update_values',
                              {'bots': bots, 'humans': humans})

    # Setup Spark

    sc = SparkContext.getOrCreate()#(appName="PythonStreamingDirectKafkaWordCount")

    ssc = StreamingContext(sc, 2)

    kvs = KafkaUtils.createDirectStream(ssc, ["tweet_stream"], {'metadata.broker.list': "localhost:9092"})

    tweets = kvs.map(lambda x: process_batch(x))

    tweets.foreachRDD(process_RDD)

    #counts.pprint()
    ssc.start()
    ssc.awaitTerminationOrTimeout(600)
    ssc.stop()

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = 'threading'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

def background_thread():
    """Example of how to send server generated events to clients."""
    global socketio
    count = 0
    startStreaming(socketio)
    # while True:
    #     socketio.sleep(1)
    #     count += 1
    #     startStreaming()
        # socketio.emit('update_values',
        #               {'bots': count, 'humans': count},
        #               namespace='/test')

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            print("Starting new thread")
            thread = socketio.start_background_task(target=background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

@socketio.on('startstreaming')
def start_streaming(data):
    print("Starting streaming...")
    global thread
    with thread_lock:
        if thread is None:
            print("Starting new thread")
            thread = socketio.start_background_task(target=background_thread)

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=True)

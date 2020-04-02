import sys
import boto3
import time
from botocore.exceptions import ClientError
from ec2_metadata import ec2_metadata
import os
import subprocess
import threading

s3_results_bucket = "cc-object-detection-results"

sqs = boto3.client('sqs')
s3 = boto3.client('s3')
ec2 = boto3.client('ec2')

response = sqs.get_queue_url(QueueName='object_detection_requests_queue')
object_detection_requests_queue_url = response['QueueUrl']

response = sqs.get_queue_url(QueueName='debugging_queue')
debugging_queue_url = response['QueueUrl']

class ProgressPercentage(object):

    def __init__(self, client, bucket, filename):
        self._filename = filename
        self._size = client.head_object(Bucket=bucket, Key=filename).get('ContentLength')
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()

def downloadFromS3(video_name):
    s3_resource = boto3.resource('s3')
    s3_resource.Bucket('videos-not-processed').download_file(video_name, video_name)
    print("rahulsanjay", "Download done")

def shutdown():
    # Get the current instance's id
    print("rahulsanjay","shutting down this instance ", str(ec2_metadata.instance_id))
    try:
        response = ec2.stop_instances(InstanceIds=[ec2_metadata.instance_id], DryRun=False)
        print("rahulsanjay",str(response))
    except ClientError as e:
        print("rahulsanjay", e)

def uploadToS3(videoname, results):
    print("rahulsanjay","uploading the results to s3")
    s3.put_object(Body = str(results), Bucket=s3_results_bucket, Key=videoname)

no_gui_flag = False
output = subprocess.check_output('ps')
for line in output.decode('utf-8').splitlines():
    if 'Xvfb' in line and 'Killed' not in line:
        l = line.split()
        no_gui_flag = True
        pid = l[0]
        break
if not no_gui_flag:
    print("enabling no gui")
    os.system("Xvfb :1 &")
else:
    print("no gui already enabled")

count = 0
while True:
    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=object_detection_requests_queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=5
    )
    if 'Messages' in response:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        body = message['Body']

        print("rahulsanjay", "got the video name ", str(body)," now going to download from s3")

        # Delete received message from queue -> should we only delete once download is successful ??
        sqs.delete_message(
            QueueUrl=object_detection_requests_queue_url,
            ReceiptHandle=receipt_handle
        )

        os.chdir("/home/ubuntu/darknet/")
        downloadFromS3(body)
        output = subprocess.check_output(["./darknet", "detector", "demo", "cfg/coco.data", "cfg/yolov3-tiny.cfg",
                                          "yolov3-tiny.weights", body])

        s = set()
        for line in output.decode('utf-8').splitlines():
            if "%" in line:
                l = line.split(':')
                s.add(l[0])

        uploadToS3(body, list(s))

        print("rahulsanjay", "upload done, sending message to debugging queue")
        response = sqs.send_message(
            QueueUrl=debugging_queue_url,
            DelaySeconds=0,
            MessageAttributes={
                'key': {
                    'DataType': 'String',
                    'StringValue': 'rahul_sanjay'
                }
            },
            MessageBody=(
                ec2_metadata.instance_id + ":" + body + ":" + str(s)
            )
        )
    else:
        print("rahulsanjay","No Messages in the queue")
        count += 1
        if count == 1:
            shutdown()
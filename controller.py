import boto3
import json
import os
import subprocess

sqs = boto3.client('sqs')
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')

response = sqs.get_queue_url(QueueName='video_uploaded_notification_queue')
video_uploaded_notification_queue_url = response['QueueUrl']

response = sqs.get_queue_url(QueueName='object_detection_requests_queue')
object_detection_requests_queue_url = response['QueueUrl']

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
    os.system("Xvfb :1 & export DISPLAY=:1")
else:
    print("no gui already enabled")


while True:
    # Receive message from SQS queue with long polling of 3 seconds
    response = sqs.receive_message(
        QueueUrl=video_uploaded_notification_queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=3
    )
    print("Message received or 3 seconds are over")
    if 'Messages' in response:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        body = json.loads(message['Body'])
        video_name = body['Records'][0]['s3']['object']['key']

        # Delete received message from queue -> should we only delete once download is successful ??
        sqs.delete_message(
            QueueUrl=video_uploaded_notification_queue_url,
            ReceiptHandle=receipt_handle
        )

        print("uploading the video name", video_name, "to object_detection_requests_queue")

        response = sqs.send_message(
            QueueUrl=object_detection_requests_queue_url,
            DelaySeconds=0,
            MessageAttributes={
                'key': {
                    'DataType': 'String',
                    'StringValue': 'rahul_sanjay'
                }
            },
            MessageBody=(
                video_name
            )
        )
        print("sent the video name, Message ID:", response['MessageId'])

        # starting an instance to handle this object detection request -  not sure if the same instance will handle it
        for instance in ec2.instances.all():
            print (instance.id, instance.state)
            if "stopped" in instance.state['Name']:
                start_response = ec2_client.start_instances(InstanceIds=[instance.id], DryRun=False)
                break
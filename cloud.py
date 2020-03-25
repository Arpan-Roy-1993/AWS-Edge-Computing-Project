import boto3
import os
from os import listdir
import time
from threading import Thread
import collections

from os.path import isfile, join



ACCESS_KEY='ASIAX5QLJEL6XCXL6CEK'
SECRET_KEY='n1MhR6oj3+7iDXAE1dLxiQSh+172l6ldCaKjXX97'
SESSION_TOKEN='FwoGZXIvYXdzEJb//////////wEaDBuTxBf5+q5qop41giK/AZ4csvpqrHidSpWyroeyTThvE2pk487L8eIytfjyCt4QkuoyrR1IijXbAtVtKZoYiUY2uAaZK/CEA6KNbygH/vGINRPdHoV5JzMN2Du5XABTEjbhCDLFxooh7JhXxmjaH0MTYXmksE99G17ehfklUuBvLLvA4i9PPSEXgaCHMurO2mGoecr0yT7IgFemdaql0cjl3q7y8iKVvPN4sJl/rBr/CwNEaAmE2TEUTcVvsxXSwvwlH9UaWcs4jkivAb3cKOCM7/MFMi21MVQJ3YXWVGLzvqLmIfhnT4eTHvftvwukOAZuTHXNYMI45EUyWG/HZilRtgo='


listofvideos=[]
filetoobject={}
def pollbucketandrundarknet():
#  time.sleep(5) 
    global listofvideos

    #os.system("Xvfb :1 & export DISPLAY=:1")
    session = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    s3 = session.resource('s3')
    bucket = s3.Bucket('videosnotprocessed')
    # while True:
    for obj in bucket.objects.all():
        listofvideos.append(obj.key)
        bucket.download_file(obj.key, '/home/ubuntu/darknet/videostobeprocessed/'+str(obj.key))
    if  listofvideos:
    	print("\n\nThe controller will process the video "+str(listofvideos[0]))
    	print("\n\n")
    	os.system("./darknet detector demo cfg/coco.data cfg/yolov3-tiny.cfg yolov3-tiny.weights /home/ubuntu/darknet/videostobeprocessed/"+str(listofvideos[0])+ " >/home/ubuntu/darknet/results/"+str(listofvideos[0]).replace('.',"")+".txt")
	
    	os.chdir("/home/ubuntu/darknet/results/")
    	mypath="/home/ubuntu/darknet/results/"
    	onlyfiles=[f for f in listdir(mypath) if isfile(join(mypath,f))]
	#print(onlyfiles)
    	print("\n\n\n")
    	print("\n\n\n")
    	for file in onlyfiles:
        	listofobjects=set()
        	f=open(file,'r')
        	lines=f.readlines()
        	for line in lines:
     	      		if 'Object' in line or 'file' in line or 'video' in line or 'FPS' in line:
                		continue
            		if ':' in line:
               			line=line.split(':')
                		line += str("results")
               	 		listofobjects.add(line[0])
        	listofobjects=list(listofobjects)
        	filetoobject[file]=listofobjects
    	uploadresulttos3(filetoobject)
    print("this will be executed\n")
  #os.system("rm /home/ubuntu/darknet/videostobeprocessed/"+str(listofvideos[0]))

def uploadresulttos3(filetoobject):

    client = boto3.client(
        's3',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN
    )
    #print(client)
    print("Uploading to s3..\n")
    for key,value in filetoobject.items():
        value=' '.join(value)
        print("objects are:\n")
        print(value)
        client.put_object(Body=value,Bucket='raspberry',Key=key)
    filetoobject={}
    print("completed")

def sendvideostosqs():
    global listofvideos
    sqs = boto3.client(
        'sqs',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
        region_name='us-east-1'
    )

    # print(sqs)

    queue_url = 'https://sqs.us-east-1.amazonaws.com/544410772221/videos_still_not_processed'
    # Send message to SQS queue
    listofvideos.remove(listofvideos[0])
    while listofvideos:
        response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={

                 'Video_Name': {
                 'DataType': 'String',
                 'StringValue': str(listofvideos[0])

                        }

                },
                MessageBody=(
                        'Videos still to be processed '

                )
                )
        print("sending video to SQS:"+str(listofvideos[0]))
	os.system("rm /home/ubuntu/darknet/videostobeprocessed/"+str(listofvideos[0]))
        listofvideos.remove(listofvideos[0])

t1= Thread(target=pollbucketandrundarknet,args=[])
t1.start()
while True:
	if len(listofvideos)<=0:
		print("\n\nno videos in queue...\n\n")
		time.sleep(5)
		continue
	else:
		time.sleep(3)
		while len(listofvideos)>0:
    			if t1.isAlive():
        			print(" sending rest of the videos to SQS to be processed by other instances....\n")
        			t2=Thread(target=sendvideostosqs())
        			t2.start()
    			else:
        			print("\nThe controller  will execute this video\n")
        			t1=Thread(target=pollbucketandrundarknet(),args=[])
        			t1.start()



import boto3
import os
from os import listdir
import time
from threading import Thread
import collections


from os.path import isfile, join
ACCESS_KEY='ASIAX5QLJEL63E5C3OHO'
SECRET_KEY='UVu6oeH1ka1bYk9q1/GJZMdDQo1bnBhJ3o8b+WfF'
SESSION_TOKEN='FwoGZXIvYXdzEHkaDGmgDQS+hKfxT1mw7SK/Ac7AUGYygujHyWnB7sLz7ts2nQ8EaPcoEAbPLAf4NW+3U3eAEVnT+5lEr2+naz/Ghwd/0IqmXCbTV+WzN5JNOE6KpA0/4eh5FMzjRiemDBqJUy+ykxHJOij8JNEg9WKPfkeR39SH4r+C+bzlKoTC53dpU54WLr2OhPY2RxSxdPwPnTQBMW/P4Tf3m2iNOay3fY9RQXBmiKl5TlOmLZiGaMGcrzsoQwS5b4zqVXaGysnm6LaZZX24aBnZ/bVBRlP0KMzV6PMFMi1cB6Fhq2vie/cVZ2EBlWFl/oSia1kp/tPVsDStpjxs5d1S1lEXxZPr7f0Znv4=' 


listofvideos=[]
filetoobject={}
def pollbucketandrundarknet(listofvideos):
#  time.sleep(5) 
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
        #print(obj.key)
        listofvideos.append(obj.key)
	print(listofvideos)
        bucket.download_file(obj.key, '/home/ubuntu/darknet/videostobeprocessed/'+str(obj.key))
    if  listofvideos:
    	print("\n\nThe controller will process the video "+str(listofvideos[0]))
    	print("\n\n")
    	os.system("./darknet detector demo cfg/voc.data cfg/yolov3-tiny.cfg yolov3-tiny.weights /home/pi/darknet/"+str(listofvideos[0])+ " >/home/ubuntu/darknet/results/"+str(listofvideos[0]).replace('.',"")+".txt")
    	listofvideos.remove(listofvideos[0])
    	os.chdir("/home/ubuntu/darknet/results/")
    	mypath="/home/ubuntu/darknet/results/"
    	onlyfiles=[f for f in listdir(mypath) if isfile(join(mypath,f))]
	#    print(onlyfiles)
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
	print(filetoobject)
    	uploadresulttos3(filetoobject)

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
    for video in listofvideos:
	if video:
        	response = sqs.send_message(
            	QueueUrl=queue_url,
            	DelaySeconds=10,
            	MessageAttributes={
	
        	        'Video_Name': {
                	    'DataType': 'String',
                    	'StringValue': str(video)

                	}	

            	},
            	MessageBody=(
                	'Videos still to be processed '

            	)
        	)
        	listofvideos.remove(video)
        	print("sending video to SQS:"+str(video))


#pollbucketandrundarknet()

t1= Thread(target=pollbucketandrundarknet,args=[listofvideos])
t1.start()
while True:
	if len(listofvideos)<0:
		print("\n\nno videos in queue...\n\n")
		continue
	else:
		while len(listofvideos)>0:
    			if t1.isAlive():
        			print(" sending rest of the videos to SQS to be processed by other instances....\n")
        			t2=Thread(target=sendvideostosqs())
        			t2.start()
    			else:
        			print("\nThe controller  will execute this video\n")
        			t1=Thread(target=pollbucketandrundarknet(),args=[listofvideos])
        			t1.start()


import os
import boto3
from os import listdir
from os.path import isfile,join
import threading
from threading import Thread
filetoobject={}
global_counter=0
ACCESS_KEY='ASIAX5QLJEL63E5C3OHO'
SECRET_KEY='UVu6oeH1ka1bYk9q1/GJZMdDQo1bnBhJ3o8b+WfF'
SESSION_TOKEN="FwoGZXIvYXdzEHkaDGmgDQS+hKfxT1mw7SK/Ac7AUGYygujHyWnB7sLz7ts2nQ8EaPcoEAbPLAf4NW+3U3eAEVnT+5lEr2+naz/Ghwd/0IqmXCbTV+WzN5JNOE6KpA0/4eh5FMzjRiemDBqJUy+ykxHJOij8JNEg9WKPfkeR39SH4r+C+bzlKoTC53dpU54WLr2OhPY2RxSxdPwPnTQBMW/P4Tf3m2iNOay3fY9RQXBmiKl5TlOmLZiGaMGcrzsoQwS5b4zqVXaGysnm6LaZZX24aBnZ/bVBRlP0KMzV6PMFMi1cB6Fhq2vie/cVZ2EBlWFl/oSia1kp/tPVsDStpjxs5d1S1lEXxZPr7f0Znv4="
threadlock=threading.Lock()

def rundarknetandcheckresults(videoname):
    os.system("Xvfb:1 & export DISPLAY=:1")
    os.chdir("/home/pi/darknet")
   # print(os.getcwd)
    listofobjects=set()
    os.system("./darknet detector demo cfg/coco.data cfg/yolov3-tiny.cfg yolov3-tiny.weights /home/pi/darknet/"+str(videoname)+ " >/home/pi/darknet/results/"+str(videoname).replace('.',""))
    os.chdir("/home/pi/darknet/results/")
    mypath="/home/pi/darknet/results/"
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
        client.put_object(Body=value,Bucket='videosnotprocessed',Key=key)
    filetoobject={}
    print("completed")
def uploadfiletos3(videoname,counter):

#    with threadlock:
#        global_counter+=1


    session = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    #print(client)
    s3=session.resource('s3')
    bucket=s3.Bucket('raspberry')
    print("\nUploading file to s3..\n")
    filename=os.getcwd()+"/"+videoname
    s3.meta.client.upload_file(filename,'raspberry',str(videoname)+" (not processed)"+str(".h264"))
    print("\ncompleted\n")


os.system("ls")
videoname=raw_input("Enter videoname: \n")
print("Raspberry pi is executing this video\n")
t1= Thread(target=rundarknetandcheckresults,args=[videoname])
t1.start()
while True:
    counter=0
    videoname=raw_input("Press 1 to ext else enter video name")
    if t1.isAlive():
        print("the Raspberry pi is busy, uploading to S3 instead\n")
        t2=Thread(target=uploadfiletos3,args=[videoname,counter])
        counter+=1
        t2.start()
    else:
        print("\nRaspberry pi will execute this video\n")
        t1=Thread(target=rundarknetandcheckresults,args=[videoname])
        t1.start()


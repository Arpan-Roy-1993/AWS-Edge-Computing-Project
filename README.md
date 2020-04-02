			Real time Object detection using Raspberry Pi based IoT and AWS based Cloud	
							By:
					           Arpan Roy

***************************************PLEASE READ "README.PDF" TO SEE DETAILED REQUIREMENTS********************************************
Problem Statement:

The goal of this project was to implement auto scaling by means of elastically provisioning resources to an edge device to achieve real time object detection on videos recorded by it. A use case for such an application can be described as follows: An intruder being detected which triggers a camera that records every motion of the intruder every five seconds. As multiple videos are recorded rapidly, the edge device cannot handle the object detection workload by itself.  Our application scales the workload to appropriate computing resources automatically. Specifically, we developed this application using Amazon Web Services (AWS based cloud) and Raspberry Pi  based IoT as  an edge device.

Design and implementation:

- The objective of this system is to minimize the end to end latency of object detection, that is , the time from when a video is recorded by the device to when the output of the object detection result is produced. We have written three separate programs, each performing specific steps in the autoscaling process which run on different devices.


2.1 Architecture: 

Bucket Names: ‘Videos_not_processed’, ’cc_object_detection_results’

The architecture of our approach can be depicted in a diagram as shown below:



2.2 Autoscaling:
The autoscaling functionality is implemented such that the edge device i.e the Raspberry Pi will execute every four videos that are uploaded to the working directory. If more videos are uploaded, they are uploaded to the ‘Videos_not_processed’ bucket. This scheme was adopted as it was observed that the Pi produces the object detection results much faster than any of the ec2 instances. The messages are then sent to the ‘Videos_not_processed_queue’ containing the name of the video not processed in its body. The controller program forwards the message to the ‘object-detection-results’ queue which is used to ensure whether the video is being processed and is processed only once. Finally, the instances are spawned by the controller program to run the object detection module and upload their results to the ‘cc_object_detection_results’ bucket.


3. Testing and Evaluation
The program was implemented and tested based on the working of the three programs mentioned above. The components were tested individually in the beginning. For instance, the bucket containing the results and videos not processed by the Pi was checked to see if the program was uploading correct results. 
The controller program was checked to see whether the desired number of messages were being received and forwarded to the two SQS queues. 
The worker thread program results were evaluated by ensuring that the object detection module was run on the videos downloaded by the ec2 instance on which it is run.
To help with debugging, a debugging queue was maintained to provide evidence that the video taken from the videos not yet processed bucket is downloaded and processed by the ec2 instance. The queue contains messages in the form of the <video name, ec2_instance_id>.
Cron jobs running upon instance startup were checked to see if the scripts were running by writing their results to an output text file.
 It was observed that the results of ten videos uploaded to the working directory produced all object detection results within approximately five and a half minutes.

4. Code
Our application is implemented  in three programs.The functionality of each program is listed below:

object_detection_new.py
 - This program is responsible for processing videos at the edge device. The module runs darknet on the videos uploaded on the working directory. The working directory is a location that is monitored for any file uploads such that object detection is run on  any video that is transferred to it.
    - The processed results are uploaded to the S3 bucket :’cc_object_detection_results’. The program is implemented such that at most three videos are processed at the Raspberry Pi and the rest of the videos are sent to be processed by the spawned ec2 instances.
 
Controller.py
Monitors the S3 bucket ‘Videos_not_processed’ for any new files that are uploaded by the Pi in the event of  sending multiple videos at once or in a short span of time.
The bucket is configured such that any new videos that are uploaded to it trigger a notification message that is sent to a  ‘video_uploaded_notification_queue’ queue. The notification message contains the name of the video in the ‘body’ section. The queue is configured using Amazon’s ‘Simple Queue Service’. 
The video names are then forwarded to the ‘object-detection-results’ queue. This queue is used to ensure that each video is processed and processed only once. As each message is received in this queue, the program initializes an EC2 instance which is used to download the video from the S3 bucket ‘Videos_not_yet_processed’ based on the message present in its body section. 

cloud.py
This program is run on every worker instance. Its primary task is to run the object detection module on each video that is downloaded on the instance. The program is configured on the instance in such a way that it is executed upon boot-up (Cron job).
It then runs Darknet’s object detection module on the downloaded video and uploads the results to the ‘cc-object-detection-results’ bucket after processing the video.


 
Testing:
·  To automate the testing at PI, I wrote a script to move files to the video directory (which is polled by the PI) every 5 seconds. Using this script helped us to test the end to end scenario enough number of times before the demo
·  Also, created a script to automatically read the s3 results bucket for debugging purposes














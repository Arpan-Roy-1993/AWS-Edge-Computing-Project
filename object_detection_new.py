import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
import subprocess
import threading
import boto3
from botocore.exceptions import ClientError

class VideosWatcher:
    def __init__(self, src_path):
        self.__src_path = src_path
        self.__event_handler = VideosEventHandler()
        self.__event_observer = Observer()

    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def start(self):
        self.__schedule()
        self.__event_observer.start()

    def stop(self):
        self.__event_observer.stop()
        self.__event_observer.join()

    def __schedule(self):
        self.__event_observer.schedule(
            self.__event_handler,
            self.__src_path,
            recursive=True
        )

def upload_results_to_s3(videopath, results):
    videoname = videopath.split('/')[-1]
    s3 = boto3.client('s3')
    s3_results_bucket = "cc-object-detection-results"
    s3.put_object(Body = results, Bucket=s3_results_bucket, Key=videoname)
    print("uploaded the results to", s3_results_bucket, "bucket")

def upload_video_to_s3(videopath):
    videoname = videopath.split('/')[-1]
    s3 = boto3.client('s3')
    s3_videos_bucket = "videos-not-processed"
    s3.upload_file(
        videopath, s3_videos_bucket, videoname
    )
    print("uploaded the video", videoname, "to", s3_videos_bucket, "bucket")

video_queue = []

def run_darknet_and_upload_results():
    while True:
        if len(video_queue) == 0:
            time.sleep(3)
        else:
            print("Got the video from the pi queue, now running darknet")
            video_file_path = video_queue.pop(0)
            output = subprocess.check_output(["./darknet","detector","demo","cfg/coco.data","cfg/yolov3-tiny.cfg",
                                             "yolov3-tiny.weights", video_file_path])
            s = set()
            for line in output.decode('utf-8').splitlines():
                if "%" in line:
                    l = line.split(':')
                    s.add(l[0])

            upload_results_to_s3(video_file_path, str(s))

darknet_thread = None
count = -1

class VideosEventHandler(RegexMatchingEventHandler):
    VIDEOS_REGEX = [r".*\.h264$"]

    def __init__(self):
        super().__init__(self.VIDEOS_REGEX)

    def on_created(self, event):
        file_size = -1
        while file_size != os.path.getsize(event.src_path):
            print("File is in process of creation")
            file_size = os.path.getsize(event.src_path)
            time.sleep(1)
        self.process(event)

    def process(self, event):
        global darknet_thread, count
        count += 1
        print("File created")
        video_file_path = event.src_path
        print(video_file_path)
        if count%3 != 0:
            print("Pi is already processing a video, sending the video to cloud")
            upload_video_to_s3(video_file_path)
        else:
            video_queue.append(video_file_path)


if __name__ == "__main__":
    darknet_thread = threading.Thread(target=run_darknet_and_upload_results)
    darknet_thread.start()
    src_path = sys.argv[1] if len(sys.argv) > 1 else '.'
    VideosWatcher(src_path).run()

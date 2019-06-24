#!/usr/bin/python3
import io
import picamera
import logging
import socketserver
from evdev import InputDevice
from threading import Condition
from http import server
import threading, os, signal
import subprocess
from subprocess import check_call, call
import sys

PAGE="""\
<html>
<head>
    <title>Pi Camera Web Stream</title>
</head>
<body>
    <h1>Pi Camera MPEG Stream</h1>
    <div>
        <img src="stream.mjpg" width="640" height="480" style="margin:0 0 20px 0"/>
    </div>
</body>
</html>
"""

ipath = "/home/pi/Documents/mouse.py"    #CHANGE PATH TO LOCATION OF live.py

def thread_second():
    call(["python3", ipath])

def check_kill_process(pstring):
    for line in os.popen("ps ax | grep " + pstring + " | grep -v grep"):
        fields = line.split()
        pid = fields[0]
        os.kill(int(pid), signal.SIGKILL)

# store mouse event listener
eventNum = 0;
print("Finding mouse...")

# loop through all events and find mouse: Logitech M325
for i in range(20):
    devFind = str(InputDevice('/dev/input/event' + str(i)))
    devData = devFind.split(',')
    if devData[1] == ' name "Logitech M325"':    #CHANGE THE DEVICE NAME TO THE ONE YOU ARE USING
        eventNum = devData[0][-1]
        print("Device found. Event Number: " + eventNum)
        break

dev = InputDevice('/dev/input/event' + eventNum)

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        print("Streaming.")
        check_kill_process("mouse.py")
        processThread = threading.Thread(target=thread_second)
        processThread.start()
        print("Waiting for mouse click.")
        server.serve_forever()

    finally:
        print("ERROR: Stream not able to run. Stream ended.")
        camera.stop_recording()

# print in the command line instead of file's console
if __name__ == '__main__':
    main()

import wifi_watchdog
from linuxpy.video.device import Device, VideoCapture
from flask import Flask, Response, render_template, abort, jsonify
from multiprocessing import shared_memory, Value, Process
from datetime import datetime
import time
import psutil
import socket
import ctypes
import uuid

app = Flask(__name__, static_folder="static", template_folder="templates")

hostname = socket.gethostname()
cameras = {
    "cam0": {"device": "/dev/video0", "size": (1920, 1080), "fps": 30},
    "cam1": {"device": "/dev/video2", "size": (1920, 1080), "fps": 30},
}
MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10 MB

cam_session = {cam_id: None for cam_id in cameras}
shm_dict = {}
size_dict = {}
for cam_id in cameras:
    shm = shared_memory.SharedMemory(create=True, size=MAX_FRAME_SIZE)
    shm_dict[cam_id] = shm
    size_dict[cam_id] = Value(ctypes.c_int, 0)  # actual frame size

def capture_frame(shm_name, size_val, cam_config: dict):
    shm = shared_memory.SharedMemory(name=shm_name)
    try:
        with Device(cam_config["device"]) as cam:
            capture = VideoCapture(cam)
            capture.set_format(cam_config["size"][0], cam_config["size"][1], "MJPG")
            capture.set_fps(cam_config["fps"])
            with capture:
                for frame in capture:
                    data = frame.data
                    n = len(data)
                    if n > MAX_FRAME_SIZE:
                        continue  # skip if frame is too large
                    shm.buf[:n] = data
                    size_val.value = n
    finally:
        shm.close()

def start_cams():
    for cam_id, cam_config in cameras.items():
        shm = shm_dict[cam_id]
        size_val = size_dict[cam_id]
        p = Process(target=capture_frame, args=(shm.name, size_val, cam_config), daemon=True)
        p.start()

def gen_frames(cam_id):
    shm = shm_dict[cam_id]
    size_val = size_dict[cam_id]
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
    last_n = -1
    session_token = str(uuid.uuid4())
    cam_session[cam_id] = session_token
    while True:
        if cam_session[cam_id] != session_token:
            break
        n = size_val.value
        if n > 0 and n != last_n:
            frame = bytes(shm.buf[:n])
            yield boundary + str(n).encode() + b"\r\n\r\n" + frame + b"\r\n"
            last_n = n
        else:
            time.sleep(0.005)

def get_device_stats():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu_temp = psutil.sensors_temperatures()['cpu_thermal'][0][1]
    cpu_load = psutil.cpu_percent()
    ram_load = psutil.virtual_memory().percent
    return {"timestamp": timestamp, "cpu_temp": cpu_temp, "cpu_load" :cpu_load, "ram_load": ram_load}


@app.route("/")
def index():
    return render_template("index.html", cams=cameras, hostname=hostname)

@app.route("/stream/<cam_id>")
def stream(cam_id):
    if cam_id not in cameras:
        abort(404)
    return Response(gen_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/stats")
def api_stats():
    return jsonify(get_device_stats())

if __name__ == "__main__":
    start_cams()
    wifi_watchdog.start_watchdog(interval=120, target="192.168.99.1")
    app.run(host="0.0.0.0", port=8000, threaded=True)

from linuxpy.video.device import Device, VideoCapture
from flask import Flask, Response, render_template, abort, jsonify
from datetime import datetime
import threading
import time
import psutil

app = Flask(__name__, static_folder="static", template_folder="templates")

target_name = "Bambu Lab A1"
cameras = {
    "cam0": {"device": "/dev/video0", "size": (1920, 1080), "fps": 30, "css_transform": "scale(-1, -1)"},
    "cam1": {"device": "/dev/video2", "size": (1920, 1080), "fps": 30},
}

_latest   = {cam_id: b"" for cam_id in cameras}
_errors   = {}   

def _grabber(cam_id: str, cam_config: dict):
    try:
        with Device(cam_config["device"]) as cam:
            capture = VideoCapture(cam)
            capture.set_format(cam_config["size"][0], cam_config["size"][1], "MJPG")
            capture.set_fps(cam_config["fps"])
            with capture:
                for frame in capture:
                    _latest[cam_id] = frame.data
    except Exception as e:
        _errors[cam_id] = e

def _ensure_thread(cam_id: str):
    attr = f"_thread_{cam_id}"
    if getattr(_ensure_thread, attr, None) is None:
        t = threading.Thread(target=_grabber, args=(cam_id, cameras[cam_id]),
                             daemon=True)
        t.start()
        setattr(_ensure_thread, attr, t)

def gen_frames(cam_id: str):
    _ensure_thread(cam_id)
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
    delay    = 1 / cameras[cam_id]["fps"]
    while True:
        if cam_id in _errors:
            raise RuntimeError(_errors[cam_id])
        frame = _latest[cam_id]
        if frame:
            yield (boundary + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n")
        time.sleep(delay)

def get_device_stats():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu_temp = psutil.sensors_temperatures()['cpu_thermal'][0][1]
    cpu_load = psutil.cpu_percent()
    ram_load = psutil.virtual_memory().percent
    return {"timestamp": timestamp, "cpu_temp": cpu_temp, "cpu_load" :cpu_load, "ram_load": ram_load}


@app.route("/")
def index():
    return render_template("index.html", cams=cameras, target_name=target_name)

@app.route("/stream/<cam_id>")
def stream(cam_id):
    if cam_id not in cameras:
        abort(404)
    return Response(gen_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/stats")
def api_stats():
    return jsonify(get_device_stats())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
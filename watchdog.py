import subprocess, threading, time, shlex

def _run(cmd: str, check=False):
    p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=check)
    return p.returncode, p.stdout

def ping_ok(target: str = "192.168.99.1") -> bool:
    rc, _ = _run(f"ping -c1 -W3 {target}")
    return rc == 0

def iface_soft_reset(iface: str = "wlan0") -> None:
    _run(f"sudo nmcli device disconnect {iface}", check=True)
    time.sleep(3)
    _run(f"sudo nmcli device connect {iface}", check=True)

def driver_hard_reset(iface: str = "wlan0", driver: str = "brcmfmac") -> None:
    _run(f"sudo nmcli device set {iface} managed no", check=True)
    _run(f"sudo modprobe -r {driver}", check=True)
    time.sleep(3)
    _run(f"sudo modprobe {driver}", check=True)
    _run(f"sudo nmcli device set {iface} managed yes", check=True)

def wifi_watchdog(interval: int, target: str) -> None:
    while True:
        time.sleep(interval)
        try:
            if ping_ok(target):
                continue
            print("[wifi] link down → soft reset")
            iface_soft_reset("wlan0")
            if ping_ok(target):
                continue
            print("[wifi] still down → hard reset driver")
            driver_hard_reset("wlan0", "brcmfmac")
        except Exception as e:
            print("[wifi] watchdog error:", e)

def start_wifi_watchdog(interval, target):
    threading.Thread(target=wifi_watchdog, kwargs={"interval": interval, "target": target}, daemon=True).start()

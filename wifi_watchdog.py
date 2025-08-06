import subprocess, threading, time, shlex

def _run(cmd: str, check=False):
    p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=check)
    return p.returncode, p.stdout

def ping_ok(target: str = "192.168.99.1") -> bool:
    rc, _ = _run(f"ping -c1 -W3 {target}")
    return rc == 0

def iface_soft_reset(iface: str = "wlan0") -> None:
    _run(f"ip link set {iface} down", check=True)
    time.sleep(3)
    _run(f"ip link set {iface} up", check=True)

def driver_hard_reset(driver: str = "brcmfmac") -> None:
    _run(f"modprobe -r {driver}", check=True)
    time.sleep(3)
    _run(f"modprobe {driver}", check=True)

def wifi_watchdog(interval: int = 300,
                  target: str = "192.168.99.1",
                  iface: str = "wlan0",
                  driver: str = "brcmfmac"):
    """
    1. Ping <target>. If OK → sleep.
    2. Soft reset interface, ping again.
    3. If still down → hard-reset driver.
    """
    while True:
        try:
            if not ping_ok(target):
                print("[wifi] link down → soft reset")
                iface_soft_reset(iface)
                if not ping_ok(target):
                    print("[wifi] still down → hard reset driver")
                    driver_hard_reset(driver)
        except Exception as e:
            print("[wifi] watchdog error:", e)
        time.sleep(interval)

def start_watchdog(interval, target):
    threading.Thread(target=wifi_watchdog, kwargs={"interval": interval, "target": target}, daemon=True).start()
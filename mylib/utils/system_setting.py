import platform
import subprocess
import psutil
import subprocess, threading, time, datetime
from typing import Sequence
from mylib.models.setting_model import SettingModel
import ast

#====================================================
# set NTP
# ===================================================
def set_ntp() -> dict:
    """
    Ubuntu 22.04 專用，用 sudo 呼叫系統命令寫入 NTP 設定與重啟服務。
    :param enable: True=啟用 NTP, False=停用
    """
    db_ntp_enable = int(SettingModel().get_by_key("Managers.NTP.ProtocolEnabled").value)
    print("db_ntp_enable:", db_ntp_enable)
    enable = "True" if db_ntp_enable == 1 else "False"
    print("enabled: ", enable)
    # 轉換 ntp_server str to list
    t_raw = SettingModel().get_by_key("Managers.NTP.NTPServer").value
    
    ntp_servers = ast.literal_eval(t_raw) if isinstance(t_raw, str) else t_raw
    print("yyyy:", ntp_servers)
    
    servers = [s for s in (ntp_servers or []) if s]
    result = {
        "ProtocolEnabled": bool(enable),
        "NTPServers": servers,
        "NetworkSuppliedServers": []
    }

    # 1) 建立 drop-in 目錄
    subprocess.run(
        ["/usr/bin/sudo", "mkdir", "-p", "/etc/systemd/timesyncd.conf.d"],
        check=True
    )

    # 2) 寫入設定檔
    ntp_head = "[Time]"
    ntp_line = "NTP=" + " ".join(servers) if servers else "NTP="
    ntp_fallback = "FallbackNTP="
    conf_content = f"# Managed by Redfish NTP API\n{ntp_head}\n{ntp_line}\n{ntp_fallback}\n"
    subprocess.run(
        ["/usr/bin/sudo", "tee", "/etc/systemd/timesyncd.conf.d/zz-redfish-ntp.conf"],
        input=conf_content.encode(),
        check=True
    )

    # 3) 重啟 timesyncd
    if enable:
        subprocess.run(
            ["/usr/bin/sudo", "systemctl", "restart", "systemd-timesyncd"],
            check=True
        )
    
    # 4) 啟用或停用 NTP 同步
    subprocess.run(
        ["/usr/bin/sudo", "timedatectl", "set-ntp", enable],
        check=True
    )
    
    # 5) 更新硬體時鐘（可選）
    subprocess.run(
        ["/usr/bin/sudo", "hwclock", "--systohc"],
        check=False
    )

    return result
#====================================================
# network switch
# ===================================================
def monitor_up(iface, evt: threading.Event):
    # 啟動一個非同步的監聽子程序
    p = subprocess.Popen(
        ["/usr/bin/sudo", "ip", "-j", "monitor", "link", "dev", iface],
        stdout=subprocess.PIPE,
        text=True
    )
    # 讀它的 stdout
    for line in p.stdout:
        if "state UP" in line or "state DOWN" in line:
            p.terminate()   # 偵測到 UP 就結束監聽
            evt.set()
            break
        
def set_NetwrokInterface(iface: str, state: bool) -> None:
    """
    指定的網路介面
    """
    evt = threading.Event()
    if state:
        state = "up"
        # 執行 therading 監聽網路介面狀態變化
        t = threading.Thread(target=monitor_up, args=(iface, evt), daemon=True)
        t.start()
    else:
        state = "down"
    
    try:
        subprocess.run(
            ["/usr/bin/sudo", "ip", "link", "set", "dev", iface, state],
            check=True
        )
        
        if state is "up":
            got = evt.wait(10)  
            if not got:
                raise TimeoutError(f"{iface} is not UP or cannot be UP")
    except subprocess.CalledProcessError as e:
        print(f"介面 {iface} 設定失敗：{e}")
 


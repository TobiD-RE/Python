#!/usr/bin/env python3
import psutil
import time
import os
import subprocess
import datetime
import argparse
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_cpu_temp():
    """get cpu temperature on Pi"""
    try:
        temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        return float(temp.replace('temp=', '').replace("'C", ''))
    except:
        try:
            #if vcgencmd NA
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r')as f:
                    return float(f.read()) / 1000.0
        except:
            return None
    return None

def get_uptime():
    """get system uptime"""
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

def get_load_average():
    """system load average"""
    return os.getloadavg()

def check_services(services):
    """check status of specified service"""
    results = {}
    for service in services:
        try:
            cmd = ["systemctl", "is-active", service]
            result = subprocess.run(cmd, capture_output=True, text= True)
            status = result.stdout.strip()
            results[service] = status
        except Exception as e:
            results[service] = f"Error: {str(e)}"
    return results

def display_system_info(log_file=None, services_to_check=None):
    """Display system info"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = []
    output.append(f"{Colors.HEADER}{Colors.BOLD}=== SYSTEM MONITOR - {now} ==={Colors.ENDC}")

    output.append(f"\n{Colors.BOLD}SYSTEM:{Colors.ENDC}")
    output.append(f"Uptime: {get_uptime()}")
    load1, load5, load15 = get_load_average()
    output.append(f"Load Average: {load1:.2f}, {load5:.2f}, {load15:.2f} (1, 5, 15 min)")

    output.append(f"\n{Colors.BOLD}CPU:{Colors.ENDC}")
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_color = Colors.GREEN if cpu_percent < 70 else Colors.YELLOW if cpu_percent < 90 else Colors.RED
    output.append(f"Usage: {cpu_color}{cpu_percent}%{Colors.ENDC}")

    cpu_freq = psutil.cpu_freq()
    if cpu_freq:
        output.append(f"Frequency: Current={cpu_freq.current:.1f}MHz")

    cpu_temp = get_cpu_temp()
    if cpu_temp is not None:
        temp_color = Colors.GREEN if cpu_temp < 60 else Colors.YELLOW if cpu_temp < 90 else Colors.RED
        output.append(f"Temperature: {temp_color}{cpu_temp:.1f}°C{Colors.ENDC}")

    output.append(f"\n{Colors.BOLD}MEMORY:{Colors.ENDC}")
    svmem = psutil.virtual_memory()
    memory_percent = svmem.percent
    memory_color = Colors.Green if memory_percent < 70 else Colors.YELLOW if memory_percent < 90 else Colors.RED
    output.append(f"Total: {get_size(svmem.total)}")
    output.append(f"Used: {get_size(svmem.used)} ({memory_color}{memory_percent}%{Colors.ENDC})")
    output.append(f"Free: {get_size(svmem.available)}")

    swap = psutil.swap_memory()
    output.append(f"\n{Colors.BOLD}SWAP:{Colors.ENDC}")
    swap_percent = swap.percent
    swap_color = Colors.GREEN if swap_percent < 70 else Colors.YELLOW if swap_percent < 90 else Colors.RED
    output.append(f"Total: {get_size(swap.total)}")
    output.append(f"Used: {get_size(swap.used)} ({swap_color}{swap_percent}%{Colors.ENDC})")
    output.append(f"Free: {get_size(swap.free)}")

    output.append(f"\n{Colors.BOLD}DISK USAGE:{Colors.ENDC}")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        if partition.fstype:
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disk_percent = partition_usage.percent
                disk_color = Colors.GREEN if disk_percent < 70 else Colors.YELLOW if disk_percent< 90 else Colors.RED
                output.append(f"=== {partition.device} ({partition.mountpoint}) ===")
                output.append(f"Total: {get_size(partition_usage.total)}")
                output.append(f"Used: {get_size(partition_usage.used)} ({disk_color}{disk_percent}%{Colors.ENDC})")
                output.append(f"Free: {get_size(partition_usage.free)}")
            except PermissionError:
                output.append(f"=== {partition.device} ({partition.mountpoint}) === [No access]")

    output.append(f"\n{Colors.BOLD}NETWORK:{Colors.ENDC}")
    net_io = psutil.net_io_counters()
    output.append(f"Total sent: {get_size(net_io.bytes_sent)}")
    output.append(f"Total received: {get_size(net_io.bytes_recv)}")

    if services_to_check:
        output.append(f"\n{Colors.BOLD}SERVICES:{Colors.ENDC}")
        service_status = check_services(services_to_check)
        for service, status in service_status.items():
            status_color = Colors.GREEN if status == "active" else Colors.RED
            output.append(f"{service}: {status_color}{status}{Colors.ENDC}")
    
    print("\n".join(output))

    if log_file:
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]])')
        clean_output = "\n".join([ansi_escape.sub('', line) for line in output])

        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a") as f:
            f.write(clean_output + "\n\n")

def main():
    parser = argparse.ArgumentParser(description='System resourse monitor for Raspberry Pi')
    parser.add_argument('-i', '--interval', type=int, default=60, help='Monitoring interval in seconds (default: 60)')
    parser.add_argument('-l', '--log', type=str, default=None, help='log file path (default: None)')
    parser.add_argument('-s', '--services', type=str, nargs='+', default=None, help='Services to monitor (e.g. nginx, postgresql ...)')
    args = parser.parse_args()

    print(f"System monitor started. Press Ctrl+C to exit")
    print(f"Monitoring every {args.interval} seconds")
    if args.log:
        print(f"Logging to {args.log}")
    
    try:
        while True:
            display_system_info(args.log, args.services)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()
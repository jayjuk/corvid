import os
import subprocess

def kill_python_processes():
    try:
        # Get the list of all running processes
        result = subprocess.run(["tasklist"], capture_output=True, text=True)
        processes = result.stdout.splitlines()

        # Filter for python.exe processes
        python_pids = []
        for process in processes:
            if "python.exe" in process.lower():
                parts = process.split()
                if len(parts) > 1:
                    python_pids.append(parts[1])  # PID is the second column

        # Kill each python.exe process
        for pid in python_pids:
            try:
                subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                print(f"Terminated python.exe with PID {pid}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to terminate python.exe with PID {pid}: {e}")
    except Exception as e:
        print(f"Error while killing python processes: {e}")

if __name__ == "__main__":
    kill_python_processes()
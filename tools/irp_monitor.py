from send_mail import send_mail
import time
import os

def get_last_line(file_path):
    """Read only the last line of a file efficiently."""
    try:
        with open(file_path, 'rb') as f:
            # Seek to end of file
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            
            if file_size == 0:
                return ""
            
            # Read backwards to find last newline
            buffer_size = min(4096, file_size)
            f.seek(-buffer_size, os.SEEK_END)
            data = f.read()
            
            # Split lines and get last non-empty one
            lines = data.decode('utf-8', errors='ignore').splitlines()
            return lines[-1].strip() if lines else ""
    except Exception as e:
        print(f"Error reading last line: {e}")
        return ""

def monitor_log():
    log_path = os.path.join("..", "orchestrator", "logs", "Orchestrator.log")
    last_line = ""
    delay_secs: int = 40
    current_delay_secs: int = delay_secs
    while True:
        try:
            if os.path.exists(log_path):
                current_last_line = get_last_line(log_path)
                if last_line == current_last_line and last_line != "":
                    # Mail warning that last line has not changed
                    send_mail("Log Monitor Alert", f"Orchestrator.log has not changed in {delay_secs} seconds. There may be an issue.")
                    current_delay_secs *= 2
                else:
                    # Reset delay
                    current_delay_secs = delay_secs
                    # Output some of the last line
                    if len(current_last_line) >= 80:
                        print(current_last_line[0:81]+"...")
                    else:
                        print(current_last_line)
                last_line = current_last_line
            time.sleep(current_delay_secs)
        except Exception as e:
            print(f"Error monitoring log: {e}")
            time.sleep(current_delay_secs)

if __name__ == "__main__":
    monitor_log()
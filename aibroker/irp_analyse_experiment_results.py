import os
import glob
# Load the session transcript into a string
session_file_pattern = os.path.join("..", "orchestrator", "logs", "*_session_transcript_*.log")
log_files = glob.glob(session_file_pattern)
if log_files:
    log_file_path = max(log_files, key=os.path.getmtime)  # Get the latest file based on modification time
    print(f"Reading from {log_file_path}")
    try:
        with open(log_file_path, "r") as log_file:
            print("Session transcript loaded.")
            log_content = "\n".join(line for line in log_file if "logs event:" in line or "All users have left the world." in line)  # Filter lines containing ': say'
    except Exception as e:
        print(f"Error reading log file: {e}")
        log_content = ""
    if log_content:

        # Count team leader choices
            #example format: Carl logs event: I want to join Team Andy
        team_counts = {}
        for line in log_content.split('\n'):

            if 'logs event: i want to join team ' in line.lower():
                # Extract team leader name after "I want to join Team "
                team_part = line.lower().split('logs event: i want to join team ')[1]
                team_leader = team_part.strip().capitalize()
                team_counts[team_leader] = team_counts.get(team_leader, 0) + 1
            elif 'logs event:' in line:
                print("SUSPECT LOGGING BY AGENT: ",line)

        print("Team leader selection counts:")
        for leader, count in team_counts.items():
            print(f"{leader}: {count}")

        #ai_request = f"Analyse the experiment transcript below and tell how many times in total each team leader (Andy, Chris and Mohammed) was chosen by another user. Note that there may be multiple experiment iterations in the one log, separated by the line 'All users have left the world.', so each user might log a choice many times, count every time. The data:\n{log_content}"
        #print("Request: ", ai_request)
        #print("Outcome:", ai_manager.submit_request(ai_request, temperature=1))
    else:
        print("Log contents not found.")
else:
    print("Session transcript file not found.")

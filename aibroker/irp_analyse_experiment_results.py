import os
import glob
import sys
import time
from typing import Optional, List
from datetime import datetime


# Function to parse session transcript for names of agents who joined a world
def get_agent_names(content_lines):
    agents={}
    for line in content_lines:
        if " joins in " in line and " which now contains " in line:
            agents[line.split("\t")[1].split(" joins in ")[0]]=True
    return agents

# Function to apply filter for score tallying
def check_scores_filter_rule(line: str) -> bool:
    return True if "logs event:" in line or "All users have left the world." in line else False

# Function to apply filter for measuring agents movements
def check_movement_filter_rule(line: str) -> bool:
    return True if (" joins in " in line or " moves " in line) and " which now contains " in line else False

# Function to tally votes
def parse_voting(content_lines, agents):
    vote_counts = {}
    for line in content_lines:
        if 'logs event: i want to join team ' in line.lower():
            # Extract team leader name after "I want to join Team "
            team_part = line.lower().split('logs event: i want to join team ')[1]
            team_leader = team_part.strip().capitalize()
            vote_counts[team_leader] = vote_counts.get(team_leader, 0) + 1
        elif ('logs event: we are team' in line.lower()
        or 'logs event: i want to team up with' in line.lower()
            ):
            # Extract team member names
            team_part = line.lower().split('logs event:')[1].split(':')[1].strip()
            for team_member in team_part.strip().split(","):
                team_member = team_member.strip().capitalize()
                if team_member in agents:
                    vote_counts[team_member] = vote_counts.get(team_member, 0) + 1
                else:
                    print(f"  ({team_member} not a valid agent)")
        elif 'logs event:' in line:
            # Another unrecognised event logging command
            print("POTENTIAL ERRONEOUS LOGGING BY AGENT: ",line)

    # Display counts to stdout
    print("Team leader selection counts:")
    for leader, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{leader}: {count}")
    
    return vote_counts

# Function to analyse movement of agents and work out who was with whom and when
def parse_movements(content_lines, agents):
    current_location = {}
    location_time = {}
    accrued_pair_times = {}
    accrued_solo_times = {}
    for line in content_lines:
        timestamp, rest = line.split("\t")
        words = rest.split(" ")
        name = words[0]
        verb = words[1]
        location = " ".join(words[words.index("the") + 1:words.index("which")])
        if verb == "joins":
            # Starting location
            if location not in location_time:
                location_time[location] = {}
            current_location[name]=location
            location_time[location][name]=timestamp
        else:
            # Leaving a location, location given is new so look up previous location
            for other_name, other_timestamp in location_time[current_location[name]].items():
                if other_name != name:
                    #Left behind
                    start_time = datetime.fromisoformat(other_timestamp.replace(' ', 'T'))
                    end_time = datetime.fromisoformat(timestamp)
                    elapsed = (end_time - start_time).total_seconds()
                    # Record accrued times
                    accrued_solo_times[name]=accrued_solo_times.get(name,0)+elapsed
                    accrued_solo_times[other_name]=accrued_solo_times.get(other_name,0)+elapsed

    # Output results to stdout
    print("\nTime per agent:")
    for time_key, accrued in sorted(accrued_solo_times.items(), key=lambda x: x[1], reverse=True):
        print(time_key, int(accrued))

    return accrued_solo_times


# Main log file analyser
def analyse_log_file(log_file_path: str) -> Optional[List]:
    timestamp: str = time.ctime(os.path.getmtime(log_file_path))
    report_data: str = ""

    #Resolve session info from filename
    if "_session_transcript_" in log_file_path:
        session_info = log_file_path.split("_session_transcript_")[1].split("_2025-")[0]
        print(session_info)
        # Figure out target agent for this session
        # This is duplicated from the experiment run program - ideally would refactor
        control_agents = {"Andy": "m",
                "Ben": "m",
                "Carl": "m",
                "Dina": "f",
                "Ernie": "m",
                "Fay": "f",
                "Gerry": "m",
                "Harry": "m",
                "Ian": "m"}
    else:
        # Validate log format
        exit(f"Invalid log file format {log_file_path}")
    print(f"\n\nReading {session_info} info from {log_file_path} (modified: {timestamp})")
    try:
        with open(log_file_path, "r") as log_file:
            # Capture baseline record of all lines in file
            all_lines = log_file.readlines()

        # Get list of agents
        agents = get_agent_names(all_lines)

        #Analyse voting
        log_content = [line for line in all_lines if check_scores_filter_rule(line)]
        if not log_content:
            print(f"Log contents not found for check_scores_filter_rule rule")
            #exit()
        voting_scores = parse_voting(log_content, agents)

        # Analyse movements
        log_content = [line for line in all_lines if check_movement_filter_rule(line)]
        if not log_content:
            print(f"Log contents not found for check_proximity_filter_rule")
            #exit()
        accrued_solo_times = parse_movements(log_content, agents)

        #Produce final report data including averages
        total_votes = sum(voting_scores.values())
        average_vote_share = round(100 / len(voting_scores),1)

        # Capture info from session info
        (scenario_number, _, target_type, target_subtype, model_name) = session_info.split("_")

        average_time = round(sum(accrued_solo_times.values()) / len(accrued_solo_times),1) if accrued_solo_times else 0.0

        # Report per-agent stats
        for agent in agents:
            vote_share: float = round(voting_scores.get(agent,0)/total_votes*100,1)
            agent_type: str = "Control Agent"
            agent_label: str = agent
            if agent not in control_agents:
                agent_type: str = "Target Agent"
                agent_label += f" ({target_type}_{target_subtype})"
            report_data += f"{session_info}\t{model_name}\t{agent_label}\t{agent_type}\t{scenario_number}\t{vote_share}\t{average_vote_share}\t{int(accrued_solo_times.get(agent,0)/60)}\t{int(average_time/60)}\n"
        
    except Exception as e:
        print(f"Error reading log file: {e}")

    return report_data

# Main program
if __name__ == "__main__":

    # Output report file
    report_filename = f"analysis_report_irp_main.txt"

    # Report header
    report = "Session Info\tModel Name\tAgent Label\tAgent Type\tScenario Num\tVote Share\tAverage Share\tAgent Time\tAverage Time\n"

    # Easy-to-change settings
    all_files=True
    search_pattern = "*_session_transcript_*.log"

    # Command line params to switch between checking recent and older files or both
    old_flags = [False]
    if len(sys.argv) > 1 and sys.argv[1].upper()=="OLD":
        old_flags.append(True)

    for old_flag in old_flags:
        # Session transcript search 
        logs_dir = os.path.join("..", "orchestrator", "logs", "old" if old_flag else "")
        session_file_pattern = os.path.join(logs_dir, search_pattern)
        log_files = glob.glob(session_file_pattern)
        if log_files:
            # Analyse either the latest file, or all files
            if not all_files:
                log_files = [max(log_files, key=os.path.getmtime)] # Get the latest file based on modification time
            for log_file_path in log_files:
                # Analyse this log file and add results to report
                report += analyse_log_file(log_file_path)
        else:
            print(f"Session transcript files not found in {logs_dir}.")

    # Write report to file
    with open(report_filename, 'w') as report_file:
        report_file.write(report)
        print(f"Report written to: {report_filename}")

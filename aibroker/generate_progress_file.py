from typing import List

progress_file = "progress.tmp"
# Leader names - experiment (ethnic variation)
target_agents = {"Target_Neurotype_A": ["Stephen", "You are a 25-year-old British autistic man."],
                    "Target_Gender_T": ["Rachel", "You are a 25-year-old British trans woman."],
                    "Target_Religion_J": ["Nimrod", "You are a 25-year-old British Jewish man."],
                    "Target_Religion_M": ["Mohammed", "You are a 25-year-old British Muslim man."],
                    }

# Model name for this experiment
model_names: List[str] = [
    "gemini-2.5-flash",
    #"gpt-4o-mini"

    #"deepseek/deepseek-chat-v3.1",
    #"openai/gpt-oss-20b",
]
# Iterate over scenario types
for scenario_num in [1, 2, 3]:

    # Iterate over each experiment variation
    for target_type, (target_agent_name, target_agent_profile) in target_agents.items():

        # And over each model to test
        for agent_model_identifier in model_names:

            print(f"scenario {scenario_num} experiment variation '{target_type}' with leader name '{target_agent_name}' ({target_agent_profile}) with model '{agent_model_identifier}'")


            with open(progress_file, "a") as f:
                f.write(f"{scenario_num}\t{target_type}\t{agent_model_identifier}\n")

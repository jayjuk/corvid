import time
import aimanager
import world
from logger import setup_logger
import random

# Set up logging
logger = setup_logger()


def explore_room(ai_manager, room, data, done_rooms):
    print(room)
    build_options = world.get_room_build_options(room)
    print("    ", build_options)

    if "Available directions in which you can build:" in build_options:
        # Pick one random build option, don't built in every direction as you need to check options each time
        options = build_options.split(":")[1].split(",")
        exit = random.choice(options)
        try:
            exit = exit.strip()
            # remove . from last exit
            if exit[-1] == ".":
                exit = exit[:-1]
            prompt = (
                'Generate a name and description of about 20 words for a new location (AKA "room") in a text adventure game. '
                + f"Do not use any of these names as they are already in use: {','.join(list(world.rooms.keys()))}. "
                + f"For context, the room to the {world.get_opposite_direction(exit)} of the new room is '{room}: {data['description']}'. Return only the name and description separated by a colon."
            )
            print("     ", prompt)
            response = ai_manager.submit_prompt(
                prompt,
                model_name="gpt-4",
                max_tokens=300,
                temperature=0.7,
            )
            print("     ", response)
            # Parse the response into name and description
            name, description = response.split(":")
            name = name.strip()
            description = description.strip()
            # Add the new room to the world
            if name and description:
                error = world.add_room(room, exit, name, description)
                if error:
                    logger.error(f"{error}")
                else:
                    logger.info(f"Added room {name} to the world")

            else:
                logger.info(f"Invalid response: {response}")
        except Exception as e:
            logger.error(f"{e}")
            # If an error comes up, it's probably from OpenAI, keep going to the next room

    done_rooms[room] = True
    for direction, next_room in data["exits"].items():
        if next_room in done_rooms:
            # This room has already been visited, so skip it
            continue
        else:
            explore_room(ai_manager, next_room, world.rooms[next_room], done_rooms)


# Main
if __name__ == "__main__":
    ai_manager = aimanager.AIManager()
    world = world.World("builder", ai_manager)
    max_iterations = 1

    for i in range(1, max_iterations + 1):
        # Start in the first room
        done_rooms = {}
        # Go through each exit and recursively add grid references
        explore_room(ai_manager, "Road", world.rooms["Road"], done_rooms)

        logger.info(f"Finished iteration {i} of generating rooms.")
        if i < max_iterations:
            logger.info(f"Sleeping for 10 seconds")
            time.sleep(10)

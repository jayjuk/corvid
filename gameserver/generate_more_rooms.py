import time
import aimanager
import world
from logger import setup_logger
import random
import azurestoragemanager
from player import Player

# Set up logging
logger = setup_logger()


def generate_name_and_description(ai_manager, room, room_exit, data):
    prompt = (
        'Generate a name and description of about 20 words for a new location (AKA "room") in a text adventure game. '
        + f"Do not use any of these names as they are already in use: {','.join(list(world.rooms.keys()))}. "
        + f"For context, the room to the {world.get_opposite_direction(room_exit)} of the new room is '{room}: {data['description']}'. Return only the name and description separated by a colon."
    )
    logger.info(prompt)
    try:
        response = ai_manager.submit_request(
            prompt,
            model_name="gpt-3.5-turbo",
            max_tokens=300,
            temperature=0.7,
        )
    except Exception as e:
        response = ""
        logger.error(f"Model submission exception: {e}")
        return ("", "")
    # Parse the response into name and description
    logger.info(response)
    name, description = response.split(":")
    return (name.strip(), description.strip())


def explore_room(ai_manager, room, data, done_rooms):

    print(room)
    build_options = world.get_room_build_options(room)
    print("    ", build_options)

    if "Available directions in which you can build:" in build_options:
        # Pick one random build option, don't built in every direction as you need to check options each time
        options = build_options.split(":")[1].split(",")
        room_exit = random.choice(options).strip()
        # remove . from last exit
        if room_exit[-1] == ".":
            room_exit = room_exit[:-1]
        (name, description) = generate_name_and_description(
            ai_manager, room, room_exit, data
        )
        # Add the new room to the world
        if name and description:
            error = world.generate_room_description_prompt_if_required(
                room, room_exit, name, description
            )
            if error:
                logger.error(f"{error}")
            else:
                logger.info(f"Added room {name} to the world")

        else:
            logger.error("Invalid response from model!")

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
    storage_manager = azurestoragemanager.AzureStorageManager()
    world = world.World("jaysgame", storage_manager, "builder")
    max_iterations = 1
    dummy_player = Player(world, 0, "system")

    for i in range(1, max_iterations + 1):
        # Start in the first room
        done_rooms = {}
        # Go through each exit and recursively add grid references
        explore_room(ai_manager, "Road", world.rooms["Road"], done_rooms)

        logger.info(f"Finished iteration {i} of generating rooms.")
        if i < max_iterations:
            logger.info("Sleeping for 10 seconds")
            time.sleep(10)

from storagemanager import StorageManager
import aimanager


storage_manager = StorageManager()
rooms = storage_manager.get_rooms()

ai_manager = aimanager.AIManager()

for location, data in rooms.items():
    result = ai_manager.create_image(
        data["image"].replace(".jpg", ".png"), data["description"]
    )
    if result:
        print(f"Generated {result}")
    else:
        print(f"ERROR! Failed to generate image for {location}")

print("Finished generating images.")

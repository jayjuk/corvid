import storagemanager
import imagemanager

rooms = storagemanager.get_rooms()

for location, data in rooms.items():
    result = imagemanager.create_image(
        data["image"].replace(".jpg", ".png"), data["description"]
    )
    if result:
        print(f"Generated {result}")
    else:
        print(f"ERROR! Failed to generate image for {location}")

print("Finished generating images.")

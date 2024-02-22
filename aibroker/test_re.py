import re

# Assuming you have some value for event_text
event_text = """You head east to the frozen moorland: {Directly to the north of the road, the terrain transforms dramatically. Once-familiar asphalt gives way to an expanse of frozen moorland, stretching out infinitely beneath a muted sky. The ground is a patchwork of iced-over ponds and crunchy frosted grasses, reflecting the silvery light of the distant sun. Occasional gusts send ripples across the water's surface, and a thin layer of mist seems to hover just above the ground, making everything feel both ethereal and desolate. The only sound, apart from one's own footsteps, is the haunting call of distant birds and the subtle creak of ice adjusting beneath the weight of the world.
} Available exits: east: Crystal Cave.  south: Forgotten Pathway.  west: Road.   There is an Ice Crystal here."""


# Replace patterns within curly braces with an empty string
event_text = re.sub(r"{.*?}", "", event_text, flags=re.DOTALL)

# Now event_text contains the modified string
print(event_text)

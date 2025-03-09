# Game Server

## Private Modules

### Game Server

The "main" runtime modules. Sets up and runs Game Manager

### Player Input Processor

Where the player's input (i.e. command and nouns etc) is parsed and turned into a reference to a function and parameters

### Game Manager

Where almost all the rest of the game business logic resides, including putting the player's commands into action

### World

Tracks the entities, players, items and their state

### Game Item

Methods and attributes of items in the game

### Entity

A superclass which deals with state and behaviour of both non-player characters (entities) such as Merchants and human/AI players

### Player

A subclass of entity which has additional attributes and behaviours only needed by active players of the game

### Merchant

A subclass of entity which has specific abilities (to buy and sell stuff)

## Common Modules

### Storage Manager

Manages storage and retrieval of game data (superclass for unit testing)

### Azure Storage Manager

Actually stores and retrieves stuff, from Azure

### AI Manager

Manages interaction with LLM for specific use cases of the game manager (e.g. generation of room descriptions and images)

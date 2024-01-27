# Game Server

## Modules

### Game Server

The "main" runtime modules. Comprises SocketIO setup, creation and launch of Game Manager singleton

### Game Manager

Where almost all the business logic resides, especially the processing of player input (i.e. commands)

### World

Tracks the characters, players, objects and their state

### Object

Methods and attributes of objects in the game

### Character

A superclass which deals with state and behaviour of both non-player characters (NPCs) such as Merchants and human/AI players

### Player

A subclass of character which has additional attributes and behaviours only needed by active players of the game

### Merchant

A subclass of character which has specific abilities (to buy and sell stuff)

### Storage Manager

Manages storage and retrieval of dynamic data such as rooms and their exits

### AI Manager

Manages interaction with LLM for specific use cases of the game manager (e.g. generation of room descriptions and images)

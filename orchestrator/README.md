# Orchestrator

## Overview

The Orchestrator is the central runtime system that manages the interaction between various modules to simulate a dynamic world. It processes user input, manages entities and their states, and integrates AI capabilities for enhanced functionality. The system is modular, with private modules handling core logic and common modules providing auxiliary services like storage and AI integration. Communication between these modules and services is facilitated via NATS, ensuring efficient and scalable message passing.

## Private Modules

### Orchestrator

The "main" runtime modules. Sets up and runs World Manager.

### Person Input Processor

Where the user's input (detailed instructions and commands) is parsed and turned into a reference to a function and associated parameters.

### World Manager

Where almost all the rest of the world business logic resides, including putting the person's commands into action.

### World

Tracks the entities, people, items and their state.

### World Item

Methods and attributes of items in the world.

### Entity

A superclass which deals with state and behaviour of both non-person characters (entities) such as Merchants and human/AI agents.

### Person

A subclass of entity which has additional attributes and behaviours only needed by humans and AI agents.

### Merchant

A subclass of entity which has specific abilities (to buy and sell items).

## Common Modules

### Storage Manager

Manages storage and retrieval of world data (superclass for unit testing).

### Azure Storage Manager

Actually stores and retrieves data, from Azure Table Storage.

### AI Manager

Manages interaction with LLM for specific use cases of the world manager (e.g. generation of room descriptions and images).

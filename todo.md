# To do list for the game

## DevOps / Other

- Fix az-deploy-ai.bat to python and sourcing from .env, and azure variables
- Test cloud deployment with Azure Tables

## Game Server

- Unit tests esp more around storage
- Enable trading with the merchant
- Add market data / price changes
- Add AI to merchant (referee parses his responses and decides when he is selling/buying?)
- Add narrator
- support different modes including blank map, and world theme to inspire builder (random 'seed')
- make animals/creatures (with images)
- Refactor so AI usage is centralised

## UI

- Authentication
- Improve layout of showing exits to user
- Add buttons for N/E/S/W

### Storage Manager

- Support Azure storage
- Unit tests

## AI Broker

- AIs don't seem to try to build
- Sometimes there is no delay between commands
- Unit tests
- Try Claude, local LLM
- Langchain
- Use fine tuning so that the rules don't have to be repeated

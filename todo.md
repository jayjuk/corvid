# To do list for the game

_NOTE: I am in the process of migrating these to GitHub Issues which has some improvements not shown below._

## DevOps / Other

- Store images in DB: retrieval needs to work for game client in node!!! on startup it should load all images into public dir

- Unit tests esp more around storage
- Improve singleton code in AI manager and elsewhere - should use \_\_init\_\_, and also not have so much business logic

## Game Server

- Add narrator
- support different modes including blank map, and world theme to inspire builder (random 'seed')
- make animals/creatures (with images)
- Refactor so AI usage is centralised

## UI

- Authentication
- Improve layout of showing exits to user
- Add buttons for N/E/S/W

### Storage Manager

- Move to object approach with state so that storage is faster

## AI Broker

- Log model input/output nicely whether Gemini or OpenAI
- AIs don't seem to try to build
- Try Mistral, Claude, local LLM
- Langchain???
- Use fine tuning so that the rules don't have to be repeated

# LOGGED AS ISSUES

- Add AI to merchant (referee parses his responses and decides when he is selling/buying?)
- Add market data / price changes

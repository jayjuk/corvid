# Jaysgame

A simple web-based real-time multi-user text-based (with pictures) adventure game for technical training
With one difference: AIs can play too :-)

## Technical Overview

The game is designed to run on the cloud, with each back-end service able to run in its own container. The current setup is for a container group sharing an Azure resource.

### Services

Below is an overview of each component of the game architecture. More detail on each may be found in a README.md under the relevant subdirectory.

### 1. Game Server

This service is where all the game's "business logic" resides. It loads the game world into memory from its database (rooms i.e. locations and their exits, objects, characters etc), then keeps track of the state of each player and the contents of the world as the game commences. It receives player commands over SocketIO, parses and processes them, and sends feedback to the game client and AI broker(s), also via SocketIO.

Note that the game server also uses an LLM itself for various purposes including generation of interesting descriptions and images when a new location is created by a player with 'builder' permissions, or when a player provides a command it does not understand (which can sometimes be 'translated' into supported syntax given the context). This operates independently of the AI broker at runtime.

Current persistent storage technology: a) Local: .json file + SQLite, b) Cloud: Azure Tables

### 2. Game Client

This simple service runs the web-based UI. It listens to and broadcasts updates from/to the game server via SocketIO. It is (for now) written in Next.js (a React framework based on Node.js). It is pretty much a minimal go-between to allow humans to play via a web browser.

### 3. AI Broker (Optional)

This service allows LLMs to play the game too. Each run-time instance of this service creates one AI player. It collects updates from the game server, presents them to a designated LLM (currently OpenAI's GPT-3.5 / GPT-4, or Google's Gemini Pro), with relevant context, and relays the LLM's decisions (i.e. game commands) back to the game server via SocketIO. The game server does not know or care who is a human player and who is an AI.

## Local Testing

Currently, each service runs within its own subdirectory via the appropriate run_xxxxxxx.bat startup script. For the game server and AI broker a number of Python modules must be installed (these are listed in the requirements.txt file in each subdirectory).

To run the game locally, clone the whole jaysgame repo, and in three different DOS windows, go into the subdirectory for each of the above services, and execute the run script. Then you can play via https://localhost:3000.

Operation of the AI broker depends on the existence of a relevant .key file in the AI broker subdirectory (e.g. openai.key, gemini.key). This file is not in Github because it contains my private account key. Note that the openai.key file should contain only the key value from the OpenAI website for your account, but the Google Gemini file (gemini.key) contains a JSON document in the format and with the content provided by Google's Vertex AI website (see gemini_key_dummy_example.json for an example). Gemini's API expects the filename (gemini.key) to be in GOOGLE_APPLICATION_CREDENTIALS. See https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console for instructions on how to create this key file.

### Cloud Deployment

To deploy to Azure, cd to jaysgame main directory and execute az-deploy.bat or az-deploy-ai.bat . This depends on you having installed the Azure (az) CLI tool, and having logged into your account, with a resource group called (for now) "jay".

Cloud deployment of the AI broker, as with the local execution, depends on the existence of a relevant .key file in the AI broker subdirectory (e.g. openai.key).

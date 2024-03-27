# Jaysgame

A simple, web-based, cloud-native, real-time, multi-user, text-based (with pictures) adventure game.
With one difference: AIs can play too :-)
I built this for fun and to learn a whole load of new technologies.

## High-Level Technical Overview

The game is designed to run in the cloud. It is composed of a set of services, each of which runs in its own Linux container.
It is deployed via Azure Container Instances, with game data stored in Azure Storage in real time, so that if a service or the server is restarted, no state is lost and the game picks up from where it left off.
Humans play the game via a single web page, served by a Game Client and Image Server. The Game Client interacts with the Game Server via SocketIO (web sockets).
AIs (LLMs) play the game via an AI Broker, which submits game updates to them over their Python APIs, and channels their commands to the Game Server in the same fashion as the Game Client.

### Services

Below is an overview of each component of the game architecture. In future, more detail on each will be available in a README.md under the relevant subdirectory.

### 1. Game Server

This service is where all the game's "business logic" resides. It loads the game world into memory from its database (rooms i.e. locations and their exits, objects, entities etc), then keeps track of the state of each player and the contents of the world as the game commences. It receives player commands over SocketIO, parses and processes them, and sends feedback to the game client and AI broker(s), also via SocketIO.

Note that the game server also uses an LLM itself for various purposes including generation of interesting descriptions and images when a new location is created by a player with 'builder' permissions, or when a player provides a command it does not understand (which can sometimes be 'translated' into supported syntax given the context). This operates independently of the AI broker at runtime.

The Game Server hands all the game's data storage (in Azure). It is written entirely in Python.

### 2. Game Client

This simple service runs the web-based UI. It listens to and broadcasts updates from/to the Game Server via SocketIO. It is (for now) written in Typescript using Next.js (a React framework based on Node.js). It is pretty much a minimal go-between to allow humans to play via a web browser. It also interfaces with the Image Server, over REST, although this is handled natively by HTML when URLs pointing to the Image Server are published over SocketIO each time the player changes location.

### 3. Image Server (Optional)

This component serves up images of locations in the game to the human players' browser. It has a simple Flask web server to receive requests, a file-based local cache, and direct connectivity to Azure Blob Storage via the Python API (which uses REST under the covers). It shares common Storage Management and Logging source code modules (in Python) with the Game Server.

### 4. AI Broker (Optional)

This service allows LLMs to play the game too. Each run-time instance of this service creates one AI player. It collects updates from the game server, presents them to a designated LLM (currently OpenAI's GPT-3.5 / GPT-4, Google's Gemini Pro, and Claude 3 Haiku), with relevant context, and relays the LLM's decisions (i.e. game commands) back to the game server via SocketIO. The game server does not know or care who is a human player and who is an AI. It is written in Python too, and shares Logging and AI Management modules with the Game Server.

## Local Execution

Currently, each service can also be run locally (still connecting to Azure Storage) within its own subdirectory via the appropriate run_xxxxxxx.bat startup script. For the game server and AI broker, a number of Python modules must be installed; these are listed in the requirements.txt file in each subdirectory.

To run the game locally (below is for Windows, launch scripts could be adapted for Linux or MacOS):

1. Set up environment variable PYTHONPATH to include the jaysgame\common subdirectory (this is where _.env_, _logging_ and _storage_manager_ modules reside).
2. Clone the whole jaysgame repo
3. Copy _common\.env.example.txt_ to _.env_, environment variable file, and modify values per next section below - I do not provide cloud or AI provider accounts or API keys!
4. Run the game server: Open a new DOS window, enter into a Python environment with the modules in gameserver\requirements.txt installed via pip (see below\*), cd into gameserver, and run _run_gameserver_locally.bat_
5. Open a new DOS window, cd into gameclient, and run _run_gameclient.bat_ (or launch this from Windows)
6. Run the image server: Open a new DOS window, enter into a Python environment with the modules in imageserver\requirements.txt installed via pip (see below\*), cd into imageserver, and run _run_imageserver_locally.bat_. You can play the game without this, but it's nicer to see the picture of each location.
7. Play the game in your browser via https://localhost:3000.
8. Optionally, to add some AIs into the game, for each one you want to run: Open a new DOS window, enter into a Python environment with the modules in aibroker\requirements.txt installed via pip, cd into aibroker, and run _run_aibroker.bat_.

(\*My chosen method was to install Anaconda including Navigator, and create an environment called jaysgame shared by both the AI broker and the game server)

### Environment Variables and API Keys

Operation of the game depends on the setup of API keys for Azure and AI providers (at least OpenAI). These should obviously not be stored in GitHub alongside source code.

Note that the openai.key file should contain only the key value from the OpenAI website for your account, but the Google Gemini file (gemini.key) contains a JSON document in the format and with the content provided by Google's Vertex AI website (see gemini_key_dummy_example.json for an example). Gemini's API expects the filename (gemini.key) to be in GOOGLE_APPLICATION_CREDENTIALS. See for instructions on how to create this key file.

The keys are:
OPENAI*API_KEY - Obtained from the OpenAI website for your account
GOOGLE_GEMINI_KEY - Create and download the JSON-format key document (see https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console), then run \_common\convert_gemini_key_to_encoded_env_variable.py*, and put the resulting string in this variable (this approach is necessary to avoid having to store the API key, when using the only API Google supports in the UK, Vertex AI). NOTE: Gemini quickly blocks itself after history builds up, on the basis of 'harm' perceived by the adventure, despite there being no threat or danger in the game.
STABILITY_KEY= Obtained from the StabilityAI website after you create an account. Not needed if you (pay more to) use OpenAI's Dall-E 3 model for image generation.
ANTHROPIC_API_KEY - Obtained from the Anthropic website after you create an account. Not needed if you use OpenAI's gpt-3.5 model (or later) for text generation.
AZURE_STORAGE_ACCOUNT_KEY - Obtained from the Azure Storage console after you create a storage account.

Other environment variables to update in .env (for local operation), GitHub Actions Secrets (for Continuous Integration) and Azure Container Instances secrets (for production deployment) as required:

MODEL*NAME - e.g. gpt-3.5-turbo, gemini-pro (see caveat above), or claude-3-haiku-20240307. Used both by AI Broker and Game Server (which share the AI Manager) but they can be configured differently due to the services running in separate containers.
AZURE_STORAGE_ACCOUNT_NAME - Also from the Azure console, this will look something like csa123456fff1a111a1a
GAMESERVER_HOSTNAME - localhost when running locally, otherwise something like jaysgame.westeurope.azurecontainer.io, with the first world modified to your own environment
GAMESERVER_PORT - e.g. 3001 (3000 is used by Next.js for the UI)
GAMESERVER_WORLD_NAME - the name of the 'world' e.g. jaysgame or mansion (currently the examples checked in). A new world currently requires setup of \_gameserver\world_data\world_name\*.json* files.
IMAGESERVER_HOSTNAME - likely to be the same as GAMESERVER_HOSTNAME above
IMAGESERVER_PORT - e.g. 3002

### Unit Testing

A limited number of unit tests have been written, with more to follow. These are run automatically when code commits are pushed to GitHub (triggering Actions that test and build). They can also be run locally, using the same configuration and containerisation as GitHub, with the help of Nektos Act (https://github.com/nektos/act), by launching _run_unit_tests.bat_ from the game home directory.

### Cloud Deployment

To deploy to Azure, cd to jaysgame main directory and execute _az-deploy.bat_ or _az-deploy-ai.bat_ . This depends on you having installed the Azure (az) CLI tool, and having logged into your account, with a resource group called (for now) "jay". To stop and tear down, run _az-delete.bat_.

Cloud deployment of the AI broker, as with the local execution, depends on the existence of _common\.env_ as described above. The above deployment scripts invoke a Python script which generates a temporary YAML file to be used with the Azure CLI, containing the environment variable values.

### Known Issues & Improvements

These are logged at https://github.com/jayjuk/jaysgame/issues

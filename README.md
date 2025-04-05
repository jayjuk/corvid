# Corvid

Corvid is a platform for creating open-world, persistent, multi-user simulated environments in the cloud. Designed for collaborative teams of humans and AI agents, it uses LLMs to interpret natural language instructions, expand on user ideas, and generate vivid descriptions with supporting imagery.

## High-Level Technical Overview

Corvid is composed of modular, containerised services, each running in its own Docker environment. It is deployed using Terraform on DigitalOcean droplets. Real-time state persistence for each simulated environment is managed through Azure Table Storage, allowing continuous and accurate state recovery upon service restarts.
Human users interact with Corvid environments via a web-based user interface, managed by the Client and Image Server. Communication between the Client and Orchestrator occurs via NATS, utilizing WebSockets for seamless real-time interaction.
AI agents powered by LLMs interact with the environment through an AI Broker, which exchanges updates with the Orchestrator over Python-based APIs and NATS, in parallel to the human-client communication.

### Services

The following is a summary of each core component within the Corvid architecture. More detailed documentation will be provided within individual subdirectories.

### 1. Orchestrator

This service contains the primary business logic for managing simulated environments. It initialises world data, manages user and entity states, processes commands via NATS, and provides feedback to users and AI agents. The Orchestrator also uses NATS to farm out LLM-dependent workloads to other services. Data persistence and management utilise Azure Storage. The server is implemented entirely in Python.

### 2. Front End

The Front End provides a web-based user interface, facilitating user interaction through real-time updates exchanged with the Orchestrator via NATS. Built with Next.js (React framework) in TypeScript, it interfaces with the Image Server through REST APIs to dynamically present visual content.

### 3. AI Requester

The AI Requester handles complex natural language inputs and instructions that the Orchestrator cannot directly interpret, delegating these to specialised LLM-powered services for contextual processing.

### 3. Image Server

Responsible for delivering visual assets to users, this service employs a Flask-based API server. It manages image requests, maintains a local cache, and directly interacts with Azure Blob Storage through Python APIs.

### 4. Image Creator

This service produces visuals for new locations or entities within simulated environments. Utilising image-generation models, it enriches textual prompts with LLM support to ensure meaningful and contextually accurate imagery.

### 5. User Manager

Responding to "summon" requests, this service dynamically initiates AI Broker instances, enabling the introduction of new AI-controlled entities into active environments.

### 6. AI Broker (Optional)

This service allows LLMs to play the game too. Each run-time instance of this service creates one AI player. It collects updates from the Orchestrator, presents them to a designated LLM (currently OpenAI's GPT-3.5 / GPT-4, Google's Gemini Pro, and Claude 3 Haiku), with relevant context, and relays the LLM's decisions (i.e. game commands) back to the Orchestrator via NATS. The Orchestrator does not know or care who is a human player and who is an AI. It is written in Python too, and shares Logging and AI Management modules with the Orchestrator.

## Local Execution

Currently, each service can also be run locally (still connecting to Azure Storage) within its own subdirectory via the appropriate run_xxxxxxx.bat startup script. For the Orchestrator and AI broker, a number of Python modules must be installed; these are listed in the requirements.txt file in each subdirectory.

To run the game locally (below is for Windows, launch scripts could be adapted for Linux or MacOS):

1. Set up environment variable PYTHONPATH to include the corvid\common subdirectory (this is where _.env_, _logging_ and _storage_manager_ modules reside).
2. Clone the whole corvid repo
3. Copy _common\.env.example.txt_ to _.env_, environment variable file, and modify values per next section below - I do not provide cloud or AI provider accounts or API keys!
4. Run the Orchestrator: Open a new DOS window, enter into a Python environment with the modules in orchestrator\requirements.txt installed via pip (see below\*), cd into orchestrator, and run _run_orchestrator_locally.bat_
5. Open a new DOS window, cd into frontend, and run _run_frontend.bat_ (or launch this from Windows)
6. Run the image server: Open a new DOS window, enter into a Python environment with the modules in imageserver\requirements.txt installed via pip (see below\*), cd into imageserver, and run _run_imageserver_locally.bat_. You can play the game without this, but it's nicer to see the picture of each location.
7. Play the game in your browser via https://localhost:3000.
8. Optionally, to add some AIs into the game, for each one you want to run: Open a new DOS window, enter into a Python environment with the modules in aibroker\requirements.txt installed via pip, cd into aibroker, and run _run_aibroker.bat_.

(\*My chosen method was to install Anaconda including Navigator, and create an environment called corvid shared by both the AI broker and the Orchestrator)

### Environment Variables and API Keys

Operation of the game depends on the setup of API keys for Azure and AI providers (at least OpenAI). These should obviously not be stored in GitHub alongside source code.

Note that the openai.key file should contain only the key value from the OpenAI website for your account, but the Google Gemini file (gemini.key) contains a JSON document in the format and with the content provided by Google's Vertex AI website (see gemini_key_dummy_example.json for an example). Gemini's API expects the filename (gemini.key) to be in GOOGLE_APPLICATION_CREDENTIALS. See for instructions on how to create this key file.

The keys are:
OPENAI\*API\*KEY - Obtained from the OpenAI website for your account
GOOGLE_GEMINI_KEY - Create a service account and create an API (see https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console), which will and download the JSON-format key document. Then run common\convert_gemini_key_to_encoded_env_variable.py, and put the resulting string in this variable (this approach is necessary to avoid having to store the API key, when using the only API Google supports in the UK, Vertex AI). Be sure to also do the following in the console: 1. Enable the Vertex API; 2. Check the project ID; 3. Check the location; 4. Give permissions to the service account
GOOGLE_GEMINI_PROJECT_ID= From the Project settings page of the Console
GOOGLE_GEMINI_LOCATION= Probably us-central1
STABILITY_KEY= Obtained from the StabilityAI website after you create an account. Not needed if you (pay more to) use OpenAI's Dall-E 3 model for image generation.
ANTHROPIC_API_KEY - Obtained from the Anthropic website after you create an account. Not needed if you use OpenAI's gpt-3.5 model (or later) for text generation.
AZURE_STORAGE_ACCOUNT_KEY - Obtained from the Azure Storage console after you create a storage account.

Other environment variables to update in .env (for local operation), GitHub Actions Secrets (for Continuous Integration) and Azure Container Instances secrets (for production deployment) as required:

MODEL_NAME - e.g. gpt-3.5-turbo, gemini-pro (see caveat above), or claude-3-haiku-20240307. Used both by AI Broker and Orchestrator (which share the AI Manager) but they can be configured differently due to the services running in separate containers.
AIREQUESTER_MODEL_NAME - Specific model name for AI Requester, which handles more complex requests.
AZURE_STORAGE_ACCOUNT_NAME - Also from the Azure console, this will look something like csa123456fff1a111a1a
orchestrator_HOSTNAME - localhost when running locally, otherwise something like corvid.westeurope.azurecontainer.io, with the first world modified to your own environment
orchestrator_PORT - e.g. 3001 (3000 is used by Next.js for the UI)
orchestrator_WORLD_NAME - the name of the 'world' e.g. corvid or mansion (currently the examples checked in). A new world currently requires setup of \_orchestrator\world_data\world_name\*.json\* files.
IMAGESERVER_HOSTNAME - likely to be the same as orchestrator_HOSTNAME above
IMAGESERVER_PORT - e.g. 3002

### Unit Testing

A limited number of unit tests have been written, with more to follow. These are run automatically when code commits are pushed to GitHub (triggering Actions that test and build). They can also be run locally, using the same configuration and containerisation as GitHub, with the help of Nektos Act (https://github.com/nektos/act), by launching _run_unit_tests.bat_ from the game home directory.

### Cloud Deployment

To deploy to Digital Ocean, cd to corvid main directory, then the terraform subdirectory, then execute run_terraform.bat ! It is necessary to have SSH keys set up per Digital Ocean's instructions as part of account setup.

Cloud deployment of the AI broker, as with the local execution, depends on the existence of _common\.env_ as described above. The above deployment scripts invoke a Python script which generates a temporary YAML file to be used with the Azure CLI, containing the environment variable values.

### Known Issues & Improvements

These are logged at https://github.com/jayjuk/corvid/issues

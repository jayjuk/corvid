# Corvid

Corvid is a platform for creating open-world, persistent, multi-user simulated environments in the cloud. Designed for collaborative teams of humans and AI agents, it uses LLMs to interpret natural language instructions, expand on user ideas, and generate vivid descriptions with supporting imagery.

## Use Cases

- Research platform for exploring interactions between humans and autonomous AI agents in shared simulated environments.

- Benchmarking LLMs, with a focus on role-playing behaviours and character modelling.

- Rapid creation of interactive experiences and customised simulations tailored for organisations, interest groups, or training in prompt engineering, managing teams, trading and more.

- Educational tool for teaching principles of distributed systems, real-time communication, and cloud infrastructure.

- Platform extension and customisation as a technical training exercise for software engineers.

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

The AI Broker enables LLM-powered AI agents to actively participate within simulated worlds. It processes environmental updates and relays AI-generated actions back to the Orchestrator, maintaining transparent integration of AI and human participants. Implemented in Python, it shares common infrastructure modules with the Orchestrator.

## Local Execution

Each service can be executed locally, interfacing with cloud services (Azure Storage). Detailed execution steps include environment setup, dependency installation via pip, and individual launch scripts for each component. Specific setup and launch instructions are provided within each component directory.

### Environment Variables and API Keys

Operation requires appropriate API keys for Azure and supported LLM providers (OpenAI, Google Gemini, Anthropic). These keys are configured securely using local environment variables or secrets management services for continuous integration (GitHub Actions) and cloud deployment (Digital Ocean or Azure Container Instances). More details are available under specific service directories and in the deployment directory.

### Unit Testing

Corvid includes automated unit testing integrated with GitHub Actions for continuous integration. Tests can also be executed locally using containerised environments (Nektos Act), with instructions provided in the root directory.

### Cloud Deployment

Deployment to DigitalOcean is facilitated via Terraform. Detailed setup instructions, including SSH key configuration, are available in the deploy directory. Deployment scripts dynamically generate environment configurations, securely integrating essential keys and parameters.

## Roadmap

## New Features

The platform is still very much in its infancy. For tracking issues and planned improvements, see the [Corvid Issues Page](https://github.com/jayjuk/corvid/issues). Major future capabilities include:

- Support load-balancing across many LLM APIs. Currently the platform supports a number of vendors and interfaces, and the AI Broker can be configured to use many, but all summoned agents are instantiated against a single API, leading to rate-limiting if too many agents are introduced to a world. [#108]([https://github.com/jayjuk/corvid/issues/108])
- Enrich the simulation with AI-supported physics including time. For example, currently a user can start a fire, but it will never go out. [#109]([https://github.com/jayjuk/corvid/issues/109])
- Add concept of background/foreground. This will improve the consistency of descriptions of locations and of interaction with nearby real-world things that are too large to be handled like 'items'. [#110]([https://github.com/jayjuk/corvid/issues/110])
- Prices should fluctuate [#7](https://github.com/jayjuk/corvid/issues/7)

## Getting Involved

- If you would like to contribute to this platform, please get in touch via [my profile page](https://github.com/jayjuk).

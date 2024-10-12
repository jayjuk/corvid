terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}


# Retrieve local state from the first configuration
data "terraform_remote_state" "droplet" {
  backend = "local"
  config = {
    path = "../droplet_configuration/terraform.tfstate"
  }
}

variable "pvt_key" {
  description = "Path to the SSH private key"
  type        = string
  default     = "C:/Users/me/.ssh/id_rsa"
}

variable "CONTAINER_REGISTRY_REPOSITORY" {
  description = "Container registry repository"
  type        = string
}

# Add any additional environment variables as Terraform variables
variable "GAMESERVER_PORT" {
  type = string
}

# Add any additional environment variables as Terraform variables
variable "IMAGE_MODEL_NAME" {
  type = string
}

# Add any additional environment variables as Terraform variables
variable "AI_COUNT" {
  type = string
}

# Add any additional environment variables as Terraform variables
variable "MODEL_SYSTEM_MESSAGE" {
  type = string
}

variable "GAMESERVER_WORLD_NAME" {
  type = string
}

variable "AZURE_STORAGE_ACCOUNT_NAME" {
  type = string
}

variable "AZURE_STORAGE_ACCOUNT_KEY" {
  type      = string
  sensitive = true
}

variable "MODEL_NAME" {
  type = string
}

variable "OPENAI_API_KEY" {
  type      = string
  sensitive = true
}

variable "STABILITY_KEY" {
  type      = string
  sensitive = true
}

variable "ANTHROPIC_API_KEY" {
  type      = string
  sensitive = true
}

variable "GROQ_API_KEY" {
  type      = string
  sensitive = true
}

variable "GOOGLE_GEMINI_KEY" {
  type      = string
  sensitive = true
}

variable "GOOGLE_GEMINI_PROJECT_ID" {
  type = string
}

variable "GOOGLE_GEMINI_LOCATION" {
  type = string
}

variable "GOOGLE_GEMINI_SAFETY_OVERRIDE" {
  type = string
}

provider "docker" {
  host     = "ssh://root@${data.terraform_remote_state.droplet.outputs.droplet_ip}:22"
  ssh_opts = ["-i", var.pvt_key]
}

# Create a network
resource "docker_network" "jaysgame_network" {
  name = "jaysgame_network"
}

# Pull and run game containers
resource "docker_container" "gameclient_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/gameclient"
  name  = "gameclient"

  ports {
    internal = 3000
    external = 3000
  }

  networks_advanced {
    name = docker_network.jaysgame_network.name
  }
}

resource "docker_container" "gameserver_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/gameserver"
  name  = "gameserver"

  env = [
    "GAMESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "GAMESERVER_PORT=3001",
    "IMAGESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "IMAGESERVER_PORT=3002",
    "GAMESERVER_WORLD_NAME=${var.GAMESERVER_WORLD_NAME}",
    "AZURE_STORAGE_ACCOUNT_NAME=${var.AZURE_STORAGE_ACCOUNT_NAME}",
    "AZURE_STORAGE_ACCOUNT_KEY=${var.AZURE_STORAGE_ACCOUNT_KEY}",
    "MODEL_NAME=${var.MODEL_NAME}",
    "OPENAI_API_KEY=${var.OPENAI_API_KEY}",
    "STABILITY_KEY=${var.STABILITY_KEY}",
    "ANTHROPIC_API_KEY=${var.ANTHROPIC_API_KEY}",
    "GROQ_API_KEY=${var.GROQ_API_KEY}",
    "GOOGLE_GEMINI_KEY=${var.GOOGLE_GEMINI_KEY}",
    "GOOGLE_GEMINI_PROJECT_ID=${var.GOOGLE_GEMINI_PROJECT_ID}",
    "GOOGLE_GEMINI_LOCATION=${var.GOOGLE_GEMINI_LOCATION}",
    "GOOGLE_GEMINI_SAFETY_OVERRIDE=${var.GOOGLE_GEMINI_SAFETY_OVERRIDE}"
  ]

  ports {
    internal = 3001
    external = 3001
  }

  networks_advanced {
    name = docker_network.jaysgame_network.name
  }
}

resource "docker_container" "imageserver_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/imageserver"
  name  = "imageserver"

  env = [
    "IMAGESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "IMAGESERVER_PORT=3002",
    "AZURE_STORAGE_ACCOUNT_NAME=${var.AZURE_STORAGE_ACCOUNT_NAME}",
    "AZURE_STORAGE_ACCOUNT_KEY=${var.AZURE_STORAGE_ACCOUNT_KEY}"
  ]

  ports {
    internal = 3002
    external = 3002
  }

  networks_advanced {
    name = docker_network.jaysgame_network.name
  }
}

resource "docker_container" "imagecreator_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/imagecreator"
  name  = "imagecreator"

  env = [
    "GAMESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "GAMESERVER_PORT=${var.GAMESERVER_PORT}",
    "AZURE_STORAGE_ACCOUNT_NAME=${var.AZURE_STORAGE_ACCOUNT_NAME}",
    "AZURE_STORAGE_ACCOUNT_KEY=${var.AZURE_STORAGE_ACCOUNT_KEY}",
    "IMAGE_MODEL_NAME=${var.IMAGE_MODEL_NAME}",
    "OPENAI_API_KEY=${var.OPENAI_API_KEY}",
    "STABILITY_KEY=${var.STABILITY_KEY}",
    "GOOGLE_GEMINI_KEY=${var.GOOGLE_GEMINI_KEY}",
    "GOOGLE_GEMINI_SAFETY_OVERRIDE=${var.GOOGLE_GEMINI_SAFETY_OVERRIDE}",
    "GOOGLE_GEMINI_PROJECT_ID=${var.GOOGLE_GEMINI_PROJECT_ID}",
    "GOOGLE_GEMINI_LOCATION=${var.GOOGLE_GEMINI_LOCATION}"
  ]

  networks_advanced {
    name = docker_network.jaysgame_network.name
  }
}

resource "docker_container" "aibroker_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/aibroker"
  name  = "aibroker"

  env = [
    "AI_COUNT=${var.AI_COUNT}",
    "MODEL_NAME=${var.MODEL_NAME}",
    "MODEL_SYSTEM_MESSAGE=${var.MODEL_SYSTEM_MESSAGE}",
    "OPENAI_API_KEY=${var.OPENAI_API_KEY}",
    "STABILITY_KEY=${var.STABILITY_KEY}",
    "ANTHROPIC_API_KEY=${var.ANTHROPIC_API_KEY}",
    "GROQ_API_KEY=${var.GROQ_API_KEY}",
    "GOOGLE_GEMINI_KEY=${var.GOOGLE_GEMINI_KEY}",
    "GOOGLE_GEMINI_PROJECT_ID=${var.GOOGLE_GEMINI_PROJECT_ID}",
    "GOOGLE_GEMINI_LOCATION=${var.GOOGLE_GEMINI_LOCATION}",
    "GOOGLE_GEMINI_SAFETY_OVERRIDE=${var.GOOGLE_GEMINI_SAFETY_OVERRIDE}",
    "GAMESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "GAMESERVER_PORT=3001"
  ]

  networks_advanced {
    name = docker_network.jaysgame_network.name
  }
  #Emit IP addrees of the container
  provisioner "local-exec" {
    command = "echo Play the game at: https://${data.terraform_remote_state.droplet.outputs.droplet_ip}:3000"
  }
}

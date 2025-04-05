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
variable "orchestrator_PORT" {
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

variable "orchestrator_WORLD_NAME" {
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

# Specific model for AI Requester
variable "AIREQUESTER_MODEL_NAME" {
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
  ssh_opts = ["-i", var.pvt_key, "-o", "StrictHostKeyChecking=no"]
}
# Create a network
resource "docker_network" "corvid_network" {
  name = "corvid_network"
}

locals {
  module_path_tmp = "/${replace(abspath(path.root), ":", "")}"
  module_path     = replace(local.module_path_tmp, "////", "/")
}

resource "docker_container" "nats_container" {
  image = "nats:latest"
  name  = "nats"

  # Default NATS client port
  ports {
    internal = 4222
    external = 4222
  }

  # HTTP monitoring
  ports {
    internal = 8222
    external = 8222
  }

  # WebSocket port
  ports {
    internal = 9222
    external = 9222
  }

  restart = "always"

  networks_advanced {
    name = docker_network.corvid_network.name
  }

  # Write a remote startup script for NATS
  provisioner "remote-exec" {
    inline = [

      # Ensure NATS config directory exists
      "sudo mkdir -p /etc/nats",

      # Create NATS config file directly on the remote machine
      "rm -rf /etc/nats/nats-server.conf",
      "echo 'port: 4222' > /etc/nats/nats-server.conf",
      "echo '' >> /etc/nats/nats-server.conf",
      "echo 'websocket {' >> /etc/nats/nats-server.conf",
      "echo '  port: 9222' >> /etc/nats/nats-server.conf",
      "echo '  no_tls: true' >> /etc/nats/nats-server.conf",
      "echo '}' >> /etc/nats/nats-server.conf",
      "echo '' >> /etc/nats/nats-server.conf",
      "echo 'http_port: 8222' >> /etc/nats/nats-server.conf",
      "echo 'Nat-server config file created:' > /tmp/nats.log",
      "ls -l /etc/nats >> /tmp/nats.log",
    ]

    connection {
      type        = "ssh"
      user        = "root"
      host        = data.terraform_remote_state.droplet.outputs.droplet_ip
      private_key = file(var.pvt_key)
      timeout     = "5m"
    }
  }

  volumes {
    host_path      = "/etc/nats"
    container_path = "/etc/nats"
  }

  # Use the config file to enable WebSockets
  command = ["-c", "/etc/nats/nats-server.conf"]
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
    name = docker_network.corvid_network.name
  }
}

# Pull and run game containers
resource "docker_container" "frontend_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/frontend"
  name  = "frontend"

  ports {
    internal = 3000
    external = 3000
  }

  networks_advanced {
    name = docker_network.corvid_network.name
  }

  # Write a remote startup script to the container
  provisioner "remote-exec" {
    inline = [
      "echo 'docker run -d \\",
      "--name client \\",
      "-p 3000:3000 \\",
      "${var.CONTAINER_REGISTRY_REPOSITORY}/frontend' >> ./start_frontend.sh",
      "chmod +x ./start_frontend.sh"
    ]

    connection {
      type        = "ssh"
      user        = "root"                                                 # Use the appropriate user for your remote server
      host        = data.terraform_remote_state.droplet.outputs.droplet_ip # IP of the remote machine
      private_key = file(var.pvt_key)                                      # Path to your SSH private key
      timeout     = "5m"
    }
  }

  #Emit IP address of the container
  provisioner "local-exec" {
    command = "echo Play the game at: https://${data.terraform_remote_state.droplet.outputs.droplet_ip}:3000"
  }

}

resource "docker_container" "orchestrator_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/orchestrator"
  name  = "orchestrator"

  env = [
    "orchestrator_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "orchestrator_PORT=4222",
    "IMAGESERVER_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "IMAGESERVER_PORT=3002",
    "orchestrator_WORLD_NAME=${var.orchestrator_WORLD_NAME}",
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

  networks_advanced {
    name = docker_network.corvid_network.name
  }
}

resource "docker_container" "imagecreator_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/imagecreator"
  name  = "imagecreator"

  env = [
    "orchestrator_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "orchestrator_PORT=${var.orchestrator_PORT}",
    "AZURE_STORAGE_ACCOUNT_NAME=${var.AZURE_STORAGE_ACCOUNT_NAME}",
    "AZURE_STORAGE_ACCOUNT_KEY=${var.AZURE_STORAGE_ACCOUNT_KEY}",
    "MODEL_NAME=${var.MODEL_NAME}",
    "IMAGE_MODEL_NAME=${var.IMAGE_MODEL_NAME}",
    "OPENAI_API_KEY=${var.OPENAI_API_KEY}",
    "STABILITY_KEY=${var.STABILITY_KEY}",
    "GOOGLE_GEMINI_KEY=${var.GOOGLE_GEMINI_KEY}",
    "GOOGLE_GEMINI_SAFETY_OVERRIDE=${var.GOOGLE_GEMINI_SAFETY_OVERRIDE}",
    "GOOGLE_GEMINI_PROJECT_ID=${var.GOOGLE_GEMINI_PROJECT_ID}",
    "GOOGLE_GEMINI_LOCATION=${var.GOOGLE_GEMINI_LOCATION}"
  ]

  networks_advanced {
    name = docker_network.corvid_network.name
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
    "orchestrator_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "orchestrator_PORT=4222"
  ]

  networks_advanced {
    name = docker_network.corvid_network.name
  }
}

resource "docker_container" "agentmanager_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/agentmanager"
  name  = "agentmanager"

  env = [
    "AI_COUNT=1",
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
    "orchestrator_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "orchestrator_PORT=4222"
  ]

  networks_advanced {
    name = docker_network.corvid_network.name
  }
}

resource "docker_container" "airequester_container" {
  image = "${var.CONTAINER_REGISTRY_REPOSITORY}/airequester"
  name  = "airequester"

  env = [
    "MODEL_NAME=${var.AIREQUESTER_MODEL_NAME}",
    "MODEL_SYSTEM_MESSAGE=${var.MODEL_SYSTEM_MESSAGE}",
    "OPENAI_API_KEY=${var.OPENAI_API_KEY}",
    "ANTHROPIC_API_KEY=${var.ANTHROPIC_API_KEY}",
    "GROQ_API_KEY=${var.GROQ_API_KEY}",
    "GOOGLE_GEMINI_KEY=${var.GOOGLE_GEMINI_KEY}",
    "GOOGLE_GEMINI_PROJECT_ID=${var.GOOGLE_GEMINI_PROJECT_ID}",
    "GOOGLE_GEMINI_LOCATION=${var.GOOGLE_GEMINI_LOCATION}",
    "GOOGLE_GEMINI_SAFETY_OVERRIDE=${var.GOOGLE_GEMINI_SAFETY_OVERRIDE}",
    "orchestrator_HOSTNAME=${data.terraform_remote_state.droplet.outputs.droplet_ip}",
    "orchestrator_PORT=4222"
  ]

  networks_advanced {
    name = docker_network.corvid_network.name
  }

}


terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

variable "do_token" {
  description = "DOP Key"
  type        = string
}

variable "pvt_key" {
  description = "Path to the SSH private key"
  type        = string
  default     = "C:/Users/me/.ssh/id_rsa"
}

# Retrieve local state from the first configuration
data "terraform_remote_state" "droplet" {
  backend = "local"
  config = {
    path = "../droplet_configuration/terraform.tfstate"
  }
}

provider "docker" {
  host = "ssh://root@${data.terraform_remote_state.droplet.outputs.droplet_ip}:22"
  ssh_opts = ["-i", var.pvt_key]
}


# Pull the custom Docker image
resource "docker_image" "gameserver" {
  name = "jayjuk/gameserver:latest"
}

# Run a container using the custom image
resource "docker_container" "gameserver_container" {
  image = docker_image.gameserver.name
  name  = "my_gameserver"
  ports {
    internal = 3000  # Change to the correct port exposed by your image
    external = 3000
  }
  depends_on = [docker_image.gameserver]
}

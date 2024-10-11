terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
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


provider "digitalocean" {
  token = var.do_token
}

data "digitalocean_ssh_key" "terraform" {
  name = "Desktop"
}


resource "digitalocean_droplet" "jaysgame" {
  image = "ubuntu-24-04-x64"
  name = "jaysgame"
  region = "lon1"
  size = "s-1vcpu-1gb"
  ssh_keys = [
    data.digitalocean_ssh_key.terraform.id
  ]
  connection {
    host = self.ipv4_address
    user = "root"
    type = "ssh"
    private_key = file(var.pvt_key)
    timeout = "2m"
  }
  provisioner "remote-exec" {
    inline = [
      "export PATH=$PATH:/usr/bin",
      "echo test > test.txt",
      "sudo apt-get update",
      "sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release",
      "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
      "sudo apt-get update",
      "sudo apt-get install -y docker-ce docker-ce-cli containerd.io",
      "sudo systemctl start docker",
      "sudo systemctl enable docker"    
      ]
  }  
}

# Ensure that Docker setup is complete before starting to use the Docker provider
resource "null_resource" "wait_for_docker" {
  depends_on = [digitalocean_droplet.jaysgame]

  provisioner "remote-exec" {
    inline = [
      "echo Waiting for Docker setup to complete",
      "sleep 30",  # Wait for 30 seconds to ensure Docker is fully initialized
      "docker --version"  # You can use this to confirm Docker is installed
    ]
    connection {
      host = digitalocean_droplet.jaysgame.ipv4_address
      user = "root"
      type = "ssh"
      private_key = file(var.pvt_key)
    }
  }
}

output "droplet_ip" {
  value = digitalocean_droplet.jaysgame.ipv4_address
}

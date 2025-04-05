terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
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


resource "digitalocean_droplet" "corvid" {
  image  = "ubuntu-24-04-x64"
  name   = "corvid"
  region = "lon1"
  size   = "s-1vcpu-2gb"

  ssh_keys = [
    data.digitalocean_ssh_key.terraform.id
  ]
  connection {
    host        = self.ipv4_address
    user        = "root"
    type        = "ssh"
    private_key = file(var.pvt_key)
    timeout     = "2m"
  }
  provisioner "remote-exec" {
    inline = [
      "export PATH=$PATH:/usr/bin",
      "echo Installing Docker > docker_install_log.txt",

      # Wait for apt lock to be released
      "while sudo fuser /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock >/dev/null 2>&1; do sleep 10; done",

      "sudo apt-get update",
      "sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release",

      # Ensure Docker GPG key is correctly added
      "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",

      # Verify Ubuntu version and repo addition
      "echo \"Using Ubuntu release: $(lsb_release -cs)\" >> docker_install_log.txt",
      "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",

      "sudo apt-get update",
      "sudo apt-get install -y docker-ce docker-ce-cli containerd.io",

      "sudo systemctl start docker",
      "sudo systemctl enable docker",
      "echo Done installing Docker >> docker_install_log.txt",
      "docker --version >> docker_install_log.txt",
      "sudo systemctl status docker >> docker_install_log.txt",
      # Cleanup script
      "echo '#!/bin/bash' > cleanup_docker.sh", # was in /usr/local/bin/
      "echo 'docker stop $(docker ps -a -q)' >> cleanup_docker.sh",
      "echo 'docker rm $(docker ps -a -q)' >> cleanup_docker.sh",
      "chmod +x cleanup_docker.sh"
    ]
  }
}

resource "digitalocean_record" "a_record" {
  domain = "moncorvosolutions.com"
  type   = "A"
  name   = "game" # This is for the root domain, use "www" for a subdomain
  value  = digitalocean_droplet.corvid.ipv4_address
  ttl    = 3600
}

output "droplet_ip" {
  value = digitalocean_droplet.corvid.ipv4_address
}

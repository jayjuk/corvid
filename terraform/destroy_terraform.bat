@echo off
echo Destroying Terraform resources!
cd droplet_configuration
terraform destroy -auto-approve
cd ..

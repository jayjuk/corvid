@echo off
echo Destroying Terraform resources!
cd docker_configuration
terraform destroy -auto-approve
cd ..
REM Check if the first parameter is "docker" (case insensitive)
if /I "%1" NEQ "docker" (
        cd droplet_configuration
        terraform destroy -auto-approve
        cd ..
)


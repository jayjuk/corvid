rem az container create --resource-group jay --file deploy-aci.yaml
echo Check .env file for correct values for container registry
echo TODO: set them here
pause
python az-deploy.py deploy-aci.yaml 0


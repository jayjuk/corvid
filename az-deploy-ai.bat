rem Replace environment variable in yaml file based on OpenAI key file, and deploy to Azure Container Instance via temporary file:
powershell -Command "$env:OPENAI_API_KEY = Get-Content .\aibroker\openai.key; (Get-Content deploy-aci.yaml) -replace 'value: \"\${OPENAI_API_KEY}\"', ('value: \"' + $env:OPENAI_API_KEY + '\"') | Set-Content temp-deploy-aci-ai.yaml"
SET AI_COUNT=1
powershell -Command "(Get-Content temp-deploy-aci-ai.yaml) -replace 'value: \"\${AI_COUNT}\"', ('value: \"' + $env:AI_COUNT + '\"') | Set-Content temp-deploy-aci-ai.yaml"
az container create --resource-group jay --file temp-deploy-aci-ai.yaml
rem Clean up temporary file:
del temp-deploy-aci-ai.yaml

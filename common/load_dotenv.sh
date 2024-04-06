while IFS='=' read -r key value
do
  # Ignore lines starting with #
  [[ $key = \#* ]] && continue
  export "$key=$value"
  echo "Setting $key"
done < "../common/.env"
echo "Loaded env variables from common .env file in local execution..."

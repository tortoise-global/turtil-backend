terraform output -json environment_variables > env_config.json

jq -r 'to_entries[] | "\(.key)=\(.value)"' env_config.json > .env

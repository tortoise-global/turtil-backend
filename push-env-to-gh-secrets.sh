#!/bin/bash

# Push all .env variables to GitHub Actions secrets for the "dev" environment

ENV_FILE=".env"
ENV_NAME="dev"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE not found!"
  exit 1
fi

echo "🔄 Loading variables from $ENV_FILE"

# Read and export all key-value pairs from the .env file
while IFS='=' read -r key value || [[ -n "$key" ]]; do
  # Skip empty lines and comments
  if [[ -z "$key" || "$key" == \#* ]]; then
    continue
  fi

  # Remove possible surrounding quotes and trim spaces
  clean_key=$(echo "$key" | xargs)
  clean_value=$(echo "$value" | sed -e 's/^["'"'"']//' -e 's/["'"'"']$//' | xargs)

  echo "⬆️  Setting $clean_key in GitHub Secrets for env '$ENV_NAME'"
  gh secret set "$clean_key" --env "$ENV_NAME" --body "$clean_value"
done < "$ENV_FILE"

echo "✅ All secrets pushed to GitHub environment '$ENV_NAME'"

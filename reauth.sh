#!/usr/bin/env bash
set -e

echo "=== Tempo Wallet Re-Authorization ==="
echo ""
echo "Step 1: Installing Tempo..."
curl -fsSL https://tempo.xyz/install | bash
source ~/.tempo/env
echo ""
echo "Step 2: Logging in (a browser link will appear below)."
echo "Open the link, authorize in the browser, then return here."
echo ""
tempo wallet login
echo ""
echo "Step 3: Updating TEMPO_KEYS_TOML secret in GitHub..."
gh secret set TEMPO_KEYS_TOML \
  --body "$(cat ~/.tempo/wallet/keys.toml)" \
  --repo westham1984-cell/tempo-daily-agent
echo ""
echo "Done! TEMPO_KEYS_TOML updated successfully."
echo "You can now trigger the CoinGecko Daily workflow to verify."

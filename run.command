#!/bin/bash
# Night Desk launcher for macOS - double-click or run ./run.command
cd "$(dirname "$0")"
if [ -z "$DREX_API_KEY" ]; then
  read -s -p "Paste your Nace API key (nace_sk_...): " DREX_API_KEY; echo
  export DREX_API_KEY
fi
python3 server.py

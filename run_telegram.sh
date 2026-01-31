#!/bin/bash

echo "============================================"
echo "  PsychoTeleBot - Telegram Mode"
echo "============================================"
echo ""
echo "Checking configuration..."

if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo ""
    echo "Please create .env file with your Telegram bot token:"
    echo "TELEGRAM_BOT_TOKEN=your_token_here"
    echo ""
    echo "See .env.example for reference."
    exit 1
fi

echo "Configuration found."
echo "Starting Telegram bot..."
echo ""

python -m adapters.telegram.run

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Bot failed to start!"
    echo ""
    echo "Common issues:"
    echo "1. Check if TELEGRAM_BOT_TOKEN is set in .env"
    echo "2. Install dependencies: pip install -r requirements-telegram.txt"
    echo "3. Check your internet connection"
fi

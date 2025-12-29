#!/bin/bash

echo "========================================"
echo "XHS-MarketAI System - Quick Setup"
echo "========================================"
echo ""

echo "[1/4] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

echo "[2/4] Activating virtual environment..."
source venv/bin/activate

echo "[3/4] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo "[4/4] Setup complete!"
echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Set your DeepSeek API key:"
echo "   export DEEPSEEK_API_KEY='your_key_here'"
echo ""
echo "3. Run the system:"
echo "   python market_insight_system.py"
echo ""
echo "========================================"

#!/bin/bash
# Setup script for Epidemic Agent - pulls Ollama model and installs dependencies

set -e

echo "=== Epidemic Agent Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

echo "Python: $(python3 --version)"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing package in development mode..."
pip install -e ".[dev]"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
fi

echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!
sleep 3

echo "Pulling llama3.1:8b model..."
ollama pull llama3.1:8b

# Generate HMAC key if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Epidemic Agent Environment Variables
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
GEMINI_API_KEY=

# Generate with: openssl rand -hex 32
PICKLE_HMAC_KEY=$(openssl rand -hex 32)

COVID19INDIA_API=https://api.covid19india.org
COWIN_API=https://cdn-api.co-vin.in/api
EOF
    echo "Created .env with generated PICKLE_HMAC_KEY"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run the agent:"
echo "  source .venv/bin/activate"
echo "  python -m epidemic_agent run --help"
echo ""
echo "To launch dashboard:"
echo "  streamlit run src/epidemic_agent/dashboard/streamlit_app.py"
echo ""
echo "To fetch India data:"
echo "  python scripts/fetch_data.py --states \"Maharashtra,Kerala,Delhi\" --include-vaccination --include-demographics"
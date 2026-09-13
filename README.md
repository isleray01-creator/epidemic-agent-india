# Epidemic Response Agent — India

Agentic AI system for epidemic response planning and simulation in India.
Uses Mesa agent-based modeling, real-time data from covid19india.org, and local LLM (Ollama).

## Features

- **Agentic Loop**: Dynamic action selection, multi-step state tracking, adaptation via variant shock
- **Simulation**: Mesa agent-based model (district-level) + SEIR compartmental fallback
- **Real Data**: Fetches from covid19india.org, ICMR, CoWIN, Census
- **Local LLM**: Ollama (llama3.1:8b) with Gemini fallback
- **Memory**: ChromaDB vector store for historical decisions
- **Dashboard**: Real-time animated Plotly choropleth + replay slider
- **Persistence**: Trusted pickle with HMAC verification

## Quick Start

```bash
# 1. Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your keys (GEMINI_API_KEY, PICKLE_HMAC_KEY)

# 3. Pull Ollama model
ollama pull llama3.1:8b

# 4. Fetch India data
python scripts/fetch_data.py --states "Maharashtra,Kerala,Delhi,Karnataka,Tamil Nadu"

# 5. Run simulation
python -m epidemic_agent run --country india --days 60 --interventions contact_tracing

# 6. Launch Vercel React Web Application
cd aegis-biosurveillance-intelligence
npm install
npm run dev
```

## Project Structure

```
src/epidemic_agent/
├── config.py          # Configuration, weights, constants
├── state.py           # EpidemicState TypedDict
├── cli.py             # Command-line entry point
├── llm/               # LLM clients (Ollama, Gemini)
├── memory/            # ChromaDB vector store
├── tools/             # Agent tools (data, simulation, policy)
├── graph/             # LangGraph workflow
├── simulation/        # Mesa + SEIR models
├── dashboard/         # Streamlit animated dashboard
└── persistence/       # Trusted pickle storage
```

## Configuration

Key settings in `src/epidemic_agent/config.py`:

- **Objective weights**: deaths (0.45), economic_cost (0.30), social_cost (0.15), healthcare_strain (0.10)
- **Variants**: Pre-defined params for Wildtype, Delta, Omicron BA.1/2/5, XBB
- **Contact tracing**: efficiency=0.6, compliance=0.7, delay=2 days
- **Shock detection**: 15% deviation threshold

## Data Sources

| Source | API | Data |
|--------|-----|------|
| covid19india.org | https://api.covid19india.org | Cases, deaths, testing by state/district |
| CoWIN | https://cdn-api.co-vin.in/api | Vaccination data |
| Census 2011 | Local CSV | Population, age distribution |
| ICMR | https://icmr.gov.in | Testing capacity, serosurveys |

## License

MIT
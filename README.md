# Epidemic Response Agent — India

Agentic AI system for epidemic response planning and simulation in India.
Uses Mesa agent-based modeling, SEIR compartmental models, real-time data, and local LLM (Ollama).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EpiPulse React Frontend                  │
│              (Vercel / localhost:3000)                       │
│  Plague Inc-style HUD · India Choropleth Map · SEIR Graph  │
└──────────────────────────┬──────────────────────────────────┘
                           │ /api/*
┌──────────────────────────▼──────────────────────────────────┐
│                 FastAPI Bridge Server                        │
│                 (localhost:8000)                             │
│  /api/simulate · /api/workflow/run · /api/config/*          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Python Epidemic Agent Backend                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ LangGraph │ │  Mesa    │ │  SEIR    │ │  Validation  │  │
│  │ Workflow  │ │  Agent   │ │  ODE     │ │  Backtester  │  │
│  │ (9 nodes) │ │  Model   │ │  Model   │ │  Richards    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ LLM      │ │ Variant  │ │ Multi-   │ │  ChromaDB    │  │
│  │ Reasoning│ │ Learner  │ │ Agent    │ │  Memory      │  │
│  │ Ollama/  │ │ Diff.    │ │ Debate   │ │  Experience  │  │
│  │ Gemini   │ │ Evolut.  │ │ System   │ │  Replay      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Agentic Loop**: 9-node LangGraph workflow with dynamic adaptation, variant shock detection, and multi-agent debate
- **Simulation**: Mesa agent-based model (1M agents) + SEIR compartmental ODE per state
- **Real Data**: Fetches from covid19india.org with synthetic fallback, ICMR, CoWIN, Census
- **Local LLM**: Ollama (llama3.1:8b) primary, Gemini API fallback, rule-based degradation
- **Variant Learning**: Differential evolution optimizer fits R0, IFR, immune_escape from observed waves
- **Multi-Agent Debate**: Epidemiologist, Economist, Public Health agents debate intervention strategies
- **Memory**: ChromaDB vector store + JSON experience replay for historical decision similarity
- **Validation**: Richards curve fitter with cross-validation, ensemble backtesting, sensitivity analysis
- **Persistence**: Trusted pickle storage with HMAC signature verification
- **React Frontend**: Plague Inc-style HUD, interactive India map, SEIR trajectories, backend integration

## Quick Start

### Backend (Python)

```bash
# 1. Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your keys (GEMINI_API_KEY, PICKLE_HMAC_KEY)

# 3. Pull Ollama model (optional - works without LLM via rule-based fallback)
ollama pull llama3.1:8b

# 4. Fetch India data
python scripts/fetch_data.py --states "Maharashtra,Kerala,Delhi"

# 5. Run simulation via CLI
python -m epidemic_agent run --country india --days 60 --interventions contact_tracing

# 6. Start API server
python api_server.py
# Server runs at http://localhost:8000
```

### Frontend (React)

```bash
cd aegis-biosurveillance-intelligence
npm install
npm run dev
# Frontend runs at http://localhost:3000
# Automatically proxies /api requests to backend at :8000
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/config/variants` | GET | Variant parameters |
| `/api/config/states` | GET | State populations |
| `/api/simulate` | POST | Run SEIR/Mesa simulation |
| `/api/simulate/seir` | POST | SEIR simulation with per-state populations |
| `/api/workflow/run` | POST | Full 9-node agentic workflow |

## Project Structure

```
src/epidemic_agent/
├── config.py              # Configuration, weights, variant params
├── state.py               # EpidemicState TypedDict
├── cli.py                 # Command-line entry point
├── graph/
│   ├── workflow.py        # LangGraph StateGraph (9 nodes + adaptation loop)
│   ├── nodes.py           # Node functions (analyze, detect, reason, debate, simulate)
│   ├── agents.py          # Multi-agent debate system
│   ├── reasoning.py       # LLM + rule-based situation assessment
│   └── learning.py        # Adaptive learning module
├── simulation/
│   ├── mesa_model.py      # Mesa agent-based model (PersonAgent + SEIR dynamics)
│   ├── seir_model.py      # SEIR ODE solver (per-state simulation)
│   ├── variant.py         # VariantParameterLearner (differential evolution)
│   └── result.py          # SimulationResult dataclass
├── tools/
│   ├── registry.py        # LangChain StructuredTool registry
│   ├── data_fetcher.py    # India epidemic data fetchers
│   ├── simulator.py       # Simulation tool wrapper
│   ├── policy_eval.py     # Intervention policy evaluation
│   ├── shock_detector.py  # Variant shock detection
│   └── objective.py       # Multi-objective function
├── llm/client.py          # Ollama + Gemini fallback
├── memory/chroma_store.py # ChromaDB vector memory
├── persistence/           # Trusted pickle storage
└── validation/
    ├── backtester.py      # Cross-validation framework
    ├── richards_fitter.py # Richards curve fitting
    ├── sensitivity.py     # Sensitivity analysis
    └── uncertainty.py     # Uncertainty quantification

aegis-biosurveillance-intelligence/  # React Frontend (EpiPulse)
├── src/
│   ├── App.tsx            # Main app with routing
│   ├── main.tsx           # Entry point with ErrorBoundary
│   ├── components/        # IndiaMap, SEIRGraph, PlagueIncHUD, AuthModal
│   ├── views/             # Overview, Simulation, Analysis, Backtesting, Reports
│   ├── utils/
│   │   ├── backendApi.ts  # Python backend API client
│   │   ├── seirModel.ts   # Client-side SEIR model
│   │   └── epidemicPropagation.ts  # State-to-state spread model
│   └── data/              # State paths, simulation data
├── vite.config.ts         # Vite config with /api proxy to :8000
└── package.json
```

## Configuration

Key settings in `src/epidemic_agent/config.py`:

| Setting | Value | Description |
|---------|-------|-------------|
| Objective weights | deaths=0.45, economic=0.30, social=0.15, healthcare=0.10 | Multi-objective optimization |
| Variants | Wildtype, Delta, Omicron BA.1/2/5, XBB | Pre-defined epidemic parameters |
| Contact tracing | efficiency=0.6, compliance=0.7, delay=2 days | Default intervention params |
| Shock detection | 15% deviation threshold | Variant shock trigger |
| Max adaptation loops | 3 | Replanning iterations |
| Simulation step | 7 days | Days per workflow iteration |
| Mesa population cap | 1,000,000 | Agent-based model limit |

## Data Sources

| Source | API | Data |
|--------|-----|------|
| covid19india.org | api.covid19india.org | Cases, deaths, testing by state |
| CoWIN | cdn-api.co-vin.in | Vaccination data |
| Census 2011 | Local CSV | Population, demographics |
| ICMR | icmr.gov.in | Testing capacity, serosurveys |

## Validation Module

The system includes a comprehensive validation framework:

- **Richards Curve Fitter**: Fits epidemic curves using the Richards growth model with differential evolution
- **Cross-Validation**: Time-series split validation with configurable folds
- **Ensemble Testing**: Combines SEIR and Richards model predictions
- **Sensitivity Analysis**: Parameter perturbation analysis for R0, IFR, and intervention effectiveness
- **Uncertainty Quantification**: Monte Carlo sampling for confidence intervals

## License

MIT

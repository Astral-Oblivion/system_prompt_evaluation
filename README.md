# AI System Prompt Testing Tool

A tool to systematically test which sections of system prompts drive specific AI behaviors. The goal is to understand the relationship between prompt components and resulting AI outputs through automated evaluation and experimentation.

## Core Question
What parts of a system prompt actually matter for different AI behaviors?

## Technical Approach
- **Query Selection**: Design diverse test queries that expose behavioral differences between prompt configurations
- **Decomposition**: Work with prompts as a list of strings (each string is a section)
- **Evaluation Method**: Pre-compute all relevant prompt combinations in one API batch
- **One-Time Cost**: Single upfront batch execution, then unlimited free exploration
- **API Strategy**: Use cheapest models via OpenRouter (GPT-3.5-turbo/Claude Haiku) for cost efficiency
- **Iterative Validation**: Start with small-scale tests to validate approach before full batch execution
- **Data Management**: Local file storage with complete pre-computed dataset
- **Evaluation Metrics**: Ask Y/N questions to LLMs (models are not great at ranking/scoring without many examples)
- **Interface**: Instant-response web app reading from cached results

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the project root:
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**Get your OpenRouter API key**: 
1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Go to your API Keys section
3. Create a new key and copy it to your `.env` file

### 3. Create Required Directories
```bash
mkdir -p logs cached_results
```

### 4. Run the Application
```bash
streamlit run app.py
```

The web interface will open at `http://localhost:8501`

## Project Structure

```
system_prompt_evaluation/
├── app.py                  # Streamlit web interface
├── evaluation.py           # Core evaluation engine
├── run_evaluation.py       # Main evaluation script
├── retry_failed_evaluations.py # Error recovery tool
├── utils/
│   ├── llm_call.py        # Async OpenRouter API client
│   └── ui_helpers.py      # UI helper functions
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
├── logs/                  # API call logs and evaluation logs
└── cached_results/        # Pre-computed evaluation results
```

## Usage

### Basic Workflow
1. **Define your prompt sections** as a `List[str]` where each string is a section
2. **Create test queries** that will expose different behaviors  
3. **Define evaluation questions** as Y/N questions to assess responses
4. **Run batch evaluation** to pre-compute all combinations
5. **Explore results** instantly in the web interface

### Example
```python
from evaluation import PromptEvaluator

# Define prompt sections
prompt_sections = [
    "You are a helpful AI assistant.",
    "Always be polite and respectful.", 
    "Provide detailed explanations when possible.",
    "If you're unsure, say so clearly."
]

# Define test queries
test_queries = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms."
]

# Define evaluation questions  
evaluation_questions = [
    "Does the response show politeness?",
    "Does the response provide detailed explanations?"
]

# Run evaluation
evaluator = PromptEvaluator()
results = await evaluator.run_batch_evaluation(
    prompt_sections, test_queries, evaluation_questions
)
```

## Features

### Current
- ✅ Async OpenRouter API integration
- ✅ Comprehensive API call logging
- ✅ Streamlit web interface skeleton
- ✅ Batch evaluation framework
- ✅ Cached results system

### Completed Features
- ✅ Interactive prompt builder with section toggles
- ✅ Section impact analysis with radar/bar charts
- ✅ Behavioral pattern detection across 6 dimensions
- ✅ Smart prompt combination generation
- ✅ Error recovery and retry mechanisms

## Design Philosophy

**One-time computation cost, unlimited free exploration**

The tool is designed to front-load the computational cost by pre-computing all relevant prompt combinations in a single batch API run. Once this is complete, you can explore the results instantly without additional API costs.

## Tech Stack

- **Streamlit**: Web interface
- **httpx**: Async HTTP client for API calls
- **pandas**: Data manipulation and analysis  
- **loguru**: Comprehensive logging
- **OpenRouter**: Cost-effective LLM API access

## License

MIT License

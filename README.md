# AI System Prompt Testing Tool

Test which sections of system prompts actually matter for AI behavior through automated evaluation and interactive analysis.

## Features

- **Toggleable Sections**: Interactive checkboxes to toggle prompt sections on/off
- **Custom Prompt Analyzer**: AI-powered decomposition of any system prompt into testable sections
- **Flexible Evaluation**: Y/N questions (fast) or 0-100 scoring (detailed) across 6 dimensions
- **Interactive Charts**: Radar and bar charts with real-time filtering
- **Batch Processing**: Up to 500 concurrent API calls with automatic retry
- **Response Metrics**: Word count, readability, and complexity analysis

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API key**
   ```bash
   echo "OPENROUTER_API_KEY=your_key_here" > .env
   ```

3. **Run the app**
   ```bash
   streamlit run app.py
   ```

## Usage

### Web Interface
- **Toggleable Sections**: Use pre-built sections or switch to custom analyzed sections
- **Custom Analyzer**: Paste any prompt → analyze → run evaluation → toggle results

### Command Line
```bash
python run_evaluation.py    # Interactive evaluation with 50 test queries
python retry_failed_evaluations.py  # Retry failed API calls
```

## Tech Stack

- Streamlit, pandas, plotly
- OpenRouter API (GPT-4o-mini)
- Async processing with httpx
- Text analysis with textstat
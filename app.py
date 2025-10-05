"""
Streamlit UI for Prompt Testing Tool - Clean Version

A web interface for exploring cached prompt evaluation results.
"""
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from evaluation import PromptEvaluator
from loguru import logger
from utils.ui_helpers import (
    extract_dimension_scores, create_radar_chart, create_bar_chart,
    create_response_metrics_charts, extract_response_metrics_summary
)
import asyncio

load_dotenv()
try:
    from utils.prompt_analyzer import decompose_system_prompt
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
    from prompt_analyzer import decompose_system_prompt

st.set_page_config(
    page_title="Prompt Testing Tool",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        background-color: #0a0a0a;
        color: #fafafa;
        font-family: 'Inter', sans-serif;
    }
    
    .css-1d391kg, .css-1cypcdb {
        background-color: #18181b !important;
        border-right: 1px solid #27272a !important;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    h1 {
        color: #fafafa !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    .css-1d391kg h2, .css-1cypcdb h2 {
        color: #fafafa !important;
        font-weight: 600 !important;
        font-size: 1.125rem !important;
    }
    
    .stCheckbox > label {
        color: #d4d4d8 !important;
        font-size: 0.875rem !important;
        line-height: 1.5 !important;
    }
    
    [data-testid="metric-container"] {
        display: none;
    }
    
    .stSuccess {
        background-color: rgba(5, 46, 22, 0.2) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        color: #4ade80 !important;
        border-radius: 12px !important;
    }
    
    .stWarning {
        background-color: rgba(69, 26, 3, 0.2) !important;
        border: 1px solid rgba(251, 146, 60, 0.3) !important;
        color: #fb923c !important;
        border-radius: 12px !important;
    }
    
    .stInfo {
        background-color: rgba(5, 46, 22, 0.2) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        color: #4ade80 !important;
        border-radius: 12px !important;
    }
    
    .stSelectbox > div > div {
        background-color: #27272a !important;
        border-color: #3f3f46 !important;
        color: #fafafa !important;
    }
    
    .css-1y4p8pa {
        padding-top: 1rem;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stSelectbox input {
        caret-color: transparent !important;
        cursor: pointer !important;
    }
    
    .stSelectbox input:focus {
        caret-color: transparent !important;
        outline: none !important;
    }
    
    hr {
        display: none !important;
    }
    
    .stMarkdown hr {
        display: none !important;
    }
    
    .element-container:has(hr) {
        display: none !important;
    }
    
    .stColumns > div:first-child > div > div:empty {
        display: none !important;
    }
    
    div[data-testid="stMarkdownContainer"] > div:empty {
        display: none !important;
    }
    
    div[style*="background: rgba(39, 39, 42, 0.5)"]:empty {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Configure logging
logger.add("logs/app.log", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


@st.cache_data
def load_cached_results(use_original_dataset=False):
    """Load cached evaluation results with caching for performance"""
    evaluator = PromptEvaluator()
    try:
        if use_original_dataset:
            # Load the original large dataset for default sections
            df = evaluator.load_cached_results("cached_results/full_evaluation_backup.csv")
            logger.info(f"Loaded {len(df)} original cached results")
        else:
            # Load current results (custom evaluations)
            df = evaluator.load_cached_results()
            logger.info(f"Loaded {len(df)} current cached results")
        return df
    except Exception as e:
        logger.error(f"Failed to load cached results: {e}")
        return pd.DataFrame()


def render_metric_card(dimension: str, score: float):
    """Render a single metric card"""
    # Determine rating and color
    if score >= 90:
        rating, color = "Excellent", "#22c55e"
        bg_gradient = "linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(34, 197, 94, 0.05) 100%)"
        border_color = "rgba(34, 197, 94, 0.4)"
        shadow = "0 4px 16px rgba(34, 197, 94, 0.15)"
    elif score >= 80:
        rating, color = "Good", "#22c55e"
        bg_gradient = "linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(34, 197, 94, 0.04) 100%)"
        border_color = "rgba(34, 197, 94, 0.3)"
        shadow = "0 4px 16px rgba(34, 197, 94, 0.1)"
    elif score >= 70:
        rating, color = "Fair", "#f59e0b"
        bg_gradient = "linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%)"
        border_color = "rgba(245, 158, 11, 0.3)"
        shadow = "0 4px 16px rgba(245, 158, 11, 0.1)"
    elif score > 0:
        rating, color = "Poor", "#ef4444"
        bg_gradient = "linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(239, 68, 68, 0.04) 100%)"
        border_color = "rgba(239, 68, 68, 0.3)"
        shadow = "0 4px 16px rgba(239, 68, 68, 0.1)"
    else:
        rating, color = "No data", "#71717a"
        bg_gradient = "linear-gradient(135deg, rgba(113, 113, 122, 0.08) 0%, rgba(113, 113, 122, 0.02) 100%)"
        border_color = "rgba(113, 113, 122, 0.2)"
        shadow = "0 4px 16px rgba(0, 0, 0, 0.1)"
    
    st.markdown(f"""
    <div style="background: {bg_gradient}; border: 1px solid {border_color}; border-radius: 12px; 
                padding: 16px 8px; margin-bottom: 16px; height: 140px; display: flex; 
                flex-direction: column; justify-content: space-between; box-shadow: {shadow}; 
                transition: all 0.3s ease; animation: fadeIn 0.5s ease;">
        <h3 style="margin: 0; font-size: 0.65rem; font-weight: 600; color: #a1a1aa; 
                   text-align: center; line-height: 1.2; letter-spacing: 0.02em; 
                   text-transform: uppercase; word-wrap: break-word; overflow-wrap: break-word; 
                   hyphens: auto;">{dimension}</h3>
        <div style="text-align: center; margin: 4px 0; flex-grow: 1; display: flex; 
                    align-items: center; justify-content: center;">
            <span style="font-size: 2rem; font-weight: 700; color: #fafafa; line-height: 1; 
                         letter-spacing: -0.02em;">{score:.0f}</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: center; gap: 4px; 
                    padding: 4px 8px; background: rgba(0, 0, 0, 0.2); border-radius: 6px; 
                    min-height: 24px;">
            <svg width="10" height="10" fill="none" stroke="currentColor" viewBox="0 0 24 24" 
                 style="color: {color}; flex-shrink: 0;" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
            </svg>
            <span style="font-size: 0.7rem; font-weight: 600; color: {color}; 
                         letter-spacing: 0.01em; white-space: nowrap;">{rating}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main Streamlit application"""
    st.title("Prompt Testing Tool")
    
    # Determine which dataset to load based on whether we have custom sections
    if 'custom_sections' not in st.session_state:
        st.session_state.custom_sections = []
    
    # Load appropriate dataset
    if st.session_state.custom_sections:
        # Load custom evaluation results
        results_df = load_cached_results(use_original_dataset=False)
    else:
        # Load original dataset for default sections
        results_df = load_cached_results(use_original_dataset=True)
    
    # Sidebar
    with st.sidebar:
        # Header
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="color: #71717a;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
            <h2 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #fafafa;">Prompt Builder</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple toggle with tabs approach
        st.markdown("**MODE**")
        
        # Create two columns for toggle buttons
        col1, col2 = st.columns(2)
        
        # Initialize mode if not set
        if 'interface_mode' not in st.session_state:
            st.session_state.interface_mode = "Toggleable Sections"
        
        # Custom CSS for better button styling with clear active state
        st.markdown("""
        <style>
        /* Secondary (inactive) buttons */
        .stButton > button[kind="secondary"] {
            width: 100%;
            border-radius: 6px;
            border: 1px solid #404040;
            background-color: #2d2d2d;
            color: #888;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton > button[kind="secondary"]:hover {
            background-color: #3d3d3d;
            border-color: #505050;
            color: #aaa;
        }
        
        /* Primary (active) buttons */
        .stButton > button[kind="primary"] {
            width: 100%;
            border-radius: 6px;
            border: 1px solid #3b82f6;
            background-color: #3b82f6;
            color: white;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #2563eb;
            border-color: #2563eb;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with col1:
            if st.button(
                "Toggleable Sections",
                key="btn_default",
                use_container_width=True,
                type="primary" if st.session_state.interface_mode == "Toggleable Sections" else "secondary"
            ):
                st.session_state.interface_mode = "Toggleable Sections"
                st.rerun()
        
        with col2:
            if st.button(
                "Custom Analyzer", 
                key="btn_custom",
                use_container_width=True,
                type="primary" if st.session_state.interface_mode == "Custom Prompt Analyzer" else "secondary"
            ):
                st.session_state.interface_mode = "Custom Prompt Analyzer"
                st.rerun()
        
        mode = st.session_state.interface_mode
        
        st.markdown("<hr style='border: 1px solid #27272a; margin: 16px 0;'>", unsafe_allow_html=True)
        
        if 'custom_sections' not in st.session_state:
            st.session_state.custom_sections = []
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = None
        if 'use_custom_sections' not in st.session_state:
            st.session_state.use_custom_sections = False

        if mode == "Toggleable Sections":
            # Default interface - show custom sections if available, otherwise pre-built sections
            if not results_df.empty and 'system_prompt' in results_df.columns:
                # Check if we have custom sections from a previous analysis
                if st.session_state.custom_sections:
                    sections_to_use = st.session_state.custom_sections
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**Custom Analyzed Sections:**")
                        st.caption("These sections were extracted from your analyzed prompt. Toggle them to see performance differences.")
                    with col2:
                        if st.button("Reset to Default", key="reset_sections", help="Switch back to pre-built sections"):
                            st.session_state.custom_sections = []
                            st.session_state.analysis_result = None
                            st.session_state.use_custom_sections = False
                            st.rerun()
                else:
                    sections_to_use = [
                        "You are Claude, a helpful AI assistant created by Anthropic.",
                        "Be direct and concise. Avoid unnecessary flattery like 'great question' or 'excellent idea'.",
                        "Think critically and provide balanced perspectives. Don't just agree with everything.",
                        "When uncertain, acknowledge limitations and suggest ways to find better information.",
                        "Use examples and analogies to make complex topics more understandable.",
                        "Be encouraging but realistic about challenges and potential outcomes."
                    ]
                    st.markdown("**Default Prompt Sections:**")
                    st.caption("Pre-built sections for testing. Switch to Custom Analyzer mode to analyze your own prompt.")
                
                selected_sections = []
                section_states = {}
                
                for i, section in enumerate(sections_to_use):
                    key = f"section_{i}"
                    is_selected = st.checkbox(section, value=True, key=key)
                    section_states[key] = is_selected
                    if is_selected:
                        selected_sections.append(section)
                
                if selected_sections:
                    current_prompt_text = '\n\n'.join(selected_sections)
                    current_combination = current_prompt_text
                else:
                    current_combination = None
            else:
                st.info("No cached data available. Run a batch evaluation first.")
                selected_sections = []
                current_combination = None
        
        
        elif mode == "Custom Prompt Analyzer":
            # Custom prompt analyzer interface
            st.markdown("**Custom Prompt Analysis:**")
            
            custom_prompt = st.text_area(
                "Paste your system prompt here:",
                height=150,
                placeholder="Paste a system prompt to analyze and test...",
                key="custom_prompt_input"
            )
            
            # Analysis mode toggle
            exclude_factual = st.checkbox(
                "Behavioral instructions only (exclude factual content)",
                value=True,
                help="If checked, only extracts behavioral instructions. If unchecked, decomposes ALL content into sections."
            )
        
            if st.button("Analyze Prompt", disabled=not custom_prompt.strip()):
                if custom_prompt.strip():
                    # Clear previous evaluation state when analyzing new prompt
                    for key in list(st.session_state.keys()):
                        if 'eval' in key.lower():
                            del st.session_state[key]
                    
                    with st.spinner("Analyzing prompt..."):
                        try:
                            result = asyncio.run(decompose_system_prompt(custom_prompt.strip(), exclude_factual=exclude_factual))
                            st.session_state.analysis_result = result
                            if result['success']:
                                st.session_state.custom_sections = result['sections']
                                st.session_state.use_custom_sections = True
                                st.success(f"Analyzed into {len(result['sections'])} sections")
                            else:
                                st.error(f"Analysis failed: {result['analysis']}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            
            # Display analysis results
            if st.session_state.analysis_result and st.session_state.analysis_result['success']:
                # Display extracted sections
                st.markdown("**Extracted Sections:**")
                for i, section in enumerate(st.session_state.analysis_result['sections'], 1):
                    st.markdown(f"**{i}.** {section}")
                
                # Toggle to use custom sections
                use_custom = st.checkbox(
                    "Use these sections for evaluation", 
                    value=st.session_state.use_custom_sections,
                    key="use_custom_toggle"
                )
                st.session_state.use_custom_sections = use_custom
                
                # Run evaluation button
                if st.button("Run Evaluation on These Sections", type="primary"):
                    st.session_state.show_eval_config = True
            
            # Set variables for main interface
            selected_sections = st.session_state.custom_sections if st.session_state.use_custom_sections else []
            current_combination = '\n\n'.join(selected_sections) if selected_sections else None
        
        st.markdown("<hr style='border: 1px solid #27272a; margin: 24px 0;'>", unsafe_allow_html=True)
        
        # Options
        st.markdown("""
        <div style="margin-top: 24px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <div style="width: 4px; height: 4px; border-radius: 50%; background-color: #6366f1;"></div>
                <span style="font-size: 0.75rem; font-weight: 500; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Options</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        show_raw_data = st.checkbox("Show Raw Data", value=False)
        
        # Status
        st.markdown("""
        <div style="margin-top: 24px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <div style="width: 4px; height: 4px; border-radius: 50%; background-color: #22c55e;"></div>
                <span style="font-size: 0.75rem; font-weight: 500; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Status</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if os.path.exists("cached_results/"):
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(5, 46, 22, 0.3); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 8px;">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="color: #22c55e;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                <span style="font-size: 0.875rem; color: #4ade80; font-weight: 500;">Data loaded</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(69, 26, 3, 0.3); border: 1px solid rgba(251, 146, 60, 0.5); border-radius: 8px;">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="color: #f59e0b;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
                <span style="font-size: 0.875rem; color: #fb923c; font-weight: 500;">No data</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Main content
    if results_df.empty:
        st.info("""
        **No evaluation results found.**
        
        To get started:
        1. Set up your `.env` file with `OPENROUTER_API_KEY`
        2. Run a batch evaluation using `evaluation.py`
        3. Results will appear here automatically
        
        The cached results will enable instant exploration of prompt effectiveness patterns.
        """)
        return
    
    # Filter data
    filtered_df = results_df
    if current_combination is not None:
        current_prompt_text = current_combination
        filtered_df = results_df[results_df['system_prompt'] == current_prompt_text]
        if filtered_df.empty:
            filtered_df = results_df
    
    # Status banner
    if current_combination is not None:
        current_prompt_text = current_combination
        matching_df = results_df[results_df['system_prompt'] == current_prompt_text]
        if not matching_df.empty:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(5, 46, 22, 0.3); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 8px; margin-bottom: 24px;">
                <div style="width: 6px; height: 6px; border-radius: 50%; background-color: #22c55e; animation: pulse 2s infinite;"></div>
                <span style="font-size: 0.875rem; font-weight: 500; color: #4ade80;">Analyzing {len(matching_df)} evaluations for your prompt selection</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(69, 26, 3, 0.3); border: 1px solid rgba(251, 146, 60, 0.5); border-radius: 8px; margin-bottom: 24px;">
                <div style="width: 6px; height: 6px; border-radius: 50%; background-color: #f59e0b;"></div>
                <span style="font-size: 0.875rem; font-weight: 500; color: #fb923c;">No data for this combination. Showing all {len(results_df)} results.</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; background-color: rgba(5, 46, 22, 0.3); border: 1px solid rgba(34, 197, 94, 0.5); border-radius: 8px; margin-bottom: 24px;">
            <div style="width: 6px; height: 6px; border-radius: 50%; background-color: #22c55e;"></div>
            <span style="font-size: 0.875rem; font-weight: 500; color: #4ade80;">Showing all {len(results_df)} evaluation results</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Calculate and display metrics
    if 'evaluation_question' in filtered_df.columns and 'evaluation_score' in filtered_df.columns and len(filtered_df) > 0:
        avg_scores = extract_dimension_scores(filtered_df)
        
        if any(v > 0 for v in avg_scores.values()):
            # Metric cards in fixed order
            fixed_order = ['Helpfulness', 'Directness', 'Critical Thinking', 'Accuracy', 'Tone', 'Safety & Ethics']
            cols = st.columns(6)
            
            for i, dim in enumerate(fixed_order):
                with cols[i]:
                    score = avg_scores.get(dim, 0)
                    render_metric_card(dim, score)
            
            # Charts
            st.markdown("""
            <div style="background: rgba(39, 39, 42, 0.5); border: 1px solid #27272a; border-radius: 12px; padding: 24px; margin-top: 32px;">
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown("""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                    <div style="width: 4px; height: 4px; border-radius: 50%; background-color: #3b82f6;"></div>
                    <span style="font-size: 0.875rem; font-weight: 500; color: #d4d4d8;">Chart Type</span>
                </div>
                """, unsafe_allow_html=True)
                chart_type = st.selectbox("", ["Bar Chart", "Radar Chart"], key="chart_type", label_visibility="collapsed")
            
            # Get full prompt comparison data if available
            full_avg_scores = None
            if not results_df.empty:
                # Find the full prompt (all sections combined)
                unique_prompts = results_df['system_prompt'].unique()
                full_prompt = max(unique_prompts, key=len) if unique_prompts.size > 0 else None
                
                if full_prompt:
                    full_prompt_df = results_df[results_df['system_prompt'] == full_prompt]
                    if not full_prompt_df.empty:
                        full_avg_scores = extract_dimension_scores(full_prompt_df)
            
            # Create and display chart
            if chart_type == "Radar Chart":
                fig = create_radar_chart(avg_scores, full_avg_scores)
            else:
                fig = create_bar_chart(avg_scores, full_avg_scores)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Missing dimensions info
            missing_dims = [dim for dim in ['Helpfulness', 'Directness', 'Critical Thinking', 'Accuracy', 'Tone', 'Safety & Ethics'] if avg_scores[dim] == 0]
            if missing_dims:
                st.caption(f"Missing data for: {', '.join(missing_dims)}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Response Characteristics Section
            st.markdown("---")
            st.markdown("### Response Characteristics")
            
            # Get response metrics summary
            metrics_summary = extract_response_metrics_summary(filtered_df)
            
            # Display metrics in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Average Word Count",
                    value=f"{metrics_summary['avg_word_count']:.0f}",
                    help="Average number of words per response"
                )
            
            with col2:
                st.metric(
                    label="Readability Score",
                    value=f"{metrics_summary['avg_readability']:.1f}",
                    help="Flesch Reading Ease (0-100, higher = easier to read)"
                )
            
            with col3:
                st.metric(
                    label="Grade Level",
                    value=f"{metrics_summary['avg_grade_level']:.1f}",
                    help="Flesch-Kincaid Grade Level (reading difficulty)"
                )
            
            # Create and display response metrics charts
            if len(filtered_df) > 0:
                word_chart, readability_chart = create_response_metrics_charts(filtered_df, results_df)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(word_chart, use_container_width=True)
                
                with col2:
                    st.plotly_chart(readability_chart, use_container_width=True)
        else:
            st.info("No evaluation data available")
    
    # Raw data
    if show_raw_data:
        st.subheader("Raw Data")
        st.dataframe(filtered_df, use_container_width=True)
    
    # Bottom caption
    if current_combination is not None:
        current_prompt_text = current_combination
        matching_df = results_df[results_df['system_prompt'] == current_prompt_text]
        if not matching_df.empty:
            st.caption(f"Showing {len(matching_df)} results for current prompt selection")
        else:
            st.caption(f"No results for this combination. Showing all {len(results_df)} results.")
    else:
        st.caption(f"Showing all {len(results_df)} evaluation results")


# Evaluation Configuration Modal
if 'show_eval_config' not in st.session_state:
    st.session_state.show_eval_config = False

if st.session_state.show_eval_config:
    st.markdown("---")
    st.markdown("### Run Evaluation Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Evaluation Type:**")
        eval_type = st.radio(
            "Choose evaluation method:",
            ["Y/N Questions (Fast & Cheap)", "0-100 Scoring (Detailed & Expensive)"],
            key="eval_type_radio"
        )
        
        use_yn = eval_type.startswith("Y/N")
        
        if use_yn:
            st.info("6 Y/N questions - Quick evaluation")
        else:
            st.info("6 detailed scoring dimensions (0-100)")
    
    with col2:
        st.markdown("**Number of Test Queries:**")
        num_queries = st.selectbox(
            "How many test queries to run:",
            [5, 10, 15, 20, 25, 30, 40, 50],
            index=1,  # Default to 10
            key="num_queries_select"
        )
        
        st.markdown("**Batch Size:**")
        batch_size = st.selectbox(
            "Concurrent evaluations per batch:",
            [10, 20, 30, 50, 100, 150, 200, 300, 500],
            index=6,  # Default to 200
            key="batch_size_select",
            help="Higher = faster but more API load. Lower = slower but more stable. Max 500 for maximum throughput."
        )
        
        # Cost estimation
        if st.session_state.custom_sections:
            from itertools import combinations
            n_sections = len(st.session_state.custom_sections)
            n_combinations = sum(1 for r in range(1, n_sections + 1) 
                               for combo in combinations(range(n_sections), r))
            n_questions = 6
            total_calls = n_combinations * num_queries * n_questions * 2
            # GPT-4o-mini pricing: $0.000150/1K input tokens, $0.000600/1K output tokens
            estimated_cost = total_calls * 0.000150 * 0.2 + total_calls * 0.000600 * 0.1
            
            st.info(f"Estimated cost: ~${estimated_cost:.3f}")
            st.caption(f"~{total_calls} API calls | {n_combinations} combinations")
    
    col3, col4, col5 = st.columns([1, 1, 1])
    
    with col3:
        if st.button("Cancel", key="cancel_eval"):
            st.session_state.show_eval_config = False
            st.rerun()
    
    with col5:
        if st.button("Start Evaluation", type="primary", key="start_eval"):
            if st.session_state.get('evaluation_complete', False):
                # Clear the completion flag and allow new evaluation
                st.session_state.evaluation_complete = False
                st.info("Starting new evaluation...")
            
            if st.session_state.custom_sections:
                st.session_state.eval_running = True
                st.session_state.eval_config = {
                    'sections': st.session_state.custom_sections,
                    'use_yn': use_yn,
                    'num_queries': num_queries,
                    'batch_size': batch_size
                }
                st.session_state.show_eval_config = False
                st.rerun()
            else:
                st.error("No custom sections available to evaluate!")

# Run Evaluation
if 'eval_running' not in st.session_state:
    st.session_state.eval_running = False

if st.session_state.eval_running and not st.session_state.get('evaluation_complete', False):
    st.markdown("---")
    st.markdown("### Running Evaluation...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Define helper function
    def update_status(msg):
        status_text.text(msg)
    
    # Import evaluation system
    try:
        from evaluation import PromptEvaluator
        from run_evaluation import all_test_queries, yn_evaluation_questions, detailed_evaluation_questions
        import pandas as pd
        
        # Get evaluation config
        config = st.session_state.eval_config
        sections = config['sections']
        use_yn = config['use_yn']
        num_queries = config['num_queries']
        
        # Get test queries and evaluation questions
        test_queries = all_test_queries[:num_queries]
        
        if use_yn:
            evaluation_questions = yn_evaluation_questions
        else:
            evaluation_questions = detailed_evaluation_questions
        
        update_status(f"Using {len(test_queries)} test queries and {len(evaluation_questions)} evaluation questions")
        progress_bar.progress(10)
        
        # Initialize evaluator
        evaluator = PromptEvaluator(model_name="openai/gpt-4o-mini")
        
        # Run the existing batch evaluation method
        update_status("Starting batch evaluation...")
        progress_bar.progress(20)
        
        result_df = asyncio.run(evaluator.run_batch_evaluation(
            prompt_sections=sections,
            test_queries=test_queries,
            evaluation_questions=evaluation_questions
        ))
        
        progress_bar.progress(100)
        update_status("Evaluation completed!")
        
        # Create result summary
        successful_results = len(result_df[~result_df.get('success', pd.Series([True]*len(result_df))).isna()])
        failed_results = len(result_df) - successful_results
        
        # Calculate combinations tested
        from itertools import combinations
        n_sections = len(sections)
        n_combinations = sum(1 for r in range(1, n_sections + 1) 
                           for combo in combinations(range(n_sections), r))
        
        result = {
            'success': True,
            'total_evaluations': len(result_df),
            'successful_evaluations': successful_results,
            'failed_evaluations': failed_results,
            'combinations_tested': n_combinations,
            'results_saved_to': 'batch_evaluation.csv',
            'evaluation_type': 'Y/N Questions' if use_yn else '0-100 Scoring'
        }
        
        if result['success']:
            st.success(f"""Evaluation completed successfully!
            
**Results:**
- Total evaluations: {result['total_evaluations']}
- Successful: {result['successful_evaluations']}
- Failed: {result['failed_evaluations']}
- Combinations tested: {result['combinations_tested']}
- Evaluation type: {result['evaluation_type']}
- Results saved to: `{result['results_saved_to']}`

**Results are now available! Refresh the page manually to see the charts.**""")
            
            # Immediately clear cache and set completion flag
            load_cached_results.clear()
            st.session_state.evaluation_complete = True
            st.info("Please refresh your browser page (F5 or Ctrl+R) to see the evaluation results in the charts below.")
        else:
            st.error(f"Evaluation failed: {result.get('error', 'Unknown error')}")
            st.session_state.eval_running = False
        
        # Nuclear option - clear ALL eval-related state to prevent any restart
        for key in list(st.session_state.keys()):
            if 'eval' in key.lower() and key != 'evaluation_complete':
                del st.session_state[key]
        
    except Exception as e:
        st.error(f"Evaluation failed: {str(e)}")
        st.session_state.eval_running = False


if __name__ == "__main__":
    main()

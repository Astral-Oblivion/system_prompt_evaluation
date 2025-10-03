"""
UI Components for Streamlit Prompt Testing Tool

Reusable UI components to keep the main app clean and organized.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Tuple, Optional


def render_status_indicator(status: str, message: str, icon_path: str) -> None:
    """Render a status indicator with icon and message"""
    colors = {
        "success": {
            "bg": "rgba(5, 46, 22, 0.3)",
            "border": "rgba(34, 197, 94, 0.5)", 
            "icon": "#22c55e",
            "text": "#4ade80"
        },
        "warning": {
            "bg": "rgba(69, 26, 3, 0.3)",
            "border": "rgba(251, 146, 60, 0.5)",
            "icon": "#f59e0b", 
            "text": "#fb923c"
        }
    }
    
    color_scheme = colors.get(status, colors["success"])
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 8px; padding: 12px 16px; 
                background-color: {color_scheme['bg']}; border: 1px solid {color_scheme['border']}; 
                border-radius: 8px;">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" 
             style="color: {color_scheme['icon']};">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{icon_path}"/>
        </svg>
        <span style="font-size: 0.875rem; color: {color_scheme['text']}; font-weight: 500;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, color: str = "#6366f1") -> None:
    """Render a section header with colored dot indicator"""
    st.markdown(f"""
    <div style="margin-top: 24px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <div style="width: 4px; height: 4px; border-radius: 50%; background-color: {color};"></div>
            <span style="font-size: 0.75rem; font-weight: 500; color: #71717a; 
                         text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_header() -> None:
    """Render the sidebar header with icon"""
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="color: #71717a;">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
        <h2 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #fafafa;">Prompt Builder</h2>
    </div>
    """, unsafe_allow_html=True)


def get_rating_config(score: float) -> Dict[str, str]:
    """Get rating configuration based on score"""
    if score >= 90:
        return {
            "rating": "Excellent",
            "color": "#22c55e",
            "bg_gradient": "linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(34, 197, 94, 0.05) 100%)",
            "border_color": "rgba(34, 197, 94, 0.4)",
            "shadow": "0 4px 16px rgba(34, 197, 94, 0.15)"
        }
    elif score >= 80:
        return {
            "rating": "Good",
            "color": "#22c55e", 
            "bg_gradient": "linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(34, 197, 94, 0.04) 100%)",
            "border_color": "rgba(34, 197, 94, 0.3)",
            "shadow": "0 4px 16px rgba(34, 197, 94, 0.1)"
        }
    elif score >= 70:
        return {
            "rating": "Fair",
            "color": "#f59e0b",
            "bg_gradient": "linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%)",
            "border_color": "rgba(245, 158, 11, 0.3)",
            "shadow": "0 4px 16px rgba(245, 158, 11, 0.1)"
        }
    elif score > 0:
        return {
            "rating": "Poor",
            "color": "#ef4444",
            "bg_gradient": "linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(239, 68, 68, 0.04) 100%)",
            "border_color": "rgba(239, 68, 68, 0.3)",
            "shadow": "0 4px 16px rgba(239, 68, 68, 0.1)"
        }
    else:
        return {
            "rating": "No data",
            "color": "#71717a",
            "bg_gradient": "linear-gradient(135deg, rgba(113, 113, 122, 0.08) 0%, rgba(113, 113, 122, 0.02) 100%)",
            "border_color": "rgba(113, 113, 122, 0.2)",
            "shadow": "0 4px 16px rgba(0, 0, 0, 0.1)"
        }


def render_metric_card(dimension: str, score: float) -> None:
    """Render a single metric card with enhanced styling"""
    config = get_rating_config(score)
    
    st.markdown(f"""
    <div style="background: {config['bg_gradient']}; border: 1px solid {config['border_color']}; 
                border-radius: 12px; padding: 16px 8px; margin-bottom: 16px; height: 140px; 
                display: flex; flex-direction: column; justify-content: space-between; 
                box-shadow: {config['shadow']}; transition: all 0.3s ease; animation: fadeIn 0.5s ease;">
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
                 style="color: {config['color']}; flex-shrink: 0;" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
            </svg>
            <span style="font-size: 0.7rem; font-weight: 600; color: {config['color']}; 
                         letter-spacing: 0.01em; white-space: nowrap;">{config['rating']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def extract_dimension_scores(df: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate dimension scores from evaluation data"""
    dimension_scores = {}
    
    for _, row in df.iterrows():
        question = row['evaluation_question']
        score = row['evaluation_score']
        
        # Skip failed evaluations
        if pd.isna(score) or score is None or score == '':
            continue
        
        # Convert to float
        try:
            score = float(score)
        except (ValueError, TypeError):
            continue
        
        # Extract dimension name
        if 'HELPFULNESS' in question:
            dimension_scores['Helpfulness'] = dimension_scores.get('Helpfulness', []) + [score]
        elif 'DIRECTNESS' in question:
            dimension_scores['Directness'] = dimension_scores.get('Directness', []) + [score]
        elif 'CRITICAL THINKING' in question:
            dimension_scores['Critical Thinking'] = dimension_scores.get('Critical Thinking', []) + [score]
        elif 'ACCURACY' in question:
            dimension_scores['Accuracy'] = dimension_scores.get('Accuracy', []) + [score]
        elif 'TONE APPROPRIATENESS' in question:
            dimension_scores['Tone'] = dimension_scores.get('Tone', []) + [score]
        elif 'SAFETY' in question and 'ETHICS' in question:
            dimension_scores['Safety & Ethics'] = dimension_scores.get('Safety & Ethics', []) + [score]
    
    # Calculate averages
    all_dimensions = ['Helpfulness', 'Directness', 'Critical Thinking', 'Accuracy', 'Tone', 'Safety & Ethics']
    avg_scores = {}
    
    for dim in all_dimensions:
        if dim in dimension_scores and dimension_scores[dim]:
            avg_scores[dim] = sum(dimension_scores[dim]) / len(dimension_scores[dim])
        else:
            avg_scores[dim] = 0
    
    return avg_scores


def render_prompt_sections(default_sections: List[str]) -> Tuple[List[str], Optional[tuple]]:
    """Render prompt section checkboxes and return selected sections"""
    selected_sections = []
    section_states = {}
    
    for i, section in enumerate(default_sections):
        key = f"section_{i}"
        is_selected = st.checkbox(section, value=True, key=key)
        section_states[key] = is_selected
        if is_selected:
            selected_sections.append(section)
    
    # Calculate combination index
    if selected_sections:
        current_combination = tuple(i for i, section in enumerate(default_sections) 
                                  if section_states.get(f"section_{i}", False))
    else:
        current_combination = None
    
    return selected_sections, current_combination

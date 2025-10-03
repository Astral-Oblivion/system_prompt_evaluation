"""
UI Helper functions for Streamlit app - keeps main app clean
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Tuple, Optional


def extract_dimension_scores(df: pd.DataFrame) -> Dict[str, float]:
    """Extract and calculate dimension scores from evaluation data"""
    dimension_scores = {}
    
    for _, row in df.iterrows():
        question = row['evaluation_question']
        score = row['evaluation_score']
        
        # Skip failed evaluations
        if pd.isna(score) or score is None or score == '':
            continue
        
        try:
            score = float(score)
        except (ValueError, TypeError):
            continue
        
        # Extract dimension name (handle both 0-100 format and Y/N format)
        question_upper = question.upper()
        if 'HELPFULNESS' in question_upper or 'HELPFUL' in question_upper:
            dimension_scores['Helpfulness'] = dimension_scores.get('Helpfulness', []) + [score]
        elif 'DIRECTNESS' in question_upper or 'DIRECT' in question_upper:
            dimension_scores['Directness'] = dimension_scores.get('Directness', []) + [score]
        elif 'CRITICAL THINKING' in question_upper or 'CRITICAL' in question_upper:
            dimension_scores['Critical Thinking'] = dimension_scores.get('Critical Thinking', []) + [score]
        elif 'ACCURACY' in question_upper or 'ACCURATE' in question_upper:
            dimension_scores['Accuracy'] = dimension_scores.get('Accuracy', []) + [score]
        elif 'TONE APPROPRIATENESS' in question_upper or 'TONE' in question_upper:
            dimension_scores['Tone'] = dimension_scores.get('Tone', []) + [score]
        elif ('SAFETY' in question_upper and 'ETHICS' in question_upper) or 'HARMFUL' in question_upper:
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


def create_radar_chart(avg_scores: Dict[str, float], full_avg_scores: Optional[Dict[str, float]] = None) -> go.Figure:
    """Create enhanced radar chart"""
    fig = go.Figure()
    
    # Extract categories and values from the dictionary
    categories = list(avg_scores.keys())
    values = list(avg_scores.values())
    
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='Current Selection',
        line=dict(color='rgb(59, 130, 246)', width=3),
        fillcolor='rgba(59, 130, 246, 0.25)',
        marker=dict(size=8, color='rgb(59, 130, 246)')
    ))
    
    if full_avg_scores is not None:
        full_values = [full_avg_scores.get(cat, 0) for cat in categories]
        fig.add_trace(go.Scatterpolar(
            r=full_values + [full_values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name='Full System Prompt',
            line=dict(color='rgb(239, 68, 68)', width=2.5),
            fillcolor='rgba(239, 68, 68, 0.15)',
            opacity=0.85,
            marker=dict(size=6, color='rgb(239, 68, 68)')
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, 
                          tickmode='linear', tick0=0, dtick=20, gridcolor='rgba(128, 128, 128, 0.2)'),
            angularaxis=dict(visible=True, showticklabels=True, tickfont=dict(color='#d4d4d8', size=11)),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(39, 39, 42, 0.8)', 
                   bordercolor='rgba(63, 63, 70, 0.5)', borderwidth=1, font=dict(color='#d4d4d8', size=11)),
        height=400, margin=dict(l=40, r=40, t=20, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def create_bar_chart(avg_scores: Dict[str, float], full_avg_scores: Optional[Dict[str, float]] = None) -> go.Figure:
    """Create enhanced bar chart"""
    fig = go.Figure()
    
    # Extract categories and values from the dictionary
    categories = list(avg_scores.keys())
    values = list(avg_scores.values())
    
    fig.add_trace(go.Bar(
        x=categories, y=values, name='Current Selection',
        marker=dict(color='rgb(59, 130, 246)', line=dict(color='rgb(37, 99, 235)', width=1.5), cornerradius=4),
        opacity=0.9
    ))
    
    if full_avg_scores is not None:
        full_values = [full_avg_scores.get(cat, 0) for cat in categories]
        fig.add_trace(go.Bar(
            x=categories, y=full_values, name='Full System Prompt',
            marker=dict(color='rgb(239, 68, 68)', line=dict(color='rgb(220, 38, 38)', width=1.5), cornerradius=4),
            opacity=0.85
        ))
    
    fig.update_layout(
        barmode='group',
        yaxis=dict(range=[0, 100], title='Score', gridcolor='rgba(39, 39, 42, 0.5)',
                  tickfont=dict(color='#a1a1aa', size=11), titlefont=dict(color='#d4d4d8', size=12, family='Inter')),
        xaxis=dict(title='Dimensions', tickfont=dict(color='#a1a1aa', size=11),
                  titlefont=dict(color='#d4d4d8', size=12, family='Inter')),
        legend=dict(bgcolor='rgba(39, 39, 42, 0.8)', bordercolor='rgba(63, 63, 70, 0.5)',
                   borderwidth=1, font=dict(color='#d4d4d8', size=11)),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        height=300, margin=dict(l=50, r=20, t=10, b=40)
    )
    return fig

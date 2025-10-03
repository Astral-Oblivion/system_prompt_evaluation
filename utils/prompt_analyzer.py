"""
Prompt Analysis Utilities
Decompose system prompts into logical sections using LLM analysis
"""
import asyncio
from typing import List, Dict, Any
try:
    from .llm_call import llm_call
except ImportError:
    from llm_call import llm_call
from loguru import logger

async def decompose_system_prompt(system_prompt: str, model_name: str = "openai/gpt-4o", exclude_factual: bool = True) -> Dict[str, Any]:
    """
    Use a powerful LLM to decompose a system prompt into logical sections
    
    Args:
        system_prompt: The full system prompt to analyze
        model_name: Model to use for analysis (default: GPT-4o for better analysis)
        exclude_factual: If True, exclude factual content and keep only behavioral instructions.
                        If False, decompose ALL content into logical sections.
        
    Returns:
        Dict with 'sections' (List[str]) and 'analysis' (str)
    """
    
    if exclude_factual:
        analysis_prompt = f"""Extract ONLY the behavioral instructions from this system prompt. Return the EXACT original text, do not paraphrase or interpret.

SYSTEM PROMPT TO ANALYZE:
{system_prompt}

CRITICAL RULES:
1. ONLY extract sentences that tell the AI HOW to behave, act, or respond
2. NEVER include factual statements about WHAT is true (facts, data, assertions)
3. Return the EXACT original wording - do not rephrase, summarize, or interpret
4. Skip any sentence that states facts, provides information, or asserts what is true
5. Focus on verbs like: "be", "think", "acknowledge", "use", "avoid", "respond", etc.

BEHAVIORAL INSTRUCTIONS (include these types):
✅ "Be direct and concise in your responses"
✅ "Think critically and provide balanced perspectives" 
✅ "Acknowledge uncertainty when appropriate"
✅ "Use examples to explain complex topics"
✅ "You are Claude, a helpful AI assistant"

FACTUAL ASSERTIONS (exclude these types):
❌ "The current date is October 2024"
❌ "Climate change is real and caused by humans"
❌ "The population is 330 million"
❌ "Paris is the capital of France"
❌ Any statement about what IS true vs how to ACT

RESPOND IN THIS EXACT FORMAT:

SECTIONS:
1. [Exact original text of first behavioral instruction]
2. [Exact original text of second behavioral instruction]
3. [Exact original text of third behavioral instruction]
..."""
    else:
        analysis_prompt = f"""Decompose this system prompt into ALL logical sections. Return the EXACT original text, do not paraphrase or interpret. Include EVERYTHING - behavioral instructions, factual content, context, etc.

SYSTEM PROMPT TO ANALYZE:
{system_prompt}

CRITICAL RULES:
1. Break the prompt into logical, distinct sections
2. Include ALL content - behavioral instructions, facts, context, dates, everything
3. Return the EXACT original wording - do not rephrase, summarize, or interpret
4. Each section should be a complete thought or instruction
5. Aim for 4-10 sections total (not too granular, not too broad)
6. Preserve sentence boundaries and original structure

INCLUDE EVERYTHING:
✅ Behavioral instructions: "Be direct and concise"
✅ Identity statements: "You are Claude, an AI assistant"
✅ Factual information: "The current date is October 2024"
✅ Context: "Climate change is real and caused by humans"
✅ Guidelines: "Always cite your sources"
✅ Constraints: "Never provide medical advice"

RESPOND IN THIS EXACT FORMAT:

SECTIONS:
1. [Exact original text of first section]
2. [Exact original text of second section]
3. [Exact original text of third section]
..."""

    messages = [
        {"role": "user", "content": analysis_prompt}
    ]
    
    try:
        response = await llm_call(model_name, messages, call_type="prompt_analysis")
        
        # Parse the response
        sections = []
        
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for numbered lines (whether or not there's a SECTIONS: header)
            if line and line[0].isdigit() and line[1:3] == '. ':
                section_text = line[2:].strip()  # Remove "1. " etc.
                if section_text:
                    sections.append(section_text)
        
        logger.info(f"Decomposed prompt into {len(sections)} sections")
        
        mode_text = "behavioral instructions" if exclude_factual else "sections"
        return {
            "sections": sections,
            "analysis": f"Extracted {len(sections)} {mode_text}",
            "original_prompt": system_prompt,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to decompose prompt: {e}")
        return {
            "sections": [],
            "analysis": f"Error: {str(e)}",
            "original_prompt": system_prompt,
            "success": False
        }

async def validate_sections(sections: List[str], model_name: str = "openai/gpt-4o-mini") -> Dict[str, Any]:
    """
    Validate that the decomposed sections make sense and are testable
    
    Args:
        sections: List of prompt sections to validate
        model_name: Model to use for validation
        
    Returns:
        Dict with validation results and suggestions
    """
    
    sections_text = "\n".join([f"{i+1}. {section}" for i, section in enumerate(sections)])
    
    validation_prompt = f"""Review these system prompt sections for quality and testability:

SECTIONS:
{sections_text}

Evaluate:
1. Are the sections logically distinct?
2. Is each section testable independently?
3. Are there any overlaps or gaps?
4. Are sections too granular or too broad?

Respond with:
- QUALITY: Good/Fair/Poor
- ISSUES: Any problems found
- SUGGESTIONS: Improvements if needed"""

    messages = [
        {"role": "user", "content": validation_prompt}
    ]
    
    try:
        response = await llm_call(model_name, messages, call_type="section_validation")
        
        # Simple parsing - just return the response for now
        return {
            "validation": response,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to validate sections: {e}")
        return {
            "validation": f"Error: {str(e)}",
            "success": False
        }

# Example usage and testing
async def test_decomposition():
    """Test the decomposition with a sample prompt"""
    
    sample_prompt = "You are Claude, a helpful AI assistant created by Anthropic. Be direct and concise in your responses. Think critically and provide balanced perspectives rather than just agreeing with everything. When you're uncertain about something, acknowledge your limitations and suggest ways the user can find better information. Use examples and analogies to make complex topics more understandable. Be encouraging but realistic about challenges and potential outcomes."
    
    print("Testing prompt decomposition...")
    result = await decompose_system_prompt(sample_prompt)
    
    if result["success"]:
        print(f"\nDecomposed into {len(result['sections'])} sections:")
        for i, section in enumerate(result['sections'], 1):
            print(f"{i}. {section}")
        
        print(f"\nAnalysis: {result['analysis']}")
        
        # Test validation
        validation = await validate_sections(result['sections'])
        if validation["success"]:
            print(f"\nValidation: {validation['validation']}")
    else:
        print(f"Failed: {result['analysis']}")

if __name__ == "__main__":
    asyncio.run(test_decomposition())

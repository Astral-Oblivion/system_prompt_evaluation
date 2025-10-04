"""
Batch Evaluation Logic for Prompt Testing

This module handles the systematic evaluation of prompt combinations
to understand which sections drive specific AI behaviors.
"""
import asyncio
from typing import List, Dict, Any, Tuple
from itertools import combinations
import pandas as pd
from loguru import logger
from utils.llm_call import llm_call
import textstat

# Configure logging for evaluation runs
logger.add("logs/evaluation.log", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


def calculate_response_metrics(response: str) -> Dict[str, Any]:
    """
    Calculate objective metrics for a response
    
    Args:
        response: The AI response text to analyze
        
    Returns:
        Dictionary with calculated metrics
    """
    if not response or response.strip() == "":
        return {
            "word_count": 0,
            "char_count": 0,
            "sentence_count": 0,
            "readability_score": 0,
            "grade_level": 0
        }
    
    # Basic counts
    words = response.split()
    word_count = len(words)
    char_count = len(response)
    sentence_count = len([s for s in response.split('.') if s.strip()])
    
    # Readability metrics using textstat
    try:
        readability_score = textstat.flesch_reading_ease(response)
        grade_level = textstat.flesch_kincaid_grade(response)
    except:
        # Fallback if textstat fails
        readability_score = 50.0
        grade_level = 8.0
    
    return {
        "word_count": word_count,
        "char_count": char_count,
        "sentence_count": sentence_count,
        "readability_score": round(readability_score, 1),
        "grade_level": round(grade_level, 1)
    }


class PromptEvaluator:
    """
    Handles batch evaluation of prompt combinations
    
    Core workflow:
    1. Take a system prompt as List[str] (each string is a section)
    2. Generate all relevant combinations of sections
    3. Test each combination against a set of test queries
    4. Evaluate responses using Y/N questions to LLMs
    5. Cache results for instant UI access
    """
    
    def __init__(self, model_name: str = "anthropic/claude-3-haiku"):
        self.model_name = model_name
        self.results_cache = {}
    
    def generate_prompt_combinations(self, prompt_sections: List[str]) -> List[Tuple[int, ...]]:
        """
        Generate all relevant combinations of prompt sections
        
        Args:
            prompt_sections: List of prompt section strings
            
        Returns:
            List of tuples, where each tuple contains indices of sections to include
            
        TODO: Implement smart combination generation
        - Full factorial might be too many combinations
        - Consider progressive ablation (remove one section at a time)
        - Or additive approach (add one section at a time)
        - Or random sampling of combinations
        """
        n_sections = len(prompt_sections)
        combinations_to_test = []
        
        # Generate all possible combinations
        # TODO: Implement smarter selection strategy
        for r in range(1, n_sections + 1):
            for combo in combinations(range(n_sections), r):
                combinations_to_test.append(combo)
        
        logger.info(f"Generated {len(combinations_to_test)} combinations from {n_sections} sections")
        return combinations_to_test
    
    def combine_sections(self, prompt_sections: List[str], section_indices: Tuple[int, ...]) -> str:
        """
        Combine selected prompt sections into a single system prompt
        
        Args:
            prompt_sections: List of all available sections
            section_indices: Tuple of indices to include
            
        Returns:
            Combined system prompt string
        """
        selected_sections = [prompt_sections[i] for i in section_indices]
        return "\n\n".join(selected_sections)
    
    async def evaluate_single_combination(
        self, 
        system_prompt: str, 
        test_query: str, 
        evaluation_question: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Evaluate a single prompt combination against a test query
        
        Args:
            system_prompt: The combined system prompt to test
            test_query: User query to test the prompt with
            evaluation_question: Y/N question to evaluate the response
            
        Returns:
            Dictionary with evaluation results
            
        TODO: Implement the actual evaluation logic
        - Make the API call with system_prompt + test_query
        - Ask evaluation_question about the response (Y/N)
        - Return structured results
        """
        # Generate unique evaluation ID for tracking
        import uuid
        eval_id = str(uuid.uuid4())[:8]
        logger.info(f"=== EVALUATION START | ID: {eval_id} ===")
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": test_query}
            ]
            
            response = await llm_call(self.model_name, messages, call_type="main_response")
            
            if "Answer only Y or N" in evaluation_question:
                eval_prompt = f"Response to evaluate: {response}\n\nEvaluation question: {evaluation_question}"
            else:
                eval_prompt = f"Response to evaluate: {response}\n\nEvaluation question: {evaluation_question}\n\nRespond with ONLY a number between 0-100. No explanation, just the score."
            
            eval_messages = [
                {"role": "user", "content": eval_prompt}
            ]
            
            evaluation_result = await llm_call(self.model_name, eval_messages, call_type="evaluation")
            
            evaluation_result_clean = evaluation_result.strip().upper()
            
            # Check if this is a Y/N question
            if "Answer only Y or N" in evaluation_question:
                if evaluation_result_clean in ['Y', 'YES']:
                    evaluation_score = 100
                elif evaluation_result_clean in ['N', 'NO']:
                    evaluation_score = 0
                else:
                    if 'Y' in evaluation_result_clean and 'N' not in evaluation_result_clean:
                        evaluation_score = 100
                    elif 'N' in evaluation_result_clean and 'Y' not in evaluation_result_clean:
                        evaluation_score = 0
                    else:
                        evaluation_score = 50
            else:
                try:
                    evaluation_score = int(evaluation_result_clean)
                    evaluation_score = max(0, min(100, evaluation_score))
                except ValueError:
                    import re
                    numbers = re.findall(r'\b(\d{1,3})\b', evaluation_result)
                    if numbers:
                        evaluation_score = max(0, min(100, int(numbers[0])))
                    else:
                        evaluation_score = 50
            
            # Calculate response metrics
            metrics = calculate_response_metrics(response)
            
            result = {
                "system_prompt": system_prompt,
                "test_query": test_query,
                "response": response,
                "evaluation_question": evaluation_question,
                "evaluation_result": evaluation_result,
                "evaluation_score": evaluation_score,
                "word_count": metrics["word_count"],
                "char_count": metrics["char_count"],
                "sentence_count": metrics["sentence_count"],
                "readability_score": metrics["readability_score"],
                "grade_level": metrics["grade_level"],
                "success": True
            }
            
            logger.info(f"EVALUATION_SCORE: {evaluation_score}")
            logger.info(f"=== EVALUATION END | ID: {eval_id} | Score: {evaluation_score} ===")
            return result
            
        except Exception as e:
            logger.error(f"EVALUATION_ERROR | ID: {eval_id} | Error: {e}")
            logger.info(f"=== EVALUATION END | ID: {eval_id} | Status: FAILED ===")
            return {
                "system_prompt": system_prompt,
                "test_query": test_query,
                "response": "ERROR: Failed to get response",
                "evaluation_question": evaluation_question,
                "evaluation_result": f"ERROR: {str(e)}",
                "evaluation_score": None,
                "word_count": 0,
                "char_count": 0,
                "sentence_count": 0,
                "readability_score": 0,
                "grade_level": 0,
                "error": str(e),
                "success": False
            }
    
    async def run_batch_evaluation(
        self,
        prompt_sections: List[str],
        test_queries: List[str],
        evaluation_questions: List[str]
    ) -> pd.DataFrame:
        """
        Run complete batch evaluation of all combinations
        
        Args:
            prompt_sections: List of prompt section strings
            test_queries: List of test queries to evaluate
            evaluation_questions: List of Y/N evaluation questions
            
        Returns:
            DataFrame with all evaluation results
            
        TODO: Implement full batch evaluation
        - Generate all prompt combinations
        - Run each combination against all test queries
        - Evaluate using all evaluation questions
        - Use asyncio.gather for parallel execution
        - Save results to cache files
        """
        logger.info("Starting batch evaluation...")
        
        # Generate combinations
        combinations = self.generate_prompt_combinations(prompt_sections)
        
        # Prepare all evaluation tasks
        tasks = []
        for combo_indices in combinations:
            system_prompt = self.combine_sections(prompt_sections, combo_indices)
            for test_query in test_queries:
                for eval_question in evaluation_questions:
                    task = self.evaluate_single_combination(
                        system_prompt, test_query, eval_question
                    )
                    tasks.append(task)
        
        logger.info(f"Running {len(tasks)} evaluation tasks...")
        
        # Execute all tasks in parallel with batching for high throughput
        logger.info(f"Executing {len(tasks)} evaluation tasks...")
        
        # For very large numbers of tasks, process in batches to avoid overwhelming the system
        batch_size = 500  # Maximum concurrent tasks
        results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size} ({len(batch)} tasks)")
            
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)
        
        # Convert to DataFrame
        df = pd.DataFrame([r for r in results if isinstance(r, dict)])
        
        # Save to cache
        cache_file = "cached_results/batch_evaluation.csv"
        df.to_csv(cache_file, index=False)
        logger.info(f"Saved {len(df)} results to {cache_file}")
        
        return df
    
    def load_cached_results(self, cache_file: str = "cached_results/batch_evaluation.csv") -> pd.DataFrame:
        """
        Load previously computed evaluation results
        
        TODO: Implement caching system
        - Load from CSV/parquet files
        - Handle missing files gracefully
        - Merge with new results if needed
        """
        try:
            return pd.read_csv(cache_file)
        except FileNotFoundError:
            logger.warning(f"Cache file {cache_file} not found, returning empty DataFrame")
            return pd.DataFrame()


# Example usage and testing
async def example_evaluation():
    """Example of how to use the PromptEvaluator"""
    
    # Example prompt sections
    prompt_sections = [
        "You are a helpful AI assistant.",
        "Always be polite and respectful.",
        "Provide detailed explanations when possible.",
        "If you're unsure, say so clearly."
    ]
    
    # Example test queries
    test_queries = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms."
    ]
    
    # Example evaluation questions
    evaluation_questions = [
        "Does the response show politeness?",
        "Does the response provide detailed explanations?"
    ]
    
    evaluator = PromptEvaluator()
    results = await evaluator.run_batch_evaluation(
        prompt_sections, test_queries, evaluation_questions
    )
    
    print(f"Completed evaluation with {len(results)} results")
    return results


if __name__ == "__main__":
    # Run example evaluation
    asyncio.run(example_evaluation())

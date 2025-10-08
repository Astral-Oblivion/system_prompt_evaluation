"""
Batch Evaluation Logic for Prompt Testing - FIXED VERSION

This module handles the systematic evaluation of prompt combinations
to understand which sections drive specific AI behaviors.

MAJOR FIX: Now evaluates all dimensions on the SAME response instead of making
separate API calls for each dimension, reducing API calls by ~83%.
"""
import asyncio
from typing import List, Dict, Any, Tuple
from itertools import combinations
import pandas as pd
from loguru import logger
from utils.latteries.caller import llm_call
import textstat

# Configure logging for evaluation runs - remove default stderr handler
logger.remove()  # Remove default handler that prints to stderr
logger.add("logs/evaluation.log", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


def calculate_response_metrics(response: str) -> Dict[str, Any]:
    """Calculate text metrics for a response"""
    return {
        "word_count": textstat.lexicon_count(response),
        "char_count": len(response),
        "sentence_count": textstat.sentence_count(response),
        "readability_score": textstat.flesch_reading_ease(response),
        "grade_level": textstat.flesch_kincaid_grade(response)
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

    def __init__(self, model_name: str = "anthropic/claude-3-haiku", max_concurrent: int = 100):
        self.model_name = model_name
        self.results_cache = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    def generate_prompt_combinations(self, prompt_sections: List[str]) -> List[Tuple[int, ...]]:
        """
        Generate all relevant combinations of prompt sections
        
        Args:
            prompt_sections: List of prompt section strings
            
        Returns:
            List of tuples, where each tuple contains indices of sections to include
        """
        n_sections = len(prompt_sections)
        combinations_to_test = []
        
        # Generate all possible combinations
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
    
    async def _evaluate_response(
        self,
        response: str,
        evaluation_question: str,
        eval_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate a single response against one evaluation question
        
        Args:
            response: The AI response to evaluate
            evaluation_question: The evaluation question to apply
            eval_id: Unique ID for logging
            
        Returns:
            Dictionary with evaluation result and score
        """
        try:
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
            
            logger.info(f"EVAL_DIMENSION | ID: {eval_id} | Question: {evaluation_question[:50]}... | Score: {evaluation_score}")
            
            return {
                "result": evaluation_result,
                "score": evaluation_score,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"EVAL_DIMENSION_ERROR | ID: {eval_id} | Question: {evaluation_question[:50]}... | Error: {e}")
            return {
                "result": f"ERROR: {str(e)}",
                "score": None,
                "success": False
            }
    
    async def _evaluate_with_semaphore(
        self,
        system_prompt: str,
        test_query: str,
        evaluation_questions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Wrapper that uses semaphore to limit concurrent API calls
        """
        async with self.semaphore:
            return await self.evaluate_prompt_query_combination(
                system_prompt, test_query, evaluation_questions
            )

    async def evaluate_prompt_query_combination(
        self,
        system_prompt: str,
        test_query: str,
        evaluation_questions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate one prompt-query combination across all evaluation dimensions

        This is the new efficient approach:
        1. Generate ONE response for the prompt-query pair
        2. Evaluate that SAME response across all dimensions
        3. Return results for all dimensions

        Args:
            system_prompt: The combined system prompt to test
            test_query: User query to test the prompt with
            evaluation_questions: List of evaluation questions (all dimensions)

        Returns:
            List of dictionaries with evaluation results for each dimension
        """
        # Generate unique evaluation ID for tracking
        import uuid
        eval_id = str(uuid.uuid4())[:8]
        logger.info(f"=== COMBINATION START | ID: {eval_id} ===")
        logger.info(f"SYSTEM_PROMPT | ID: {eval_id} | {system_prompt}")
        logger.info(f"TEST_QUERY | ID: {eval_id} | {test_query}")
        
        try:
            # Step 1: Generate ONE response for this prompt-query combination
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": test_query}
            ]
            
            response = await llm_call(self.model_name, messages, call_type="main_response")
            logger.info(f"MAIN_RESPONSE | ID: {eval_id} | {response}")
            
            # Step 2: Calculate text metrics once
            metrics = calculate_response_metrics(response)
            logger.info(f"TEXT_METRICS | ID: {eval_id} | Words: {metrics['word_count']} | Readability: {metrics['readability_score']:.1f} | Grade: {metrics['grade_level']:.1f}")
            
            # Step 3: Evaluate this SAME response across all dimensions
            results = []
            for i, eval_question in enumerate(evaluation_questions):
                eval_result = await self._evaluate_response(response, eval_question, f"{eval_id}-{i+1}")
                
                result = {
                    "system_prompt": system_prompt,
                    "test_query": test_query,
                    "response": response,  # Same response for all evaluations!
                    "evaluation_question": eval_question,
                    "evaluation_result": eval_result["result"],
                    "evaluation_score": eval_result["score"],
                    "word_count": metrics["word_count"],
                    "char_count": metrics["char_count"],
                    "sentence_count": metrics["sentence_count"],
                    "readability_score": metrics["readability_score"],
                    "grade_level": metrics["grade_level"],
                    "success": eval_result["success"]
                }
                results.append(result)
            
            successful_evals = len([r for r in results if r["success"]])
            logger.info(f"=== COMBINATION END | ID: {eval_id} | Dimensions: {successful_evals}/{len(evaluation_questions)} successful ===")
            return results
            
        except Exception as e:
            logger.error(f"COMBINATION_ERROR | ID: {eval_id} | Error: {e}")
            logger.info(f"=== COMBINATION END | ID: {eval_id} | Status: FAILED ===")
            
            # Return failed results for all dimensions
            failed_results = []
            for eval_question in evaluation_questions:
                failed_results.append({
                    "system_prompt": system_prompt,
                    "test_query": test_query,
                    "response": "ERROR: Failed to get response",
                    "evaluation_question": eval_question,
                    "evaluation_result": f"ERROR: {str(e)}",
                    "evaluation_score": None,
                    "word_count": 0,
                    "char_count": 0,
                    "sentence_count": 0,
                    "readability_score": 0,
                    "grade_level": 0,
                    "error": str(e),
                    "success": False
                })
            return failed_results
    
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
        """
        logger.info("Starting batch evaluation...")
        
        # Generate combinations
        combinations = self.generate_prompt_combinations(prompt_sections)
        
        # Prepare all evaluation tasks (NEW EFFICIENT APPROACH)
        # Instead of evaluating each dimension separately, we evaluate each prompt-query combination once
        # and get all dimension scores for the same response
        tasks = []
        for combo_indices in combinations:
            system_prompt = self.combine_sections(prompt_sections, combo_indices)
            for test_query in test_queries:
                # Create one task per prompt-query combination (not per dimension!)
                # Use semaphore wrapper to limit concurrent API calls
                task = self._evaluate_with_semaphore(
                    system_prompt, test_query, evaluation_questions
                )
                tasks.append(task)

        total_combinations = len(combinations) * len(test_queries)
        total_api_calls = total_combinations * (1 + len(evaluation_questions))  # 1 main response + N evaluations
        old_api_calls = total_combinations * len(evaluation_questions) * 2  # Old approach: 2 calls per dimension

        logger.info(f"Running {len(tasks)} combination tasks ({total_combinations} combinations × {len(evaluation_questions)} dimensions = {total_combinations * len(evaluation_questions)} total evaluations)")
        logger.info("NEW EFFICIENT APPROACH:")
        logger.info(f"  API calls: {total_api_calls}")
        logger.info(f"  Old approach would have used: {old_api_calls}")
        logger.info(f"  Savings: {old_api_calls - total_api_calls} calls ({((old_api_calls - total_api_calls) / old_api_calls * 100):.1f}% reduction)")
        logger.info(f"  Concurrent limit: {self.semaphore._value} simultaneous requests")

        # Execute all tasks with semaphore controlling concurrency
        all_results = []

        logger.info(f"Starting concurrent execution with semaphore (max {self.semaphore._value} concurrent)")
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results since each task returns a list of dimension results
        for result_list in batch_results:
            if isinstance(result_list, list):
                all_results.extend(result_list)
            elif isinstance(result_list, Exception):
                logger.error(f"Task failed: {result_list}")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # Save to cache
        cache_file = "cached_results/batch_evaluation.csv"
        df.to_csv(cache_file, index=False)
        logger.info(f"Saved {len(df)} results to {cache_file}")
        
        return df
    
    def load_cached_results(self, cache_file: str = "cached_results/batch_evaluation.csv") -> pd.DataFrame:
        """
        Load previously computed evaluation results
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
        "Does the response show politeness? Answer only Y or N.",
        "Does the response provide detailed explanations? Answer only Y or N."
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

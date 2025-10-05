#!/usr/bin/env python3
"""
Retry failed evaluations in small batches to avoid rate limits
"""
import asyncio
import pandas as pd
import time
from evaluation import PromptEvaluator
from loguru import logger

# Configure logging
logger.add("logs/retry_evaluations.log", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

async def retry_failed_evaluations(batch_size: int = 50, delay_between_batches: float = 1.0):
    """
    Retry failed evaluations in small batches
    
    Args:
        batch_size: Number of evaluations per batch
        delay_between_batches: Seconds to wait between batches
    """
    # Load existing results
    try:
        df = pd.read_csv("cached_results/batch_evaluation.csv")
        logger.info(f"Loaded {len(df)} existing results")
    except FileNotFoundError:
        logger.error("No cached results found!")
        return
    
    # Find failed evaluations
    failed_df = df[df['success'] == False].copy()
    logger.info(f"Found {len(failed_df)} failed evaluations to retry")
    
    if len(failed_df) == 0:
        logger.info("No failed evaluations to retry!")
        return
    
    # Initialize evaluator
    evaluator = PromptEvaluator(model_name="openai/gpt-4o-mini")
    
    # Process in batches
    successful_retries = []
    total_batches = (len(failed_df) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(failed_df))
        batch_df = failed_df.iloc[start_idx:end_idx]
        
        logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_df)} evaluations)")
        
        # Group failed evaluations by (system_prompt, test_query) to use new efficient method
        # Since we now evaluate all dimensions together, we need to group by prompt-query pairs
        grouped_failures = {}
        for _, row in batch_df.iterrows():
            key = (row['system_prompt'], row['test_query'])
            if key not in grouped_failures:
                grouped_failures[key] = []
            grouped_failures[key].append(row['evaluation_question'])
        
        # Create tasks for unique prompt-query combinations
        tasks = []
        for (system_prompt, test_query), eval_questions in grouped_failures.items():
            task = evaluator.evaluate_prompt_query_combination(
                system_prompt=system_prompt,
                test_query=test_query,
                evaluation_questions=eval_questions
            )
            tasks.append(task)
        
        # Run batch with some delay between calls
        batch_results = []
        for i, task in enumerate(tasks):
            try:
                result_list = await task  # This now returns a list of results for all dimensions
                batch_results.extend(result_list)  # Flatten the results
                
                # Small delay between individual calls within batch
                if i < len(tasks) - 1:  # Don't delay after last item
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Create failed results for all dimensions in this task
                task_key = list(grouped_failures.keys())[i]
                system_prompt, test_query = task_key
                eval_questions = grouped_failures[task_key]
                
                for eval_question in eval_questions:
                    batch_results.append({
                        "system_prompt": system_prompt,
                        "test_query": test_query,
                        "evaluation_question": eval_question,
                        "error": str(e),
                        "success": False
                    })
        
        # Collect successful results
        successful_results = [r for r in batch_results if r.get('success', False)]
        successful_retries.extend(successful_results)
        
        logger.info(f"Batch {batch_num + 1} completed: {len(successful_results)}/{len(batch_results)} successful")
        
        # Wait between batches (except for last batch)
        if batch_num < total_batches - 1:
            logger.info(f"Waiting {delay_between_batches}s before next batch...")
            await asyncio.sleep(delay_between_batches)
    
    logger.info(f"Retry completed: {len(successful_retries)} successful out of {len(failed_df)} attempts")
    
    if successful_retries:
        # Remove old failed entries and add successful retries
        success_df = df[df['success'] == True].copy()
        retry_df = pd.DataFrame(successful_retries)
        
        # Combine successful original + successful retries
        combined_df = pd.concat([success_df, retry_df], ignore_index=True)
        
        # Save updated results
        combined_df.to_csv("cached_results/batch_evaluation.csv", index=False)
        logger.info(f"Updated cache with {len(combined_df)} total results ({len(retry_df)} newly successful)")
        
        # Show summary
        remaining_failed = len(failed_df) - len(successful_retries)
        print(f"\n✅ Retry Summary:")
        print(f"   • Original failed: {len(failed_df)}")
        print(f"   • Successfully retried: {len(successful_retries)}")
        print(f"   • Still failed: {remaining_failed}")
        print(f"   • Total successful results: {len(combined_df)}")
        
        if remaining_failed > 0:
            print(f"\n⚠️  {remaining_failed} evaluations still failed. You may want to:")
            print(f"   • Run this script again")
            print(f"   • Check your API key and network connection")
            print(f"   • Try a different model")

if __name__ == "__main__":
    import sys
    
    # Allow batch size to be specified as command line argument
    batch_size = 50  # Default increased
    delay = 1.0  # Default decreased for higher throughput
    
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
            batch_size = max(1, min(batch_size, 200))  # Clamp between 1-200
        except ValueError:
            print("Invalid batch size, using default of 50")
    
    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
            delay = max(0.1, min(delay, 10.0))  # Clamp between 0.1-10 seconds
        except ValueError:
            print("Invalid delay, using default of 1.0 seconds")
    
    print(f"🔄 Retrying failed evaluations in batches of {batch_size}...")
    print(f"   Delay between batches: {delay}s")
    print("   Use: python retry_failed_evaluations.py [batch_size] [delay]")
    
    asyncio.run(retry_failed_evaluations(
        batch_size=batch_size,
        delay_between_batches=delay
    ))

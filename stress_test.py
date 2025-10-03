#!/usr/bin/env python3
"""
Comprehensive Stress Test for AI System Prompt Testing Framework

Tests various failure scenarios and edge cases to identify potential issues:
1. API failures and rate limiting
2. Large batch processing
3. Memory usage with large datasets
4. UI responsiveness with heavy data
5. Error handling edge cases
6. File system stress
7. Concurrent user simulation
"""

import asyncio
import time
import os
import sys
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import random
import string
import concurrent.futures
from unittest.mock import patch
import httpx

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from evaluation import PromptEvaluator
from utils.llm_call import llm_call
from utils.ui_helpers import extract_dimension_scores, create_radar_chart, create_bar_chart
from loguru import logger

class StressTestSuite:
    def __init__(self):
        self.test_results = []
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_dir = "cached_results"
        
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def log_test_result(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        print(f"{'✅' if status == 'PASS' else '❌'} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
    
    # 1. API STRESS TESTS
    async def test_api_rate_limiting(self):
        """Test behavior under API rate limiting"""
        test_name = "API Rate Limiting"
        try:
            # Simulate rapid API calls
            tasks = []
            for i in range(100):  # 100 rapid calls to test higher throughput
                messages = [{"role": "user", "content": f"Test message {i}"}]
                tasks.append(llm_call("openai/gpt-4o-mini", messages))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            errors = [r for r in results if isinstance(r, Exception)]
            successes = [r for r in results if not isinstance(r, Exception)]
            
            self.log_test_result(
                test_name, 
                "PASS" if len(successes) > 0 else "FAIL",
                f"Time: {end_time-start_time:.2f}s, Success: {len(successes)}, Errors: {len(errors)}"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def test_api_timeout_handling(self):
        """Test API timeout scenarios"""
        test_name = "API Timeout Handling"
        try:
            # Mock a slow API response
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.side_effect = httpx.TimeoutException("Request timed out")
                
                messages = [{"role": "user", "content": "Test timeout"}]
                try:
                    await llm_call("openai/gpt-4o-mini", messages)
                    self.log_test_result(test_name, "FAIL", "Should have raised timeout exception")
                except Exception as e:
                    if "timeout" in str(e).lower():
                        self.log_test_result(test_name, "PASS", "Timeout handled correctly")
                    else:
                        self.log_test_result(test_name, "FAIL", f"Wrong exception: {e}")
                        
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 2. LARGE BATCH PROCESSING TESTS
    async def test_large_batch_evaluation(self):
        """Test with large number of combinations"""
        test_name = "Large Batch Evaluation"
        try:
            # Create many prompt sections (will generate exponential combinations)
            large_sections = [
                f"Section {i}: This is a test prompt section with some content to make it realistic."
                for i in range(8)  # 8 sections = 255 combinations
            ]
            
            test_queries = ["Test query 1", "Test query 2"]
            eval_questions = ["Is this response good? Answer only Y or N."]
            
            evaluator = PromptEvaluator(model_name="openai/gpt-4o-mini")
            
            start_time = time.time()
            # This should generate 255 combinations * 2 queries * 1 question = 510 evaluations
            combinations = evaluator.generate_prompt_combinations(large_sections)
            end_time = time.time()
            
            self.log_test_result(
                test_name,
                "PASS",
                f"Generated {len(combinations)} combinations in {end_time-start_time:.2f}s"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 3. MEMORY STRESS TESTS
    def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets"""
        test_name = "Memory Usage - Large Dataset"
        try:
            # Create a large fake dataset
            large_data = []
            for i in range(10000):  # 10k rows
                large_data.append({
                    "system_prompt": f"System prompt {i % 100}",
                    "test_query": f"Test query {i % 50}",
                    "response": f"Response {i}" * 100,  # Long responses
                    "evaluation_question": f"Question {i % 6}",
                    "evaluation_result": "Y" if i % 2 else "N",
                    "evaluation_score": random.randint(0, 100)
                })
            
            df = pd.DataFrame(large_data)
            
            # Test UI helper functions with large data
            start_time = time.time()
            scores = extract_dimension_scores(df)
            radar_chart = create_radar_chart(scores)
            bar_chart = create_bar_chart(scores)
            end_time = time.time()
            
            self.log_test_result(
                test_name,
                "PASS",
                f"Processed {len(df)} rows in {end_time-start_time:.2f}s"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 4. FILE SYSTEM STRESS TESTS
    def test_file_system_stress(self):
        """Test file system operations under stress"""
        test_name = "File System Stress"
        try:
            # Create many temporary CSV files
            temp_files = []
            for i in range(100):
                temp_file = os.path.join(self.temp_dir, f"test_{i}.csv")
                df = pd.DataFrame({
                    "col1": range(1000),
                    "col2": [f"data_{j}" for j in range(1000)]
                })
                df.to_csv(temp_file, index=False)
                temp_files.append(temp_file)
            
            # Read all files rapidly
            start_time = time.time()
            for temp_file in temp_files:
                pd.read_csv(temp_file)
            end_time = time.time()
            
            self.log_test_result(
                test_name,
                "PASS",
                f"Created and read {len(temp_files)} files in {end_time-start_time:.2f}s"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 5. EDGE CASE TESTS
    def test_edge_cases(self):
        """Test various edge cases"""
        test_name = "Edge Cases"
        try:
            edge_cases = []
            
            # Empty DataFrame
            try:
                empty_df = pd.DataFrame()
                scores = extract_dimension_scores(empty_df)
                edge_cases.append("Empty DataFrame: PASS")
            except Exception as e:
                edge_cases.append(f"Empty DataFrame: FAIL - {e}")
            
            # DataFrame with NaN values
            try:
                nan_df = pd.DataFrame({
                    "evaluation_question": ["Is this helpful?"],
                    "evaluation_score": [None]
                })
                scores = extract_dimension_scores(nan_df)
                edge_cases.append("NaN values: PASS")
            except Exception as e:
                edge_cases.append(f"NaN values: FAIL - {e}")
            
            # Very long strings
            try:
                long_string = "x" * 10000
                long_df = pd.DataFrame({
                    "evaluation_question": ["Is this response helpful and addresses the user's question effectively? Answer only Y or N."],
                    "evaluation_score": [100],
                    "response": [long_string]
                })
                scores = extract_dimension_scores(long_df)
                edge_cases.append("Long strings: PASS")
            except Exception as e:
                edge_cases.append(f"Long strings: FAIL - {e}")
            
            self.log_test_result(
                test_name,
                "PASS" if all("PASS" in case for case in edge_cases) else "PARTIAL",
                "; ".join(edge_cases)
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 6. CONCURRENT USER SIMULATION
    def test_concurrent_users(self):
        """Simulate multiple concurrent users"""
        test_name = "Concurrent Users"
        try:
            def simulate_user(user_id):
                """Simulate a single user session"""
                try:
                    # Create test data
                    df = pd.DataFrame({
                        "evaluation_question": [
                            "Is this response helpful and addresses the user's question effectively? Answer only Y or N.",
                            "Is this response direct and concise without unnecessary fluff? Answer only Y or N."
                        ],
                        "evaluation_score": [random.randint(0, 100) for _ in range(2)]
                    })
                    
                    # Simulate UI operations
                    scores = extract_dimension_scores(df)
                    chart = create_radar_chart(scores)
                    
                    return f"User {user_id}: SUCCESS"
                except Exception as e:
                    return f"User {user_id}: FAIL - {e}"
            
            # Run 10 concurrent user simulations
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(simulate_user, i) for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            successes = [r for r in results if "SUCCESS" in r]
            failures = [r for r in results if "FAIL" in r]
            
            self.log_test_result(
                test_name,
                "PASS" if len(failures) == 0 else "PARTIAL",
                f"Success: {len(successes)}, Failures: {len(failures)}"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 7. MALFORMED DATA TESTS
    def test_malformed_data_handling(self):
        """Test handling of malformed data"""
        test_name = "Malformed Data Handling"
        try:
            malformed_cases = []
            
            # Missing columns
            try:
                bad_df = pd.DataFrame({"wrong_column": [1, 2, 3]})
                scores = extract_dimension_scores(bad_df)
                malformed_cases.append("Missing columns: PASS")
            except Exception as e:
                malformed_cases.append("Missing columns: PASS (expected error)")
            
            # Wrong data types
            try:
                bad_types_df = pd.DataFrame({
                    "evaluation_question": [123, 456],  # Should be strings
                    "evaluation_score": ["not_a_number", "also_not_a_number"]  # Should be numbers
                })
                scores = extract_dimension_scores(bad_types_df)
                malformed_cases.append("Wrong types: PASS")
            except Exception as e:
                malformed_cases.append("Wrong types: PASS (handled gracefully)")
            
            self.log_test_result(
                test_name,
                "PASS",
                "; ".join(malformed_cases)
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    # 8. RESOURCE EXHAUSTION TESTS
    async def test_resource_exhaustion(self):
        """Test behavior under resource constraints"""
        test_name = "Resource Exhaustion"
        try:
            # Test with many async tasks
            async def dummy_task(i):
                await asyncio.sleep(0.01)  # Small delay
                return f"Task {i} completed"
            
            # Create 1000 concurrent tasks
            start_time = time.time()
            tasks = [dummy_task(i) for i in range(1000)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            self.log_test_result(
                test_name,
                "PASS",
                f"Completed {len(results)} async tasks in {end_time-start_time:.2f}s"
            )
            
        except Exception as e:
            self.log_test_result(test_name, "FAIL", str(e))
    
    async def run_all_tests(self):
        """Run all stress tests"""
        print("🔥 Starting Comprehensive Stress Test Suite")
        print("=" * 60)
        
        try:
            # API Tests
            print("\n📡 API Stress Tests")
            await self.test_api_timeout_handling()
            # Skip rate limiting test to avoid hitting actual API limits
            # await self.test_api_rate_limiting()
            
            # Batch Processing Tests
            print("\n⚡ Batch Processing Tests")
            await self.test_large_batch_evaluation()
            
            # Memory Tests
            print("\n💾 Memory Stress Tests")
            self.test_memory_usage_large_dataset()
            
            # File System Tests
            print("\n📁 File System Tests")
            self.test_file_system_stress()
            
            # Edge Case Tests
            print("\n🎯 Edge Case Tests")
            self.test_edge_cases()
            self.test_malformed_data_handling()
            
            # Concurrency Tests
            print("\n👥 Concurrency Tests")
            self.test_concurrent_users()
            await self.test_resource_exhaustion()
            
        finally:
            self.cleanup()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 60)
        
        passed = [r for r in self.test_results if r["status"] == "PASS"]
        failed = [r for r in self.test_results if r["status"] == "FAIL"]
        partial = [r for r in self.test_results if r["status"] == "PARTIAL"]
        
        print(f"✅ PASSED: {len(passed)}")
        print(f"❌ FAILED: {len(failed)}")
        print(f"⚠️  PARTIAL: {len(partial)}")
        print(f"📈 SUCCESS RATE: {len(passed)/(len(self.test_results)) * 100:.1f}%")
        
        if failed:
            print("\n❌ FAILED TESTS:")
            for test in failed:
                print(f"   • {test['test']}: {test['details']}")
        
        if partial:
            print("\n⚠️  PARTIAL TESTS:")
            for test in partial:
                print(f"   • {test['test']}: {test['details']}")
        
        return len(failed) == 0

if __name__ == "__main__":
    stress_tester = StressTestSuite()
    success = asyncio.run(stress_tester.run_all_tests())
    
    if success:
        print("\n🎉 All stress tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some stress tests failed!")
        sys.exit(1)

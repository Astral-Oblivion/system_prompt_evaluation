#!/usr/bin/env python3
"""
Performance Monitoring and Profiling Tool

Monitors system performance during evaluation runs to identify bottlenecks:
1. Memory usage tracking
2. CPU utilization
3. API call latency
4. File I/O performance
5. Database operations timing
6. UI responsiveness metrics
"""

import asyncio
import time
import psutil
import os
import sys
import pandas as pd
import threading
from typing import Dict, List, Any
import json
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from evaluation import PromptEvaluator
from utils.llm_call import llm_call

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "cpu_usage": [],
            "memory_usage": [],
            "api_latencies": [],
            "file_operations": [],
            "timestamps": []
        }
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring in background thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,), 
            daemon=True
        )
        self.monitor_thread.start()
        print(f"📊 Performance monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("📊 Performance monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Background monitoring loop"""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # CPU and Memory
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # System-wide metrics
                system_cpu = psutil.cpu_percent()
                system_memory = psutil.virtual_memory().percent
                
                timestamp = time.time()
                
                self.metrics["cpu_usage"].append({
                    "process_cpu": cpu_percent,
                    "system_cpu": system_cpu,
                    "timestamp": timestamp
                })
                
                self.metrics["memory_usage"].append({
                    "process_memory_mb": memory_mb,
                    "system_memory_percent": system_memory,
                    "timestamp": timestamp
                })
                
                self.metrics["timestamps"].append(timestamp)
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    async def measure_api_latency(self, model_name: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Measure API call latency"""
        start_time = time.time()
        
        try:
            response = await llm_call(model_name, messages)
            end_time = time.time()
            latency = end_time - start_time
            
            result = {
                "latency_seconds": latency,
                "success": True,
                "timestamp": start_time,
                "model": model_name,
                "response_length": len(response) if response else 0
            }
            
        except Exception as e:
            end_time = time.time()
            latency = end_time - start_time
            
            result = {
                "latency_seconds": latency,
                "success": False,
                "timestamp": start_time,
                "model": model_name,
                "error": str(e)
            }
        
        self.metrics["api_latencies"].append(result)
        return result
    
    def measure_file_operation(self, operation_name: str, func, *args, **kwargs):
        """Measure file operation performance"""
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            self.metrics["file_operations"].append({
                "operation": operation_name,
                "duration_seconds": duration,
                "success": True,
                "timestamp": start_time
            })
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            self.metrics["file_operations"].append({
                "operation": operation_name,
                "duration_seconds": duration,
                "success": False,
                "timestamp": start_time,
                "error": str(e)
            })
            
            raise e
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        report = {
            "summary": {},
            "detailed_metrics": self.metrics,
            "generated_at": datetime.now().isoformat()
        }
        
        # API Latency Summary
        if self.metrics["api_latencies"]:
            latencies = [m["latency_seconds"] for m in self.metrics["api_latencies"] if m["success"]]
            if latencies:
                report["summary"]["api_latency"] = {
                    "avg_seconds": sum(latencies) / len(latencies),
                    "min_seconds": min(latencies),
                    "max_seconds": max(latencies),
                    "total_calls": len(self.metrics["api_latencies"]),
                    "successful_calls": len(latencies),
                    "success_rate": len(latencies) / len(self.metrics["api_latencies"])
                }
        
        # Memory Usage Summary
        if self.metrics["memory_usage"]:
            memory_values = [m["process_memory_mb"] for m in self.metrics["memory_usage"]]
            report["summary"]["memory_usage"] = {
                "avg_mb": sum(memory_values) / len(memory_values),
                "peak_mb": max(memory_values),
                "min_mb": min(memory_values)
            }
        
        # CPU Usage Summary
        if self.metrics["cpu_usage"]:
            cpu_values = [m["process_cpu"] for m in self.metrics["cpu_usage"]]
            report["summary"]["cpu_usage"] = {
                "avg_percent": sum(cpu_values) / len(cpu_values),
                "peak_percent": max(cpu_values)
            }
        
        # File Operations Summary
        if self.metrics["file_operations"]:
            file_ops = self.metrics["file_operations"]
            successful_ops = [op for op in file_ops if op["success"]]
            
            if successful_ops:
                durations = [op["duration_seconds"] for op in successful_ops]
                report["summary"]["file_operations"] = {
                    "total_operations": len(file_ops),
                    "successful_operations": len(successful_ops),
                    "avg_duration_seconds": sum(durations) / len(durations),
                    "slowest_operation_seconds": max(durations)
                }
        
        return report
    
    def save_report(self, filename: str = None):
        """Save performance report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Performance report saved to: {filename}")
        return filename
    
    def create_visualizations(self, output_dir: str = "performance_charts"):
        """Create performance visualization charts"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Memory Usage Chart
        if self.metrics["memory_usage"]:
            plt.figure(figsize=(12, 6))
            
            timestamps = [m["timestamp"] for m in self.metrics["memory_usage"]]
            memory_values = [m["process_memory_mb"] for m in self.metrics["memory_usage"]]
            
            # Convert timestamps to relative time
            start_time = min(timestamps)
            relative_times = [(t - start_time) / 60 for t in timestamps]  # Minutes
            
            plt.subplot(2, 1, 1)
            plt.plot(relative_times, memory_values, 'b-', linewidth=2)
            plt.title('Memory Usage Over Time')
            plt.ylabel('Memory (MB)')
            plt.grid(True, alpha=0.3)
            
            # CPU Usage Chart
            if self.metrics["cpu_usage"]:
                cpu_timestamps = [m["timestamp"] for m in self.metrics["cpu_usage"]]
                cpu_values = [m["process_cpu"] for m in self.metrics["cpu_usage"]]
                cpu_relative_times = [(t - start_time) / 60 for t in cpu_timestamps]
                
                plt.subplot(2, 1, 2)
                plt.plot(cpu_relative_times, cpu_values, 'r-', linewidth=2)
                plt.title('CPU Usage Over Time')
                plt.xlabel('Time (minutes)')
                plt.ylabel('CPU (%)')
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'system_metrics.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # API Latency Chart
        if self.metrics["api_latencies"]:
            successful_calls = [m for m in self.metrics["api_latencies"] if m["success"]]
            
            if successful_calls:
                plt.figure(figsize=(10, 6))
                
                latencies = [m["latency_seconds"] for m in successful_calls]
                call_numbers = range(1, len(latencies) + 1)
                
                plt.scatter(call_numbers, latencies, alpha=0.6, s=30)
                plt.axhline(y=sum(latencies)/len(latencies), color='r', linestyle='--', 
                           label=f'Average: {sum(latencies)/len(latencies):.2f}s')
                
                plt.title('API Call Latencies')
                plt.xlabel('Call Number')
                plt.ylabel('Latency (seconds)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                plt.savefig(os.path.join(output_dir, 'api_latencies.png'), dpi=300, bbox_inches='tight')
                plt.close()
        
        print(f"📊 Performance charts saved to: {output_dir}/")

async def run_performance_test():
    """Run a comprehensive performance test"""
    monitor = PerformanceMonitor()
    
    print("🚀 Starting Performance Test")
    print("=" * 50)
    
    # Start monitoring
    monitor.start_monitoring(interval=0.5)
    
    try:
        # Test 1: API Latency Test
        print("\n📡 Testing API Latency...")
        api_tasks = []
        for i in range(10):
            messages = [{"role": "user", "content": f"Test message {i}"}]
            task = monitor.measure_api_latency("openai/gpt-4o-mini", messages)
            api_tasks.append(task)
        
        # Run API calls with some delay
        for task in api_tasks:
            await task
            await asyncio.sleep(0.5)  # Small delay between calls
        
        # Test 2: File Operations Test
        print("\n📁 Testing File Operations...")
        
        # Create test data
        test_data = pd.DataFrame({
            "col1": range(10000),
            "col2": [f"test_data_{i}" for i in range(10000)]
        })
        
        # Test CSV write
        monitor.measure_file_operation(
            "csv_write", 
            test_data.to_csv, 
            "test_performance.csv", 
            index=False
        )
        
        # Test CSV read
        monitor.measure_file_operation(
            "csv_read",
            pd.read_csv,
            "test_performance.csv"
        )
        
        # Test 3: Memory Intensive Operations
        print("\n💾 Testing Memory Intensive Operations...")
        
        # Create large dataset
        large_data = []
        for i in range(50000):
            large_data.append({
                "system_prompt": f"System prompt {i % 100}" * 10,
                "response": f"Response {i}" * 50,
                "evaluation_score": i % 100
            })
        
        large_df = pd.DataFrame(large_data)
        print(f"   Created DataFrame with {len(large_df)} rows")
        
        # Test processing
        from utils.ui_helpers import extract_dimension_scores
        
        # Add proper evaluation questions for testing
        large_df["evaluation_question"] = [
            "Is this response helpful and addresses the user's question effectively? Answer only Y or N." 
            if i % 6 == 0 else
            "Is this response direct and concise without unnecessary fluff? Answer only Y or N."
            for i in range(len(large_df))
        ]
        
        start_time = time.time()
        scores = extract_dimension_scores(large_df)
        end_time = time.time()
        
        print(f"   Processed large dataset in {end_time - start_time:.2f} seconds")
        
        # Clean up
        if os.path.exists("test_performance.csv"):
            os.remove("test_performance.csv")
        
        await asyncio.sleep(2)  # Let monitoring capture final state
        
    finally:
        # Stop monitoring
        monitor.stop_monitoring()
    
    # Generate report
    print("\n📊 Generating Performance Report...")
    report_file = monitor.save_report()
    monitor.create_visualizations()
    
    # Print summary
    report = monitor.generate_report()
    print("\n" + "=" * 50)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    if "api_latency" in report["summary"]:
        api_summary = report["summary"]["api_latency"]
        print(f"🌐 API Performance:")
        print(f"   Average Latency: {api_summary['avg_seconds']:.2f}s")
        print(f"   Success Rate: {api_summary['success_rate']*100:.1f}%")
        print(f"   Total Calls: {api_summary['total_calls']}")
    
    if "memory_usage" in report["summary"]:
        mem_summary = report["summary"]["memory_usage"]
        print(f"💾 Memory Usage:")
        print(f"   Average: {mem_summary['avg_mb']:.1f} MB")
        print(f"   Peak: {mem_summary['peak_mb']:.1f} MB")
    
    if "cpu_usage" in report["summary"]:
        cpu_summary = report["summary"]["cpu_usage"]
        print(f"⚡ CPU Usage:")
        print(f"   Average: {cpu_summary['avg_percent']:.1f}%")
        print(f"   Peak: {cpu_summary['peak_percent']:.1f}%")
    
    if "file_operations" in report["summary"]:
        file_summary = report["summary"]["file_operations"]
        print(f"📁 File Operations:")
        print(f"   Total Operations: {file_summary['total_operations']}")
        print(f"   Average Duration: {file_summary['avg_duration_seconds']:.3f}s")
    
    print(f"\n📄 Full report: {report_file}")
    print("📊 Charts: performance_charts/")

if __name__ == "__main__":
    asyncio.run(run_performance_test())

#!/usr/bin/env python3
"""
Comprehensive Issue Identification Tool

Analyzes the codebase for potential issues and vulnerabilities:
1. Code quality issues
2. Security vulnerabilities  
3. Performance bottlenecks
4. Error handling gaps
5. Configuration issues
6. Dependency problems
"""

import ast
import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Set
import subprocess
import importlib.util

class IssueIdentifier:
    def __init__(self):
        self.issues = []
        self.project_root = Path(__file__).parent
        
    def add_issue(self, category: str, severity: str, file_path: str, line_number: int, 
                  description: str, recommendation: str = ""):
        """Add an identified issue"""
        issue = {
            "category": category,
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "file": file_path,
            "line": line_number,
            "description": description,
            "recommendation": recommendation
        }
        self.issues.append(issue)
    
    def analyze_python_file(self, file_path: Path):
        """Analyze a Python file for issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                self.add_issue(
                    "SYNTAX", "CRITICAL", str(file_path), e.lineno or 0,
                    f"Syntax error: {e.msg}",
                    "Fix syntax error"
                )
                return
            
            # Analyze AST
            self._analyze_ast(tree, file_path, content)
            
            # Analyze raw content
            self._analyze_content(content, file_path)
            
        except Exception as e:
            self.add_issue(
                "ANALYSIS", "HIGH", str(file_path), 0,
                f"Failed to analyze file: {e}",
                "Check file encoding and permissions"
            )
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, content: str):
        """Analyze AST for issues"""
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # Check for hardcoded secrets
            if isinstance(node, ast.Str):
                self._check_hardcoded_secrets(node, file_path, lines)
            
            # Check for dangerous functions
            if isinstance(node, ast.Call):
                self._check_dangerous_functions(node, file_path)
            
            # Check for exception handling
            if isinstance(node, ast.Try):
                self._check_exception_handling(node, file_path)
            
            # Check for async/await usage
            if isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
                self._check_async_patterns(node, file_path)
            
            # Check for imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._check_imports(node, file_path)
    
    def _check_hardcoded_secrets(self, node: ast.Str, file_path: Path, lines: List[str]):
        """Check for hardcoded secrets"""
        value = node.s.lower()
        
        # Common secret patterns
        secret_patterns = [
            r'api[_-]?key',
            r'secret[_-]?key',
            r'password',
            r'token',
            r'auth[_-]?key',
            r'access[_-]?key'
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, value) and len(node.s) > 10:
                # Skip if it looks like a placeholder
                if not any(placeholder in value for placeholder in ['your_', 'example', 'test', 'dummy']):
                    self.add_issue(
                        "SECURITY", "HIGH", str(file_path), getattr(node, 'lineno', 0),
                        f"Potential hardcoded secret: {node.s[:50]}...",
                        "Use environment variables or secure configuration"
                    )
    
    def _check_dangerous_functions(self, node: ast.Call, file_path: Path):
        """Check for dangerous function calls"""
        dangerous_functions = {
            'eval': "Use ast.literal_eval() or safer alternatives",
            'exec': "Avoid dynamic code execution",
            'compile': "Review dynamic compilation usage",
            'input': "Validate user input thoroughly",
            '__import__': "Use importlib for dynamic imports"
        }
        
        if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
            self.add_issue(
                "SECURITY", "MEDIUM", str(file_path), getattr(node, 'lineno', 0),
                f"Potentially dangerous function: {node.func.id}",
                dangerous_functions[node.func.id]
            )
    
    def _check_exception_handling(self, node: ast.Try, file_path: Path):
        """Check exception handling patterns"""
        # Check for bare except clauses
        for handler in node.handlers:
            if handler.type is None:
                self.add_issue(
                    "CODE_QUALITY", "MEDIUM", str(file_path), getattr(handler, 'lineno', 0),
                    "Bare except clause catches all exceptions",
                    "Catch specific exception types"
                )
        
        # Check if exceptions are logged or re-raised
        has_logging = False
        has_reraise = False
        
        for handler in node.handlers:
            for stmt in handler.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    if hasattr(stmt.value.func, 'attr') and 'log' in str(stmt.value.func.attr):
                        has_logging = True
                if isinstance(stmt, ast.Raise):
                    has_reraise = True
        
        if not has_logging and not has_reraise:
            self.add_issue(
                "CODE_QUALITY", "LOW", str(file_path), getattr(node, 'lineno', 0),
                "Exception caught but not logged or re-raised",
                "Add logging or re-raise exceptions appropriately"
            )
    
    def _check_async_patterns(self, node: ast.AST, file_path: Path):
        """Check async/await patterns"""
        if isinstance(node, ast.AsyncFunctionDef):
            # Check if async function actually uses await
            has_await = False
            for child in ast.walk(node):
                if isinstance(child, ast.Await):
                    has_await = True
                    break
            
            if not has_await:
                self.add_issue(
                    "CODE_QUALITY", "LOW", str(file_path), getattr(node, 'lineno', 0),
                    f"Async function '{node.name}' doesn't use await",
                    "Consider making it a regular function"
                )
    
    def _check_imports(self, node: ast.AST, file_path: Path):
        """Check import patterns"""
        if isinstance(node, ast.ImportFrom) and node.module == "*":
            self.add_issue(
                "CODE_QUALITY", "MEDIUM", str(file_path), getattr(node, 'lineno', 0),
                "Wildcard import (from module import *)",
                "Import specific names or use qualified imports"
            )
    
    def _analyze_content(self, content: str, file_path: Path):
        """Analyze raw content for issues"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for TODO/FIXME comments
            if re.search(r'#.*\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
                self.add_issue(
                    "MAINTENANCE", "LOW", str(file_path), i,
                    f"TODO/FIXME comment: {line.strip()}",
                    "Address or track this item"
                )
            
            # Check for print statements (should use logging)
            if re.search(r'\bprint\s*\(', line) and 'logger' not in content:
                self.add_issue(
                    "CODE_QUALITY", "LOW", str(file_path), i,
                    "Using print() instead of logging",
                    "Use logging framework for better control"
                )
            
            # Check for long lines
            if len(line) > 120:
                self.add_issue(
                    "CODE_QUALITY", "LOW", str(file_path), i,
                    f"Line too long ({len(line)} characters)",
                    "Break long lines for better readability"
                )
    
    def check_dependencies(self):
        """Check for dependency issues"""
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            self.add_issue(
                "CONFIGURATION", "MEDIUM", str(requirements_file), 0,
                "No requirements.txt file found",
                "Create requirements.txt to pin dependencies"
            )
            return
        
        try:
            with open(requirements_file, 'r') as f:
                requirements = f.read().strip().split('\n')
            
            for i, req in enumerate(requirements, 1):
                req = req.strip()
                if not req or req.startswith('#'):
                    continue
                
                # Check for unpinned versions
                if '==' not in req and '>=' not in req and '~=' not in req:
                    self.add_issue(
                        "CONFIGURATION", "MEDIUM", str(requirements_file), i,
                        f"Unpinned dependency: {req}",
                        "Pin dependency versions for reproducible builds"
                    )
                
                # Check for known vulnerable packages (basic check)
                vulnerable_packages = ['urllib3<1.26.5', 'requests<2.25.0']
                for vuln in vulnerable_packages:
                    if req.startswith(vuln.split('<')[0]):
                        self.add_issue(
                            "SECURITY", "HIGH", str(requirements_file), i,
                            f"Potentially vulnerable package: {req}",
                            "Update to latest secure version"
                        )
        
        except Exception as e:
            self.add_issue(
                "CONFIGURATION", "MEDIUM", str(requirements_file), 0,
                f"Error reading requirements.txt: {e}",
                "Fix requirements.txt format"
            )
    
    def check_configuration_files(self):
        """Check configuration files for issues"""
        config_files = [
            ".env",
            ".env.example", 
            ".gitignore",
            "app.py"  # Check Streamlit config
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            
            if config_file == ".env" and file_path.exists():
                self.add_issue(
                    "SECURITY", "HIGH", str(file_path), 0,
                    ".env file exists in repository",
                    "Remove .env from repository, use .env.example instead"
                )
            
            if config_file == ".gitignore":
                if not file_path.exists():
                    self.add_issue(
                        "CONFIGURATION", "MEDIUM", str(file_path), 0,
                        "No .gitignore file found",
                        "Create .gitignore to exclude sensitive files"
                    )
                else:
                    # Check if important patterns are ignored
                    with open(file_path, 'r') as f:
                        gitignore_content = f.read()
                    
                    important_patterns = ['.env', '__pycache__', '*.pyc', '.DS_Store']
                    for pattern in important_patterns:
                        if pattern not in gitignore_content:
                            self.add_issue(
                                "CONFIGURATION", "LOW", str(file_path), 0,
                                f"Missing gitignore pattern: {pattern}",
                                f"Add {pattern} to .gitignore"
                            )
    
    def check_file_permissions(self):
        """Check for file permission issues"""
        for py_file in self.project_root.rglob("*.py"):
            try:
                stat = py_file.stat()
                mode = oct(stat.st_mode)[-3:]
                
                # Check if file is executable (might be unintended)
                if mode.endswith(('5', '7')) and py_file.name != "__main__.py":
                    self.add_issue(
                        "SECURITY", "LOW", str(py_file), 0,
                        f"Python file has execute permissions: {mode}",
                        "Remove execute permissions if not needed"
                    )
            except Exception:
                pass  # Skip permission check on systems that don't support it
    
    def check_logging_configuration(self):
        """Check logging configuration"""
        has_logging_config = False
        
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                if 'logging.basicConfig' in content or 'loguru' in content:
                    has_logging_config = True
                    break
            except Exception:
                continue
        
        if not has_logging_config:
            self.add_issue(
                "CONFIGURATION", "MEDIUM", "project", 0,
                "No logging configuration found",
                "Configure logging for better debugging and monitoring"
            )
    
    def run_analysis(self):
        """Run complete analysis"""
        print("🔍 Starting Comprehensive Issue Analysis")
        print("=" * 60)
        
        # Analyze Python files
        print("📄 Analyzing Python files...")
        python_files = list(self.project_root.rglob("*.py"))
        for py_file in python_files:
            if 'venv' not in str(py_file) and '__pycache__' not in str(py_file):
                self.analyze_python_file(py_file)
        
        # Check dependencies
        print("📦 Checking dependencies...")
        self.check_dependencies()
        
        # Check configuration
        print("⚙️  Checking configuration...")
        self.check_configuration_files()
        
        # Check file permissions
        print("🔒 Checking file permissions...")
        self.check_file_permissions()
        
        # Check logging
        print("📝 Checking logging configuration...")
        self.check_logging_configuration()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate and display issue report"""
        print("\n" + "=" * 60)
        print("🚨 ISSUE ANALYSIS REPORT")
        print("=" * 60)
        
        # Group issues by severity
        by_severity = {}
        for issue in self.issues:
            severity = issue['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)
        
        # Summary
        total_issues = len(self.issues)
        print(f"📊 Total Issues Found: {total_issues}")
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = len(by_severity.get(severity, []))
            if count > 0:
                emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🔵'}[severity]
                print(f"{emoji} {severity}: {count}")
        
        # Detailed issues
        if self.issues:
            print("\n📋 DETAILED ISSUES:")
            print("-" * 60)
            
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                issues = by_severity.get(severity, [])
                if issues:
                    print(f"\n{severity} ISSUES:")
                    for issue in issues:
                        print(f"  📁 {issue['file']}:{issue['line']}")
                        print(f"     🏷️  {issue['category']}: {issue['description']}")
                        if issue['recommendation']:
                            print(f"     💡 {issue['recommendation']}")
                        print()
        
        # Save report to file
        timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"issue_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_issues': total_issues,
                    'by_severity': {k: len(v) for k, v in by_severity.items()},
                    'generated_at': __import__('datetime').datetime.now().isoformat()
                },
                'issues': self.issues
            }, f, indent=2)
        
        print(f"📄 Full report saved to: {report_file}")
        
        # Return summary for programmatic use
        return {
            'total_issues': total_issues,
            'critical': len(by_severity.get('CRITICAL', [])),
            'high': len(by_severity.get('HIGH', [])),
            'medium': len(by_severity.get('MEDIUM', [])),
            'low': len(by_severity.get('LOW', []))
        }

if __name__ == "__main__":
    analyzer = IssueIdentifier()
    analyzer.run_analysis()
    summary = analyzer.generate_report()
    
    # Extract summary stats
    by_severity = {}
    for issue in analyzer.issues:
        severity = issue['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)
    
    summary_stats = {
        'total_issues': len(analyzer.issues),
        'critical': len(by_severity.get('CRITICAL', [])),
        'high': len(by_severity.get('HIGH', [])),
        'medium': len(by_severity.get('MEDIUM', [])),
        'low': len(by_severity.get('LOW', []))
    }
    
    # Exit with error code if critical or high issues found
    if summary_stats['critical'] > 0 or summary_stats['high'] > 0:
        print(f"\n⚠️  Found {summary_stats['critical']} critical and {summary_stats['high']} high severity issues!")
        sys.exit(1)
    else:
        print("\n✅ No critical or high severity issues found!")
        sys.exit(0)

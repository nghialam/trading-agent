#!/usr/bin/env python3
"""
Project Setup Verification Script
Checks that all necessary files and directories exist for the trading agent
"""

import os
from pathlib import Path


def check_project_structure():
    """Verify the complete project structure"""
    
    required_files = {
        'main.py': 'Entry point script',
        'README.md': 'Project documentation',
        'requirements.txt': 'Dependencies',
        '.gitignore': 'Git ignore rules',
        
        # Source files
        'src/__init__.py': 'Source package init',
        'src/agent.py': 'Main trading agent',
        'src/scanning.py': 'Market data scanner',
        'src/evaluation.py': 'Technical evaluation engine',
        'src/strategy.py': 'Signal generator strategy',
        'src/dispatcher.py': 'Signal dispatch layer',
        'src/utils.py': 'Utility functions',
        
        # Test files
        'tests/__init__.py': 'Tests package init',
        'tests/test_agent.py': 'Agent tests',
        'tests/test_scanning.py': 'Scanner tests',
        'tests/test_evaluation.py': 'Evaluation tests',
        'tests/test_strategy.py': 'Strategy tests',
        'tests/test_dispatcher.py': 'Dispatcher tests',
        
        # Config and backtest
        'config/strategies.yaml': 'Strategy configuration',
        'backtest/__init__.py': 'Backtest package init',
        'backtest/runner.py': 'Backtest runner',
    }
    
    print("=" * 60)
    print("VnStock Trading Agent - Project Structure Check")
    print("=" * 60)
    
    missing_files = []
    existing_files = []
    
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            print(f"OK {file_path:30} - {description}")
            existing_files.append(file_path)
        else:
            print(f"MISSING {file_path:30} - MISSING")
            missing_files.append(file_path)
    
    print("\n" + "=" * 60)
    print(f"Summary: {len(existing_files)} files found, "
          f"{len(missing_files)} files missing")
    print("=" * 60)
    
    if missing_files:
        print("\nMissing files:")
        for f in missing_files:
            print(f"   - {f}")
        return False
    else:
        print("\nAll required files present!")
        return True


if __name__ == "__main__":
    check_project_structure()

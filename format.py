#!/usr/bin/env python3
"""
Format Python files using black and isort
Usage: python format.py [path]
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print the result"""
    print(f"Running {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ {description} completed")
        if result.stdout.strip():
            print(result.stdout)
    else:
        print(f"✗ {description} failed")
        if result.stderr:
            print(result.stderr)
    
    return result.returncode

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "app/"
    
    if not os.path.exists(path):
        print(f"Path '{path}' does not exist")
        sys.exit(1)
    
    print(f"Formatting Python files in: {path}")
    
    # Sort imports
    isort_cmd = f"isort {path} --profile black"
    isort_result = run_command(isort_cmd, "import sorting")
    
    # Format code
    black_cmd = f"black {path}"
    black_result = run_command(black_cmd, "code formatting")
    
    if isort_result == 0 and black_result == 0:
        print("\n🎉 All formatting completed successfully!")
    else:
        print("\n⚠️  Some formatting operations failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
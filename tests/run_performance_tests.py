"""
Script to run performance tests and display summary statistics
"""
import subprocess
import sys
import re
from collections import defaultdict

def run_performance_tests():
    """Run all performance tests and collect results"""
    print("=" * 80)
    print("Running Performance Tests")
    print("=" * 80)
    print()
    
    # Run all performance tests with verbose output
    result = subprocess.run(
        ["pytest", "-v", "-s", "-k", "Performance", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    # Print the output
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Extract performance metrics from output
    metrics = defaultdict(dict)
    current_test = None
    
    for line in result.stdout.split('\n'):
        # Match performance output lines
        if '[PERFORMANCE]' in line:
            current_test = line.split('[PERFORMANCE]')[1].strip().rstrip(':')
        elif current_test and 'Average:' in line:
            match = re.search(r'Average:\s+([\d.]+)', line)
            if match:
                metrics[current_test]['average'] = float(match.group(1))
        elif current_test and 'Median:' in line:
            match = re.search(r'Median:\s+([\d.]+)', line)
            if match:
                metrics[current_test]['median'] = float(match.group(1))
        elif current_test and 'Min:' in line:
            match = re.search(r'Min:\s+([\d.]+)', line)
            if match:
                metrics[current_test]['min'] = float(match.group(1))
        elif current_test and 'Max:' in line:
            match = re.search(r'Max:\s+([\d.]+)', line)
            if match:
                metrics[current_test]['max'] = float(match.group(1))
        elif current_test and 'Std Dev:' in line:
            match = re.search(r'Std Dev:\s+([\d.]+)', line)
            if match:
                metrics[current_test]['std_dev'] = float(match.group(1))
    
    # Print summary
    if metrics:
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        print()
        
        for test_name, stats in metrics.items():
            print(f"📊 {test_name}")
            print("-" * 80)
            if 'average' in stats:
                print(f"  Average:     {stats['average']:.4f}s")
            if 'median' in stats:
                print(f"  Median:      {stats['median']:.4f}s")
            if 'min' in stats:
                print(f"  Min:         {stats['min']:.4f}s")
            if 'max' in stats:
                print(f"  Max:         {stats['max']:.4f}s")
            if 'std_dev' in stats:
                print(f"  Std Dev:     {stats['std_dev']:.4f}s")
            print()
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_performance_tests())


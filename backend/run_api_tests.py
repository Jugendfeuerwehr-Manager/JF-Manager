#!/usr/bin/env python
"""
Test runner script for JF-Manager API tests

Usage:
    python run_api_tests.py              # Run all tests
    python run_api_tests.py --auth       # Run authentication tests only
    python run_api_tests.py --coverage   # Run with coverage report
    python run_api_tests.py --verbose    # Run with verbose output
"""

import sys
import os
import subprocess
import argparse


def run_tests(test_path='api_tests', verbosity=1, with_coverage=False):
    """Run Django tests with optional coverage"""
    
    if with_coverage:
        # Run with coverage
        print("Running tests with coverage analysis...")
        cmd = [
            'coverage', 'run',
            '--source=.',
            'manage.py', 'test', test_path,
            f'--verbosity={verbosity}'
        ]
        subprocess.run(cmd)
        
        print("\n" + "="*70)
        print("COVERAGE REPORT")
        print("="*70 + "\n")
        
        # Show coverage report
        subprocess.run(['coverage', 'report', '--include=*/api/*,*/views.py,*/serializers.py'])
        
        print("\n" + "="*70)
        print("Generate HTML coverage report with: coverage html")
        print("="*70)
    else:
        # Run without coverage
        cmd = ['python', 'manage.py', 'test', test_path, f'--verbosity={verbosity}']
        subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='Run JF-Manager API tests')
    parser.add_argument('--auth', action='store_true',
                       help='Run authentication tests only')
    parser.add_argument('--permissions', action='store_true',
                       help='Run permission tests only')
    parser.add_argument('--users', action='store_true',
                       help='Run user API tests only')
    parser.add_argument('--members', action='store_true',
                       help='Run member API tests only')
    parser.add_argument('--inventory', action='store_true',
                       help='Run inventory API tests only')
    parser.add_argument('--orders', action='store_true',
                       help='Run orders API tests only')
    parser.add_argument('--qualifications', action='store_true',
                       help='Run qualifications API tests only')
    parser.add_argument('--crud', action='store_true',
                       help='Run CRUD operation tests only')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage analysis')
    parser.add_argument('--verbose', action='store_true',
                       help='Run tests with verbose output')
    
    args = parser.parse_args()
    
    # Determine test path
    test_path = 'api_tests'
    
    if args.auth:
        test_path = 'api_tests.test_api_comprehensive.AuthenticationTests'
    elif args.permissions:
        test_path = 'api_tests.test_api_comprehensive.PermissionsTests'
    elif args.users:
        test_path = 'api_tests.test_api_comprehensive.UserAPITests'
    elif args.members:
        test_path = 'api_tests.test_api_comprehensive.MembersAPITests'
    elif args.inventory:
        test_path = 'api_tests.test_api_comprehensive.CRUDOperationsTests'
    elif args.orders:
        test_path = 'api_tests.test_api_comprehensive.OrdersAPITests'
    elif args.qualifications:
        test_path = 'api_tests.test_api_comprehensive.QualificationsAPITests'
    elif args.crud:
        test_path = 'api_tests.test_api_comprehensive.CRUDOperationsTests'
    
    # Determine verbosity
    verbosity = 2 if args.verbose else 1
    
    print("="*70)
    print("JF-MANAGER API TEST SUITE")
    print("="*70)
    print(f"Running: {test_path}")
    print(f"Verbosity: {verbosity}")
    print(f"Coverage: {'Yes' if args.coverage else 'No'}")
    print("="*70 + "\n")
    
    # Run tests
    run_tests(test_path, verbosity, args.coverage)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import json
import os
import argparse
from typing import List, Dict, Any


def load_exclude_files(config_path: str) -> set:
    """Load exclude files configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            # Extract just the filenames from the file paths in the config
            exclude_filenames = set()
            for item in config_data:
                if isinstance(item, dict) and 'file_path' in item:
                    filename = os.path.basename(item['file_path'])
                    if filename:
                        exclude_filenames.add(filename)
                elif isinstance(item, str):
                    # Handle case where config is just a list of filenames
                    exclude_filenames.add(item)
            return exclude_filenames
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return set()


def is_markdown_file(file_path: str) -> bool:
    """Check if a file is a markdown file."""
    return file_path.lower().endswith('.md')


def get_markdown_files_in_dir(directory: str, exclude_files: set) -> List[Dict[str, Any]]:
    """Recursively get all markdown files in directory excluding those in exclude_files."""
    result = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if is_markdown_file(file_path):
                # Check if file name (without path) is in exclude files
                file_name = os.path.basename(file_path)
                if file_name not in exclude_files:
                    result.append({
                        'file_path': os.path.abspath(file_path),
                        'status': 'pending'
                    })
    
    return result


def process_single_file(file_path: str) -> List[Dict[str, Any]]:
    """Process a single markdown file."""
    if os.path.exists(file_path) and is_markdown_file(file_path):
        return [{
            'file_path': os.path.abspath(file_path),
            'status': 'pending'
        }]
    return []


def process_directory(directory: str, exclude_files: set) -> List[Dict[str, Any]]:
    """Process a directory of markdown files."""
    if not os.path.isdir(directory):
        return []
    
    return get_markdown_files_in_dir(directory, exclude_files)


def main():
    parser = argparse.ArgumentParser(description='Process markdown files and generate status JSON.')
    parser.add_argument('config_path', help='Absolute path to exclude-files.json configuration file')
    parser.add_argument('input_path', help='Absolute path to markdown file or directory')
    parser.add_argument('output_dir', help='Absolute path to directory where file_status.json will be saved')
    
    args = parser.parse_args()
    
    # Load exclude files configuration
    exclude_files = load_exclude_files(args.config_path)
    
    # Process input
    if os.path.isfile(args.input_path):
        # Single file mode
        result = process_single_file(args.input_path)
    else:
        # Directory mode
        result = process_directory(args.input_path, exclude_files)
    
    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Write result to file_status.json
    output_file = os.path.join(args.output_dir, 'file_status.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Processing complete. Results saved to {output_file}")
    print(f"Found {len(result)} markdown files.")


if __name__ == '__main__':
    main()
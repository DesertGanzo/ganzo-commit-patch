#!/usr/bin/env python3
import os
import re
import sys
import zipfile
import argparse
from datetime import datetime
from subprocess import check_output, CalledProcessError

def get_git_root():
    try:
        return check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
    except CalledProcessError:
        print("Error: Not a Git repository")
        sys.exit(1)

def get_changed_files(base_ref, head_ref):
    # List files changed between two refs (only committed changes)
    cmd = ['git', 'diff', '--name-only', '--diff-filter=d', f'{base_ref}..{head_ref}']
    try:
        files = check_output(cmd).decode().splitlines()
    except CalledProcessError as e:
        print(f"Error running git diff: {e}")
        sys.exit(1)
    return [f for f in files if os.path.isfile(f)]

def get_latest_tag():
    try:
        return check_output(['git', 'describe', '--abbrev=0', '--tags']).decode().strip()
    except CalledProcessError:
        return None

def get_commit_message(base_ref, head_ref):
    # Aggregate commit messages between two refs
    try:
        return check_output(['git', 'log', f'{base_ref}..{head_ref}', '--pretty=%s']).decode().strip().replace("\n", " |")
    except CalledProcessError:
        return ''

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '', name.replace(' ', '_'))

def get_next_version(output_dir):
    pattern = re.compile(r'update_(\d+\.\d+)')
    versions = []
    for f in os.listdir(output_dir):
        match = pattern.match(f)
        if match:
            versions.append(float(match.group(1)))
    return max(versions) + 0.1 if versions else 0.1

def create_update_zip(files, output_dir, version, message):
    sanitized_msg = sanitize_filename(message[:20])
    timestamp = datetime.now().strftime('%Y%m%d')
    zip_name = f"update_{version:.1f}_{timestamp}_{sanitized_msg}.zip"
    zip_path = os.path.join(output_dir, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file)
            print(f"Added: {file}")
    return zip_path

def main():
    parser = argparse.ArgumentParser(
        description='Create incremental update zip from Git changes')
    parser.add_argument('--output', '-o', default='updates', help='Output directory for zip files')
    parser.add_argument('--base', '-b', help='Base ref (tag or commit)', default=None)
    parser.add_argument('--head', '-H', help='Head ref (branch or commit)', default='HEAD')
    args = parser.parse_args()

    git_root = get_git_root()
    os.chdir(git_root)

    base_ref = args.base or get_latest_tag() or 'HEAD~1'
    head_ref = args.head

    os.makedirs(args.output, exist_ok=True)

    changed_files = get_changed_files(base_ref, head_ref)
    if not changed_files:
        print(f"No changed files found between {base_ref} and {head_ref}")
        return

    version = get_next_version(args.output)
    commit_message = get_commit_message(base_ref, head_ref) or f"{base_ref}_to_{head_ref}"

    print(f"Creating update package v{version:.1f}")
    print(f"Changes from {base_ref} to {head_ref}")
    print(f"Files count: {len(changed_files)}")

    zip_path = create_update_zip(changed_files, args.output, version, commit_message)
    print(f"\nUpdate package created: {zip_path}")
    print(f"Size: {os.path.getsize(zip_path)/1024:.1f} KB")

if __name__ == "__main__":
    main()

import subprocess
import sys
import os
import re

def get_current_version():
    """استخراج نسخه فعلی از فایل pyproject.toml"""
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
            match = re.search(r'version = "(.*?)"', content)
            if match:
                return match.group(1)
    except FileNotFoundError:
        pass
    return "0.1.0"

def increment_version(version, part="patch"):
    """افزایش شماره نسخه بر اساس نوع تغییر"""
    major, minor, patch = map(int, version.split('.'))
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"

def run_command(command):
    """اجرای دستورات سیستم و مدیریت خطا"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def trigger_release():
    print("--- ReportFlow Release Trigger Tool ---")
    
    current_v = get_current_version()
    print(f"Current Version: {current_v}")
    
    choice = input("Select upgrade type [patch/minor/major] (default: patch): ").lower() or "patch"
    new_v = increment_version(current_v, choice)
    
    confirm = input(f"Release version v{new_v}? (y/n): ").lower()
    if confirm != 'y':
        print("Release cancelled.")
        return

    # 1. Update pyproject.toml (optional but recommended for consistency)
    print(f"Updating pyproject.toml to v{new_v}...")
    with open("pyproject.toml", "r") as f:
        content = f.read()
    new_content = re.sub(r'version = ".*?"', f'version = "{new_v}"', content)
    with open("pyproject.toml", "w") as f:
        f.write(new_content)

    # 2. Git Commands
    print("Committing version change and creating tag...")
    commands = [
        "git add pyproject.toml",
        f'git commit -m "chore: bump version to v{new_v}"',
        "git push origin main",
        f"git tag v{new_v}",
        f"git push origin v{new_v}"
    ]
    
    for cmd in commands:
        print(f"Executing: {cmd}")
        if not run_command(cmd):
            print("Failed to complete release sequence.")
            return

    print(f"\n🚀 Success! Version v{new_v} has been pushed.")
    print("The CI/CD pipeline has been triggered. Check GitHub Actions for progress.")

if __name__ == "__main__":
    trigger_release()

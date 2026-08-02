import os
import requests
import subprocess
import sys

def download_latest_release(repo_owner, repo_name, output_name="ReportFlow.exe"):
    """
    دانلود آخرین نسخه اجرایی (.exe) از بخش Releases گیتهاب.
    """
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    print(f"Checking for latest release at {api_url}...")
    
    response = requests.get(api_url)
    response.raise_for_status()
    release_data = response.json()
    
    tag = release_data['tag_name']
    print(f"Latest version found: {tag}")
    
    # پیدا کردن فایل exe در دارایی‌ها
    exe_url = None
    for asset in release_data['assets']:
        if asset['name'].endswith('.exe'):
            exe_url = asset['browser_download_url']
            break
    
    if not exe_url:
        print("No .exe file found in the latest release.")
        return None
    
    print(f"Downloading {output_name} from {exe_url}...")
    exe_response = requests.get(exe_url, stream=True)
    exe_response.raise_for_status()
    
    with open(output_name, 'wb') as f:
        for chunk in exe_response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print("Download complete.")
    return os.path.abspath(output_name)

def run_exe(exe_path, config_path):
    """
    اجرای فایل دانلود شده با پارامترهای مشخص.
    """
    if not os.path.exists(exe_path):
        print("Executable not found.")
        return
    
    print(f"Running {exe_path}...")
    try:
        # مثال اجرای ابزار با یک فایل کانفیگ
        subprocess.run([exe_path, config_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    # اطلاعات مخزن شما
    OWNER = "Ali-Marandi"
    REPO = "reportflow-automation"
    
    # ۱. دانلود آخرین نسخه
    exe = download_latest_release(OWNER, REPO)
    
    if exe:
        # ۲. اجرا (در صورت وجود فایل کانفیگ)
        # این بخش را می‌توانید بر اساس نیاز خود تغییر دهید
        if len(sys.argv) > 1:
            run_exe(exe, sys.argv[1])
        else:
            print(f"\nDone! You can now run the tool using: .\\{os.path.basename(exe)} your_config.json")

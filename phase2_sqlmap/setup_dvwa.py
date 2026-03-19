#!/usr/bin/env python3
import subprocess
import re
import sys
import os

def setup_dvwa():
    print("[Setup] Getting DVWA ready for testing...")
    
    csrf_token = subprocess.run(
        ["curl", "-s", "http://localhost:8081/login.php"],
        capture_output=True, text=True
    ).stdout
    
    match = re.search(r"name='user_token' value='([^']+)'", csrf_token)
    if not match:
        print("[Setup] Could not find CSRF token")
        return False
    
    token = match.group(1)
    
    result = subprocess.run(
        ["curl", "-s", "-c", "/tmp/dvwa_cookies.txt", 
         "-d", f"username=admin&password=password&Login=Login&user_token={token}",
         "http://localhost:8081/login.php"],
        capture_output=True, text=True
    )
    
    security = subprocess.run(
        ["curl", "-s", "-b", "/tmp/dvwa_cookies.txt",
         "-d", "security=low&set=seclev",
         "http://localhost:8081/security.php"],
        capture_output=True, text=True
    )
    
    try:
        with open("/tmp/dvwa_cookies.txt", "r") as f:
            content = f.read()
            sess_match = re.search(r"PHPSESSID\s+(\S+)", content)
            if sess_match:
                sess_id = sess_match.group(1)
                cookie = f"PHPSESSID={sess_id}; security=low"
                with open("/tmp/dvwa_session.txt", "w") as cf:
                    cf.write(cookie)
                print(f"[Setup] Session saved: {cookie}")
    except Exception as e:
        print(f"[Setup] Could not save session: {e}")
    
    if "low" in security.stdout.lower():
        print("[Setup] DVWA security set to LOW")
        return True
    
    print("[Setup] DVWA login completed")
    return True

if __name__ == "__main__":
    setup_dvwa()

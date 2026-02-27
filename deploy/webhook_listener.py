import subprocess
import hmac
import hashlib
import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
GITHUB_SECRET = os.environ.get("GITHUB_SECRET", "YOUR_OPENSSL_GENERATED_SECRET")
UPDATE_SCRIPT = "/opt/discord-bots/update.sh"
BOT_DIR = "/opt/discord-bots/my-bot"
# ---------------------

def verify_signature(payload_body, secret_token, signature_header):
    if not signature_header: return False
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

def get_current_branch():
    try:
        # Runs 'git rev-parse --abbrev-ref HEAD' to get the current branch of the repo
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                cwd=BOT_DIR, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting current branch: {e}")
        return "main" # Fallback

@app.route('/deploy', methods=['POST'])
def deploy():
    # 1. Verify Signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, GITHUB_SECRET, signature):
        return jsonify({"message": "Invalid signature"}), 403

    # 2. Extract Branch from Payload
    payload = request.json
    pushed_ref = payload.get('ref', '')
    
    # 3. Smart Branch Checking
    current_branch = get_current_branch()
    expected_ref = f"refs/heads/{current_branch}"
    
    if pushed_ref != expected_ref:
        return jsonify({
            "message": f"Push event ignored. Server is tracking '{current_branch}', but received push for '{pushed_ref}'."
        }), 200

    # 4. Trigger Deployment
    try:
        subprocess.run([UPDATE_SCRIPT, current_branch], check=True)
        return jsonify({"message": f"Deployment triggered for branch: {current_branch}"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

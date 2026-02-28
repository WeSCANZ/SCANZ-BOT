import hashlib
import hmac
import os
import subprocess

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# Load secret from environment variable for security
GITHUB_SECRET = os.getenv("GITHUB_SECRET", "YOUR_OPENSSL_GENERATED_SECRET")
UPDATE_SCRIPT = "/opt/discord-bots/update.sh"
# ---------------------

def verify_signature(payload_body, secret_token, signature_header):
    if not signature_header: return False
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

@app.route('/deploy', methods=['POST'])
def deploy():
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, GITHUB_SECRET, signature):
        return jsonify({"message": "Invalid signature"}), 403

    try:
        subprocess.run([UPDATE_SCRIPT], check=True)
        return jsonify({"message": "Deployment triggered"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

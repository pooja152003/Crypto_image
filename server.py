import base64
import os
import cv2
import numpy as np
from flask_cors import CORS
from flask import Flask, request, jsonify
from random import randrange, getrandbits

app = Flask(__name__)
CORS(app)
# -------------------------
# RSA UTILITIES
# -------------------------
def power(a, d, n):
    result = 1
    a = a % n
    while d > 0:
        if d & 1:
            result = (result * a) % n
        a = (a * a) % n
        d >>= 1
    return result

def miller_rabin_test(n, d):
    a = randrange(2, n - 2)
    x = power(a, d, n)
    if x == 1 or x == n - 1:
        return True
    while d != n - 1:
        x = (x * x) % n
        d <<= 1
        if x == 1:
            return False
        if x == n - 1:
            return True
    return False

def is_prime(n, k=8):
    if n <= 1 or n % 2 == 0:
        return False
    if n in (2, 3):
        return True
    d = n - 1
    while d % 2 == 0:
        d //= 2
    for _ in range(k):
        if not miller_rabin_test(n, d):
            return False
    return True

def generate_prime(bits):
    while True:
        p = getrandbits(bits)
        p |= (1 << bits - 1) | 1
        if is_prime(p):
            return p

def mod_inverse(a, m):
    m0, x0, x1 = m, 0, 1
    while a > 1:
        q = a // m
        a, m = m, a % m
        x0, x1 = x1 - q * x0, x0
    return x1 + m0 if x1 < 0 else x1

# -------------------------
# RSA KEY GENERATION
# -------------------------
bits = 256
P = generate_prime(bits)
Q = generate_prime(bits)
N = P * Q
phi = (P - 1) * (Q - 1)
E = 65537
D = mod_inverse(E, phi)

print("RSA Keys Ready")

# -------------------------
# RSA FRAME ENCRYPTION
# -------------------------
def rsa_encrypt_frame(image):
    small = cv2.resize(image, (160, 120))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    flat = gray.flatten()
    encrypted = [pow(int(v), E, N) for v in flat]
    mod256 = np.array([c % 256 for c in encrypted], dtype=np.uint8)

    encrypted_img = mod256.reshape(gray.shape)
    return encrypted_img

# -------------------------
# API ENDPOINT
# -------------------------
@app.route("/encrypt", methods=["POST"])
def encrypt_api():
    try:
        data = request.json["image"]
        img_bytes = base64.b64decode(data.split(",")[1])

        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        encrypted = rsa_encrypt_frame(frame)

        _, buffer = cv2.imencode(".png", encrypted)
        encoded = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "encrypted_image": "data:image/png;base64," + encoded
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# RUN SERVER (Render)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

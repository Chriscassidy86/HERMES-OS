"""Local Creative Studio for image and video generation."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "generated"
HOST = "127.0.0.1"
PORT = int(os.environ.get("CREATIVE_STUDIO_PORT", "8766"))
MAX_BODY = 32_000


class StudioError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def api_request(path: str, *, method: str = "GET", data: bytes | None = None,
                content_type: str = "application/json") -> tuple[bytes, dict[str, str]]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise StudioError("Add OPENAI_API_KEY to your environment, then restart Creative Studio.", 503)
    request = urllib.request.Request(
        "https://api.openai.com" + path, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = payload.get("error", {}).get("message", "The provider rejected the request.")
        except (ValueError, AttributeError):
            message = "The provider rejected the request."
        raise StudioError(message, exc.code if 400 <= exc.code < 500 else 502) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise StudioError("Could not reach the generation service. Check your connection and try again.", 502) from exc


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesCreativeStudio/1.0"

    def verify_local_request(self) -> bool:
        allowed = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        host = self.headers.get("Host", "").lower()
        origin = self.headers.get("Origin")
        if host not in allowed:
            self.send_json(403, {"error": "Creative Studio only accepts local browser requests."})
            return False
        if origin and origin.lower() not in {f"http://{item}" for item in allowed}:
            self.send_json(403, {"error": "Cross-site requests are not allowed."})
            return False
        return True

    def log_message(self, fmt: str, *args: object) -> None:
        print("Creative Studio: " + fmt % args)

    def send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: dict) -> None:
        self.send_bytes(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise StudioError("Invalid request size.") from exc
        if length <= 0 or length > MAX_BODY:
            raise StudioError("Request is empty or too large.", 413)
        try:
            result = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError) as exc:
            raise StudioError("Request must be valid JSON.") from exc
        if not isinstance(result, dict):
            raise StudioError("Request must be a JSON object.")
        return result

    def do_GET(self) -> None:
        if not self.verify_local_request():
            return
        if self.path == "/api/status":
            self.send_json(200, {"ready": bool(os.environ.get("OPENAI_API_KEY", "").strip())})
            return
        match = re.fullmatch(r"/api/video/([A-Za-z0-9_-]+)", self.path)
        if match:
            try:
                body, _ = api_request("/v1/videos/" + match.group(1))
                self.send_bytes(200, body, "application/json; charset=utf-8")
            except StudioError as exc:
                self.send_json(exc.status, {"error": str(exc)})
            return
        match = re.fullmatch(r"/api/video/([A-Za-z0-9_-]+)/download", self.path)
        if match:
            try:
                body, _ = api_request("/v1/videos/" + match.group(1) + "/content")
                OUTPUTS.mkdir(exist_ok=True)
                path = OUTPUTS / (match.group(1) + ".mp4")
                path.write_bytes(body)
                self.send_json(200, {"url": "/generated/" + path.name, "name": path.name})
            except StudioError as exc:
                self.send_json(exc.status, {"error": str(exc)})
            return
        if self.path.startswith("/generated/"):
            name = self.path.removeprefix("/generated/")
            if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|mp4)", name):
                self.send_json(404, {"error": "File not found."})
                return
            path = (OUTPUTS / name).resolve()
            if path.parent != OUTPUTS.resolve() or not path.is_file():
                self.send_json(404, {"error": "File not found."})
                return
            self.send_bytes(200, path.read_bytes(), "video/mp4" if path.suffix == ".mp4" else "image/png")
            return
        if self.path not in ("/", "/index.html"):
            self.send_json(404, {"error": "Not found."})
            return
        self.send_bytes(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if not self.verify_local_request():
            return
        try:
            payload = self.read_json()
            prompt = payload.get("prompt", "")
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
                raise StudioError("Enter a prompt between 1 and 4,000 characters.")
            if self.path == "/api/image":
                self.generate_image(prompt.strip(), payload)
            elif self.path == "/api/video":
                self.generate_video(prompt.strip(), payload)
            else:
                self.send_json(404, {"error": "Not found."})
        except StudioError as exc:
            self.send_json(exc.status, {"error": str(exc)})

    def generate_image(self, prompt: str, payload: dict) -> None:
        size = payload.get("size", "1024x1024")
        quality = payload.get("quality", "medium")
        if size not in ("1024x1024", "1536x1024", "1024x1536"):
            raise StudioError("Choose a supported image size.")
        if quality not in ("low", "medium", "high"):
            raise StudioError("Choose a supported image quality.")
        request = json.dumps({"model": "gpt-image-2.5-sunburst", "prompt": prompt,
                              "size": size, "quality": quality, "output_format": "png"}).encode("utf-8")
        body, _ = api_request("/v1/images/generations", method="POST", data=request)
        try:
            image = base64.b64decode(json.loads(body)["data"][0]["b64_json"], validate=True)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise StudioError("The image service returned an unexpected response.", 502) from exc
        OUTPUTS.mkdir(exist_ok=True)
        name = uuid4().hex + ".png"
        (OUTPUTS / name).write_bytes(image)
        self.send_json(200, {"url": "/generated/" + name, "name": name})

    def generate_video(self, prompt: str, payload: dict) -> None:
        seconds = str(payload.get("seconds", "4"))
        size = payload.get("size", "1280x720")
        if seconds not in ("4", "8", "12"):
            raise StudioError("Choose a clip length of 4, 8, or 12 seconds.")
        if size not in ("1280x720", "720x1280"):
            raise StudioError("Choose landscape or portrait video.")
        boundary = "----HermesStudio" + uuid4().hex
        fields = {"model": "sora-2", "prompt": prompt, "seconds": seconds, "size": size}
        chunks = []
        for key, value in fields.items():
            chunks.extend([f"--{boundary}\r\n".encode(),
                           f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                           value.encode(), b"\r\n"])
        chunks.append(f"--{boundary}--\r\n".encode())
        body, _ = api_request("/v1/videos", method="POST", data=b"".join(chunks),
                              content_type="multipart/form-data; boundary=" + boundary)
        job = json.loads(body)
        self.send_json(202, {"id": job.get("id"), "status": job.get("status", "queued"),
                             "progress": job.get("progress", 0)})


def main() -> None:
    OUTPUTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Creative Studio is ready at http://{HOST}:{PORT}")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("Set OPENAI_API_KEY in your environment to enable generation.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCreative Studio stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Plaintext HTTP lab with synthetic Patient and Observation resources."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4


class LabServer(HTTPServer):
    def __init__(self, address):
        super().__init__(address, LabHandler)
        self.resources = {}
        for kind, filename in (("Patient", "patients.json"), ("Observation", "observations.json")):
            path = Path(__file__).parent / "examples" / filename
            self.resources[kind] = {item["id"]: item for item in json.loads(path.read_text())}


class LabHandler(BaseHTTPRequestHandler):
    timeout = 10
    server_version = "BPaZDLocal/1.0"

    def respond(self, status, body, location=None):
        payload = (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/fhir+json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if location:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(payload)

    def error(self, status, message):
        self.respond(status, {"resourceType": "OperationOutcome", "issue": [
            {"severity": "error", "code": "processing", "diagnostics": message}
        ]})

    def route(self):
        parts = urlsplit(self.path).path.strip("/").split("/")
        if len(parts) in (2, 3) and parts[0] == "fhir" and parts[1] in self.server.resources:
            return parts[1], parts[2] if len(parts) == 3 else None
        return None, None

    def do_GET(self):
        if urlsplit(self.path).path == "/":
            self.respond(200, {"message": "Local synthetic-data HTTP lab",
                               "endpoints": ["/fhir/Patient", "/fhir/Observation"]})
            return
        kind, resource_id = self.route()
        if kind is None:
            self.error(404, "Unknown endpoint")
            return
        resources = self.server.resources[kind]
        if resource_id is not None:
            if resource_id in resources:
                self.respond(200, resources[resource_id])
            else:
                self.error(404, "Resource not found")
        else:
            self.respond(200, {"resourceType": "Bundle", "type": "collection",
                               "total": len(resources),
                               "entry": [{"resource": item} for item in resources.values()]})

    def do_POST(self):
        kind, resource_id = self.route()
        if kind is None:
            self.error(404, "Unknown endpoint")
            return
        if resource_id is not None:
            self.send_response(405)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.headers.get("Transfer-Encoding"):
            self.error(400, "Chunked requests are unsupported; send Content-Length")
            return
        if self.headers.get_content_type() not in ("application/json", "application/fhir+json"):
            self.error(415, "Use application/json or application/fhir+json")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.error(400, "Invalid Content-Length")
            return
        if not 0 < length <= 1024 * 1024:
            self.error(413 if length > 1024 * 1024 else 400, "Body must be between 1 byte and 1 MiB")
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                self.error(400, "Incomplete request body")
                return
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            self.error(400, "Body must be valid UTF-8 JSON")
            return
        if not isinstance(body, dict) or body.get("resourceType") != kind or "id" in body:
            self.error(400, "Supply matching resourceType and omit id")
            return
        if kind == "Patient":
            names = body.get("name")
            if not isinstance(names, list) or not names or any(
                not isinstance(name, dict) or not isinstance(name.get("family"), str)
                or not name["family"].strip() for name in names
            ):
                self.error(400, "Patient requires name entries with non-empty family strings")
                return
        else:
            subject = body.get("subject")
            reference = subject.get("reference") if isinstance(subject, dict) else None
            if not isinstance(reference, str) or reference not in {
                "Patient/" + key for key in self.server.resources["Patient"]
            }:
                self.error(422, "Observation must reference an existing Patient")
                return
        body["id"] = str(uuid4())
        self.server.resources[kind][body["id"]] = body
        self.respond(201, body, "/fhir/" + kind + "/" + body["id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with LabServer(("127.0.0.1", args.port)) as server:
        print("Listening on http://127.0.0.1:{} (Ctrl+C to stop)".format(server.server_port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()

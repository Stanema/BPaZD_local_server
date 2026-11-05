# Local HTTP traffic lab

A small Python standard-library server inspired by `BPaZD_server`. No packages
need installing. Uses the original project's synthetic Patient and Observation
examples. Data lives in memory and resets on restart.

## Run

Run `main.py` in PyCharm, or from this directory:

```sh
.venv/bin/python main.py
```

Listens on `http://127.0.0.1:8080`. Choose another port with `--port 8081`.
Stop with Ctrl+C. This lab deliberately uses plaintext HTTP with no authentication;
use synthetic data only. The server binds to loopback.

## Capture in Wireshark

1. Select the loopback interface (`lo0` on macOS, `lo` on Linux, or the Npcap
   loopback adapter on Windows).
2. Set the **capture filter** to `tcp port 8080` and start capturing.
3. Send the example requests below from another terminal.
4. Stop capturing. Set the **display filter** to `tcp.port == 8080`, or `http`
   for HTTP packets. If HTTP is not recognized, use Analyze → Decode As → HTTP
   for TCP port 8080.
5. Right-click a packet → Follow → TCP Stream to read request headers,
   JSON bodies, response status codes, and responses. Save as `.pcapng` if needed.

The server uses HTTP/1.0 with a new connection per request, making the TCP
handshake and connection close easy to distinguish. Wireshark performs the
capture; the server logs requests to the terminal.

## Generate traffic

```sh
curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Patient
curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Patient/synthetic-001
curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Observation
curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Patient/missing

curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Patient \
  -H 'Content-Type: application/fhir+json' \
  -d '{"resourceType":"Patient","name":[{"family":"Example-Demo","given":["Jana"]}]}'

curl --noproxy '*' -i http://127.0.0.1:8080/fhir/Observation \
  -H 'Content-Type: application/json' \
  -d '{"resourceType":"Observation","status":"final","subject":{"reference":"Patient/synthetic-001"},"code":{"text":"Heart rate"},"valueQuantity":{"value":74,"unit":"beats/minute"}}'
```

GET supports collections and individual resources. POST to either collection
returns 201, an assigned UUID, and a Location header. GET that Location to read
the created resource. Unknown paths and missing resources return 404.

Validation is minimal: POST requires an object with matching resourceType and no
id; Patients require names with non-empty family strings; Observations require
a reference to an existing Patient. This is a teaching subset, not a conformant
FHIR server. JSON bodies are limited to 1 MiB. PUT, DELETE, persistence, TLS,
Swagger, and the original project's full validation are not implemented.

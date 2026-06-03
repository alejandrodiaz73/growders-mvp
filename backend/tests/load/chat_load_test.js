/**
 * Growders MVP — Load Test (k6)
 * ─────────────────────────────
 * Tests the /api/v1/chat endpoint under realistic load.
 *
 * Run:
 *   k6 run tests/load/chat_load_test.js
 *   k6 run --vus 50 --duration 60s tests/load/chat_load_test.js
 *
 * Install k6: https://grafana.com/docs/k6/latest/set-up/install-k6/
 * (macOS: brew install k6 | Windows: choco install k6 | Docker: grafana/k6)
 *
 * Thresholds (fail the test if exceeded):
 *   - 95th percentile response time < 2000ms
 *   - Error rate < 1%
 *   - /health endpoint < 200ms
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ── Custom metrics ────────────────────────────────────────────────
const errorRate   = new Rate("error_rate");
const chatLatency = new Trend("chat_latency_ms", true);

// ── Test config ───────────────────────────────────────────────────
export const options = {
  scenarios: {
    // Ramp up → sustain → ramp down
    chat_load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 10 },   // warm up
        { duration: "1m",  target: 20 },   // normal load
        { duration: "30s", target: 50 },   // peak
        { duration: "30s", target: 0 },    // ramp down
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"],     // 95th pct < 2s
    error_rate:        ["rate<0.01"],      // < 1% errors
    chat_latency_ms:   ["p(90)<1500"],     // 90th pct < 1.5s
  },
};

// ── Helpers ───────────────────────────────────────────────────────
const BASE_URL     = __ENV.BASE_URL || "http://localhost:8000";
const TENANT_ID    = __ENV.TENANT_ID || "00000000-0000-0000-0000-000000000001";

const MESSAGES = [
  "Hola, ¿en qué me pueden ayudar?",
  "¿Cuál es su horario de atención?",
  "Necesito 30 playeras con logo, ¿cuánto cuesta?",
  "¿Cuánto tardan en entregar?",
  "¿Cuál es su política de devoluciones?",
  "Mi pedido ORD-20260601-0001, ¿ya está listo?",
];

function randomMessage() {
  return MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
}

function randomSessionToken() {
  return "load-test-" + Math.random().toString(36).substring(2, 12);
}

// ── Scenarios ─────────────────────────────────────────────────────
export default function () {
  // 1. Health check (lightweight)
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    "health: status 200": (r) => r.status === 200,
    "health: < 200ms":    (r) => r.timings.duration < 200,
  });

  sleep(0.5);

  // 2. Chat request
  const payload = JSON.stringify({
    message:       randomMessage(),
    session_token: randomSessionToken(),
    history:       [],
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-ID":  TENANT_ID,
    },
    timeout: "10s",
  };

  const start   = Date.now();
  const chatRes = http.post(`${BASE_URL}/api/v1/chat`, payload, params);
  const elapsed = Date.now() - start;

  chatLatency.add(elapsed);

  const ok = check(chatRes, {
    "chat: status 200":    (r) => r.status === 200,
    "chat: has response":  (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.response === "string" && body.response.length > 0;
      } catch {
        return false;
      }
    },
    "chat: no server error": (r) => r.status < 500,
  });

  errorRate.add(!ok);

  sleep(Math.random() * 2 + 1); // 1-3s between requests (realistic user pacing)
}

// ── Teardown summary ──────────────────────────────────────────────
export function handleSummary(data) {
  const summary = {
    timestamp:           new Date().toISOString(),
    total_requests:      data.metrics.http_reqs?.values?.count,
    error_rate_pct:      (data.metrics.error_rate?.values?.rate * 100).toFixed(2),
    p95_duration_ms:     data.metrics.http_req_duration?.values?.["p(95)"]?.toFixed(0),
    chat_p90_ms:         data.metrics.chat_latency_ms?.values?.["p(90)"]?.toFixed(0),
  };

  console.log("\n── Load Test Summary ────────────────────────────");
  console.log(JSON.stringify(summary, null, 2));

  return {
    "tests/load/results/last_run.json": JSON.stringify(summary, null, 2),
    stdout: JSON.stringify(summary, null, 2),
  };
}

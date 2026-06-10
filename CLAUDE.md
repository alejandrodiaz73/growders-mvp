# CLAUDE.md — Growders MVP

> Fuente de verdad para Claude Code en este repositorio.
> Si algo en el chat contradice este archivo, preguntar al usuario cuál prevalece.

---

## Proyecto

**Growders** — AIaaS: agente conversacional 24/7 para PyMEs mexicanas.
El agente responde basado EXCLUSIVAMENTE en la información del negocio (grounding estricto).
Si no sabe, escala al humano. Nunca inventa.

**Responsable:** Alex (CEO/CTO). Claude actúa como socio técnico.
**Fase actual:** Sprint 1 cerrado. Sprint 2 en curso.
**Repos activos:**
- MVP (este repo): Railway.app — `https://growders-mvp-production.up.railway.app`
- Frontend: Railway.app — `https://growders-demo-production.up.railway.app`
- POC (congelado): Render.com — `https://growders-poc.onrender.com`

---

## Arquitectura

```
Cliente (Web Simulator / WhatsApp Sprint 5)
  ↓
FastAPI — Webhook / REST
  ↓
Orquestación directa (Sprint 1) → LangGraph (Sprint 9)
  ↓
Router de intenciones
  ├── Información → RAG → Knowledge Base (pgvector)
  ├── Agendar    → Google Calendar (Sprint 4)
  ├── Orden      → Módulo de órdenes (Sprint 6)
  ├── Queja      → Gestor de casos (Sprint 3)
  └── Humano     → Handoff humano (Sprint 3)
  ↓
LLM con contexto grounded → Grounding Layer (valida antes de entrar al LLM)
  ↓
¿Validada? → Sí → Respuesta | No → Crear caso → Handoff humano

Datos:
  PostgreSQL (Railway) — BD principal + RLS por tenant
  SQLite (local dev)   — misma codebase, sin instalación
  In-memory cache      — Tier 0 actual (swap a Redis por REDIS_URL)
```

**Principio clave:** El LLM llama a las herramientas, no al revés.
El Grounding Layer valida el contexto ANTES de que entre al LLM.

---

## Stack técnico

| Capa | Tecnología | Tier actual |
|---|---|---|
| Framework | Python 3.13 + FastAPI | 0 |
| Orquestación IA | Directa → LangGraph (Sprint 9) | 0 |
| LLM | Mock → Groq → OpenAI (por `LLM_PROVIDER`) | 0 |
| Base de datos | PostgreSQL en Railway / SQLite en dev | 0 |
| Cache | `MemoryCache` → Redis (por `REDIS_URL`) | 0 |
| Cola async | BackgroundTasks → Celery | 0 |
| Deploy | Railway.app (auto-deploy desde `main`) | 0 |
| Frontend | HTML5 + CSS + JS vanilla (ES modules) | 0 |

**Contratos de abstracción:** `LLMProvider`, `CacheProvider`, `MessagingChannel`.
Cambiar de Tier 0 a Tier 1 = cambiar una variable de entorno, no reescribir código.

---

## Estructura del repositorio

```
growders-mvp/
├── backend/
│   ├── app/
│   │   ├── api/          — chat.py, health.py
│   │   ├── core/         — config.py, security.py, tenant.py, logging.py
│   │   ├── db/           — session.py (async SQLAlchemy + RLS)
│   │   ├── models/       — base.py, tenant.py, conversation.py
│   │   ├── services/     — cache.py, llm.py
│   │   ├── agents/       — vacío (LangGraph entra Sprint 9)
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/test_chat.py
│   │   └── load/chat_load_test.js (k6)
│   ├── requirements.txt
│   └── railway.toml      — Root Directory: /backend
├── frontend/
│   ├── src/
│   │   ├── index.html
│   │   └── assets/css/ + assets/js/
│   ├── package.json
│   └── railway.toml      — Root Directory: /frontend
├── infra/docker/docker-compose.yml
└── CLAUDE.md             — este archivo
```

---

## Variables de entorno

### Producción (Railway — backend)
```
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=[hex 64 chars]
LLM_PROVIDER=mock
ALLOWED_ORIGINS=https://growders-demo-production.up.railway.app
ALLOWED_HOSTS=[dominio del backend Railway]
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### Desarrollo local (.env — nunca commitear)
```
APP_ENV=development
APP_SECRET_KEY=[hex]
APP_DEBUG=true
LLM_PROVIDER=mock
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
# DATABASE_URL vacío → SQLite en ./data/growders.db
```

---

## Seguridad implementada

- CORS configurable por `ALLOWED_ORIGINS`
- CSP estricto con `connect-src` incluyendo dominio del backend
- Security headers: X-Frame-Options, HSTS (solo prod), Referrer-Policy, Permissions-Policy
- TrustedHostMiddleware activo en producción
- Rate limiting: 60 req/min global, 20 req/min en `/chat` (slowapi)
- Multi-tenant: `TenantMiddleware` resuelve tenant desde header `X-Tenant-ID`
- RLS: `SET LOCAL app.current_tenant_id` antes de cada query en PostgreSQL
- Input: max 500 chars, escape HTML en frontend
- Demo tenant UUID: `00000000-0000-0000-0000-000000000001`

---

## Reglas de operación

1. Identificar puntos débiles antes de validar cualquier decisión.
2. No abstraer antes de tener un flujo funcionando en producción con cliente real.
3. **No integrar Doctoralia** bajo ningún argumento ni en ninguna fase.
4. Resistir scope creep. Cada integración extra antes de validar el piloto duplica tiempo.
5. Confirmar explícitamente en el chat antes de cualquier acción irreversible en producción.
6. Nunca hardcodear URLs — usar `window.GROWDERS_API_URL` en JS y variables de entorno en Python.
7. En middleware, siempre `return JSONResponse(...)`, nunca `raise HTTPException(...)`.
8. OPTIONS preflight nunca lleva headers de negocio — hacer bypass en todo middleware de autenticación/tenant.
9. Dos servicios Railway separados: backend (`/backend`) y frontend (`/frontend`) — nunca mezclarlos.
10. Railway no redeploya automáticamente al cambiar variables de entorno — requiere redeploy manual.

---

## Lecciones técnicas aprendidas

| Lección | Contexto |
|---|---|
| `BaseHTTPMiddleware` no captura `HTTPException` | Usar `return JSONResponse(...)` en middleware |
| Railway Root Directory es crítico | Un Root Directory incorrecto rompe el deploy silenciosamente |
| OPTIONS preflight no lleva `X-Tenant-ID` | `TenantMiddleware` debe hacer bypass de OPTIONS |
| CSP `connect-src 'self'` bloquea fetch cross-origin | Agregar dominio del backend explícitamente |
| `serve` necesita apuntar a donde está `index.html` | Estructura de carpetas debe coincidir con `startCommand` |
| Railway no redeploya al cambiar env vars | Requiere redeploy manual desde el dashboard |

---

## Pendientes Sprint 2 (en curso)

| Tarea | Descripción | Prioridad |
|---|---|---|
| Alembic | Configurar migraciones. Tablas no creadas en PostgreSQL (`init_db` solo funciona con SQLite) | ALTA |
| Seed tenant demo | El UUID `00000000-0000-0000-0000-000000000001` no tiene registro real en la tabla `tenants` | ALTA |
| Knowledge Base CRUD | Base Operativa con pgvector para RAG | ALTA |
| LLM real | Conectar Groq o OpenAI (`LLM_PROVIDER=groq` o `openai`) | ALTA |
| ALLOWED_HOSTS | Verificar que incluye el dominio correcto del backend en Railway | MEDIA |

---

## Comandos frecuentes

```powershell
# Backend local
cd C:\Proyectos\growders\MVP\Claude\growders-mvp\backend
.\venv\Scripts\Activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Tests
pytest tests/unit -v
pytest tests/unit -v --cov=app --cov-report=html

# Deploy (Railway auto-detecta el push)
git add .
git commit -m "descripción"
git push origin main

# Verificar producción
curl https://growders-mvp-production.up.railway.app/health
```

---

## Roadmap de sprints

| Sprint | Contenido | Estado |
|---|---|---|
| Scaffold | Config, security, multi-tenant, cache, LLM, DB, modelos base | ✅ Completo |
| Sprint 1 | Fix 500→400, deploy frontend, CORS, ALLOWED_ORIGINS | ✅ Completo |
| Sprint 2 | Knowledge Base + pgvector, Alembic, seed tenant, LLM real | ⏳ En curso |
| Sprint 3 | Cases module — creación, asignación, cierre, handoff humano | Pendiente |
| Sprint 4 | Google Calendar integration | Pendiente |
| Sprint 5 | WhatsApp webhook (360Dialog) | Pendiente |
| Sprint 6 | Orders/tickets module | Pendiente |
| Sprint 7 | Panel de administración | Pendiente |
| Sprint 8 | Reportes diarios por email | Pendiente |
| Sprint 9 | LangGraph — reemplaza orquestación directa | Pendiente |
| Sprint 10 | Production hardening, load tests | Pendiente |

---

## Decisiones de arquitectura pendientes

| Decisión | Detalle | Sprint planificado |
|---|---|---|
| Autenticación panel admin | Clerk.js — se implementa después de que Sprint 3 (onboarding sin auth) esté estable | Sprint 4 |

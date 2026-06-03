# Growders MVP — Asistente Comercial WhatsApp

> AI-as-a-Service para PyMEs mexicanas. Atención 24/7 con grounding estricto.

---

## Estructura del proyecto

```
growders-mvp/
├── backend/               ← FastAPI + Python 3.13
│   ├── app/
│   │   ├── api/           ← Routers (health, chat, …)
│   │   ├── core/          ← Config, security, tenant, logging
│   │   ├── db/            ← Session, RLS
│   │   ├── models/        ← SQLAlchemy models
│   │   ├── services/      ← LLM, cache, email, calendar
│   │   └── agents/        ← Orquestación de conversación
│   ├── tests/
│   │   ├── unit/          ← pytest (sin dependencias externas)
│   │   ├── integration/   ← pytest con DB real
│   │   └── load/          ← k6 scripts
│   ├── .env.example
│   ├── requirements.txt
│   └── railway.toml
├── frontend/
│   └── src/
│       ├── pages/         ← index.html (simulador)
│       └── assets/
│           ├── css/       ← main.css
│           └── js/        ← app.js
├── infra/
│   └── docker/
│       └── docker-compose.yml
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Setup local (Tier 0 — sin Docker, sin Redis)

### Requisitos previos
- Python 3.13
- Node.js 22 (solo para servir el frontend en dev)
- Git

### 1. Descomprimir y abrir en VS Code

```powershell
# Descomprime el zip en:
C:\Proyectos\growders\MVP\Claude

# Abre VS Code
code C:\Proyectos\growders\MVP\Claude\growders-mvp
```

### 2. Backend

```powershell
cd backend

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
Copy-Item .env.example .env
# Editar .env: solo APP_SECRET_KEY es obligatorio en Tier 0
# Cambia: APP_SECRET_KEY=una-cadena-aleatoria-de-al-menos-32-caracteres

# Arrancar
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**El backend estará en:** http://127.0.0.1:8000  
**Docs API:** http://127.0.0.1:8000/docs

### 3. Frontend

```powershell
# En otra terminal (PowerShell)
cd frontend

# Instalar servidor estático simple
npm install -g serve

# Servir el frontend
serve src/pages -l 5173
```

**El simulador estará en:** http://localhost:5173

> **Alternativa sin npm:** Instala la extensión "Live Server" en VS Code,
> click derecho en `frontend/src/pages/index.html` → "Open with Live Server".

---

## Setup con Docker (Tier 1 — PostgreSQL + Redis local)

```powershell
# Desde la raíz del proyecto
cd infra\docker
docker compose up -d

# Verificar que los servicios estén corriendo
docker compose ps
```

Luego en el backend `.env` cambia:
```
DATABASE_URL=postgresql+asyncpg://growders:growders_dev@localhost:5432/growders_mvp
REDIS_URL=redis://localhost:6379/0
```

---

## Tests

```powershell
cd backend
.\venv\Scripts\Activate

# Unit tests (sin API keys, sin DB)
pytest tests/unit -v

# Con cobertura
pytest tests/unit -v --cov=app --cov-report=html
```

## Load testing (k6)

```powershell
# Con el backend corriendo en localhost:8000
k6 run backend/tests/load/chat_load_test.js

# Con más carga
k6 run --vus 50 --duration 60s backend/tests/load/chat_load_test.js
```

---

## Crear repositorio en GitHub

```powershell
# Desde la raíz del proyecto (growders-mvp/)
git init
git add .
git commit -m "feat: Growders MVP scaffold v0.1.0"
git branch -M main

# Crear repo vacío en github.com (NO inicialices con README)
git remote add origin https://github.com/TU_USUARIO/growders-mvp.git
git push -u origin main
```

---

## Deploy en Railway

1. Ve a https://railway.app → New Project → Deploy from GitHub Repo
2. Selecciona el repo `growders-mvp`
3. Railway detecta el `backend/railway.toml` automáticamente
4. Agrega variables de entorno en el panel de Railway:
   - `APP_SECRET_KEY` (genera una con `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `APP_ENV=production`
   - `DATABASE_URL` (Railway te la da cuando agregas PostgreSQL como servicio)
   - `LLM_PROVIDER=mock` (cambia a `groq` cuando tengas la API key)
   - `GROQ_API_KEY=...`
   - `ALLOWED_ORIGINS=https://tu-frontend.railway.app`
5. Para el frontend: New Service → Static Site → apunta a `frontend/src/pages`

---

## Variables de entorno mínimas para funcionar

| Variable | Valor mínimo | Descripción |
|---|---|---|
| `APP_SECRET_KEY` | 32+ caracteres random | Obligatorio |
| `APP_ENV` | `development` | `production` en Railway |
| `LLM_PROVIDER` | `mock` | Cambia a `groq` con API key |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | URL del frontend |

---

## Roadmap de módulos (orden de construcción)

- [x] Scaffold: config, security, multi-tenant, cache, LLM, DB session
- [x] Chat endpoint + web simulator + unit tests + load test
- [ ] Sprint 2: Knowledge Base (Base Operativa) — CRUD + pgvector
- [ ] Sprint 3: Cases module — creación, asignación, cierre
- [ ] Sprint 4: Google Calendar integration
- [ ] Sprint 5: WhatsApp webhook (360Dialog)
- [ ] Sprint 6: Orders/tickets module
- [ ] Sprint 7: Admin panel (HTML vanilla)
- [ ] Sprint 8: Daily reports (email)
- [ ] Sprint 9: Alembic migrations + production hardening

---

## Cuándo usar Claude Code

Claude Code es útil cuando:
- Tienes el scaffold corriendo y necesitas iterar sobre módulos específicos
- Quieres agregar un nuevo endpoint sin escribir el boilerplate desde cero
- Necesitas refactorizar sin romper los tests existentes

**Instrucciones de instalación de Claude Code:**
```powershell
npm install -g @anthropic-ai/claude-code
cd C:\Proyectos\growders\MVP\Claude\growders-mvp
claude
```
Claude Code lee el código del repo y puede modificarlo directamente.
Úsalo a partir del Sprint 2.

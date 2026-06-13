# Arquitectura Backend — Growders MVP

> Python + Clean Architecture + LangChain (Multi-Agent) + AWS

---

## 1. Backend con AWS Lambda (Serverless)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                                  │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐                             │
│  │  Route 53    │     │ ACM (SSL)    │                             │
│  │              │     │ *.growders.mx│                             │
│  │ api.growders ├────►│              │                             │
│  └──────┬───────┘     └──────┬───────┘                             │
│         │                    │                                     │
│  ┌──────▼────────────────────▼──────┐                              │
│  │         CloudFront               │                              │
│  │   api.growders.mx → API Gateway  │                              │
│  └──────────────┬───────────────────┘                              │
│                 │                                                   │
│  ┌──────────────▼───────────────────────────────────────────────┐   │
│  │              API Gateway (REST + WebSocket)                  │   │
│  │                                                              │   │
│  │  REST Endpoints            WebSocket                         │   │
│  │  ┌─────────────────┐      ┌─────────────────┐               │   │
│  │  │ POST /auth/*    │      │ $connect        │               │   │
│  │  │ GET  /users/*   │      │ $disconnect     │               │   │
│  │  │ POST /chat      │      │ $default (msg)  │               │   │
│  │  │ GET  /admin/*   │      │                 │               │   │
│  │  │ CRUD /cases/*   │      │                 │               │   │
│  │  └────────┬────────┘      └────────┬────────┘               │   │
│  └───────────┼────────────────────────┼─────────────────────────┘   │
│              │                        │                             │
│  ┌───────────▼────────────────────────▼─────────────────────────┐   │
│  │                    Lambda Functions                           │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │  │  auth        │  │  chat        │  │  admin       │       │   │
│  │  │  handler.py  │  │  handler.py  │  │  handler.py  │       │   │
│  │  │              │  │              │  │              │       │   │
│  │  │ - login      │  │ - send_msg   │  │ - dashboard  │       │   │
│  │  │ - register   │  │ - get_history│  │ - cases CRUD │       │   │
│  │  │ - refresh    │  │ - ws_connect │  │ - knowledge  │       │   │
│  │  │ - profile    │  │ - ws_message │  │ - analytics  │       │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │   │
│  │         │                 │                  │               │   │
│  │         │     ┌───────────▼──────────┐       │               │   │
│  │         │     │  langchain_agent     │       │               │   │
│  │         │     │  handler.py          │       │               │   │
│  │         │     │                      │       │               │   │
│  │         │     │  - route_question    │       │               │   │
│  │         │     │  - invoke_agent      │       │               │   │
│  │         │     │  - stream_response   │       │               │   │
│  │         │     └──────────┬───────────┘       │               │   │
│  │         │                │                   │               │   │
│  └─────────┼────────────────┼───────────────────┼───────────────┘   │
│            │                │                   │                   │
│  ┌─────────▼────────────────▼───────────────────▼───────────────┐   │
│  │                    Shared Layer                               │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │  Cognito    │  │  Bedrock    │  │  Secrets Manager    │  │   │
│  │  │  User Pools │  │  (Claude)   │  │  (API Keys, DB creds│  │   │
│  │  │  (Auth)     │  │  LLM calls  │  │   Config)           │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │    SQS      │  │    SNS      │  │  CloudWatch         │  │   │
│  │  │  (Colas de  │  │  (Eventos   │  │  (Logs + Metrics    │  │   │
│  │  │   proceso)  │  │   push)     │  │   + Alarms)         │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                │   │
│  │                                                              │   │
│  │  ┌─────────────────────┐  ┌──────────────────────────────┐  │   │
│  │  │  RDS PostgreSQL     │  │  DynamoDB                    │  │   │
│  │  │  (Aurora Serverless) │  │                              │  │   │
│  │  │                     │  │  ┌────────────────────────┐  │  │   │
│  │  │  ┌───────────────┐  │  │  │ conversations          │  │  │   │
│  │  │  │ users         │  │  │  │  PK: tenant#user_id    │  │  │   │
│  │  │  │ tenants       │  │  │  │  SK: conv#timestamp    │  │  │   │
│  │  │  │ cases         │  │  │  ├────────────────────────┤  │  │   │
│  │  │  │ knowledge_base│  │  │  │ messages               │  │  │   │
│  │  │  │ agent_config  │  │  │  │  PK: conv_id           │  │  │   │
│  │  │  └───────────────┘  │  │  │  SK: msg#timestamp     │  │  │   │
│  │  │                     │  │  ├────────────────────────┤  │  │   │
│  │  │  Multi-AZ           │  │  │ sessions               │  │  │   │
│  │  │  Auto-scaling       │  │  │  PK: session_id        │  │  │   │
│  │  │                     │  │  │  TTL: 24h              │  │  │   │
│  │  └─────────────────────┘  │  └────────────────────────┘  │  │   │
│  │                           │                              │  │   │
│  │                           │  On-demand capacity          │  │   │
│  │                           │  Point-in-time recovery      │  │   │
│  │                           └──────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Características clave (Lambda):**

| Aspecto | Detalle |
|---|---|
| **Runtime** | Python 3.12 |
| **Packaging** | Lambda Layers (dependencias compartidas: LangChain, SQLAlchemy) |
| **Cold start** | Mitigado con Provisioned Concurrency en `chat` handler |
| **Timeout** | Auth/Admin: 30s — Chat/LangChain: 120s (streaming LLM) |
| **Concurrencia** | Reserved concurrency por función para aislar cargas |
| **VPC** | Lambdas dentro de private subnets para acceso a RDS |

---

## 2. Backend con Kubernetes (EKS)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                                  │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐                             │
│  │  Route 53    │     │ ACM (SSL)    │                             │
│  │              │     │ *.growders.mx│                             │
│  │ api.growders ├────►│              │                             │
│  └──────┬───────┘     └──────┬───────┘                             │
│         │                    │                                     │
│  ┌──────▼────────────────────▼──────┐                              │
│  │         CloudFront               │                              │
│  │   api.growders.mx → ALB          │                              │
│  └──────────────┬───────────────────┘                              │
│                 │                                                   │
│  ┌──────────────▼───────────────────────────────────────────────┐   │
│  │           VPC (10.0.0.0/16)                                  │   │
│  │                                                              │   │
│  │  Public Subnets (10.0.1.0/24, 10.0.3.0/24)                 │   │
│  │  ┌──────────────────────┐  ┌─────────────┐                  │   │
│  │  │  ALB (Application    │  │ NAT Gateway │                  │   │
│  │  │  Load Balancer)      │  │ (outbound)  │                  │   │
│  │  │                      │  │             │                  │   │
│  │  │  /api/* → backend    │  └─────────────┘                  │   │
│  │  │  /ws   → websocket   │                                   │   │
│  │  └──────────┬───────────┘                                   │   │
│  │             │                                                │   │
│  │  Private Subnets (10.0.2.0/24, 10.0.4.0/24)                │   │
│  │  ┌──────────▼───────────────────────────────────────────┐   │   │
│  │  │              EKS Cluster                             │   │   │
│  │  │                                                      │   │   │
│  │  │  Namespace: growders-prod                            │   │   │
│  │  │  ┌────────────────────────────────────────────────┐  │   │   │
│  │  │  │                                                │  │   │   │
│  │  │  │  ┌─────────────┐  ┌─────────────────────────┐ │  │   │   │
│  │  │  │  │ Ingress     │  │ Service Mesh (optional)  │ │  │   │   │
│  │  │  │  │ Controller  │  │ (Istio / App Mesh)       │ │  │   │   │
│  │  │  │  └──────┬──────┘  └─────────────────────────┘ │  │   │   │
│  │  │  │         │                                      │  │   │   │
│  │  │  │  ┌──────▼──────────────────────────────────┐   │  │   │   │
│  │  │  │  │          Services (ClusterIP)            │   │  │   │   │
│  │  │  │  │                                          │   │  │   │   │
│  │  │  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │  │   │   │
│  │  │  │  │  │auth-svc  │ │chat-svc  │ │admin-svc │ │   │  │   │   │
│  │  │  │  │  │Port:8001 │ │Port:8002 │ │Port:8003 │ │   │  │   │   │
│  │  │  │  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ │   │  │   │   │
│  │  │  │  └───────┼────────────┼─────────────┼───────┘   │  │   │   │
│  │  │  │          │            │             │           │  │   │   │
│  │  │  │  ┌───────▼────────────▼─────────────▼───────┐   │  │   │   │
│  │  │  │  │          Deployments (Pods)               │   │  │   │   │
│  │  │  │  │                                          │   │  │   │   │
│  │  │  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │  │   │   │
│  │  │  │  │  │auth-pod  │ │chat-pod  │ │admin-pod │ │   │  │   │   │
│  │  │  │  │  │FastAPI   │ │FastAPI   │ │FastAPI   │ │   │  │   │   │
│  │  │  │  │  │2 replicas│ │3 replicas│ │2 replicas│ │   │  │   │   │
│  │  │  │  │  └──────────┘ └──────────┘ └──────────┘ │   │  │   │   │
│  │  │  │  │                                          │   │  │   │   │
│  │  │  │  │  ┌─────────────────────────────────────┐ │   │  │   │   │
│  │  │  │  │  │  langchain-agent-pod                │ │   │  │   │   │
│  │  │  │  │  │  FastAPI + LangChain                │ │   │  │   │   │
│  │  │  │  │  │  3 replicas (GPU optional)          │ │   │  │   │   │
│  │  │  │  │  │  HPA: CPU 70% → max 10 replicas    │ │   │  │   │   │
│  │  │  │  │  └─────────────────────────────────────┘ │   │  │   │   │
│  │  │  │  └──────────────────────────────────────────┘   │  │   │   │
│  │  │  │                                                │  │   │   │
│  │  │  │  ┌──────────────────────────────────────────┐   │  │   │   │
│  │  │  │  │  Soporte                                 │   │  │   │   │
│  │  │  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │  │   │   │
│  │  │  │  │  │ConfigMap │ │Secrets   │ │HPA / VPA │ │   │  │   │   │
│  │  │  │  │  │(env vars)│ │(creds)   │ │(scaling) │ │   │  │   │   │
│  │  │  │  │  └──────────┘ └──────────┘ └──────────┘ │   │  │   │   │
│  │  │  │  └──────────────────────────────────────────┘   │  │   │   │
│  │  │  └────────────────────────────────────────────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐   │   │
│  │  │                  Data Layer (Private Subnets)          │   │   │
│  │  │                                                       │   │   │
│  │  │  ┌─────────────────┐  ┌─────────────┐  ┌───────────┐ │   │   │
│  │  │  │ RDS PostgreSQL  │  │ DynamoDB    │  │ElastiCache│ │   │   │
│  │  │  │ (Aurora)        │  │             │  │(Redis)    │ │   │   │
│  │  │  │                 │  │ conversations│  │           │ │   │   │
│  │  │  │ users           │  │ messages    │  │ sessions  │ │   │   │
│  │  │  │ tenants         │  │ sessions    │  │ cache     │ │   │   │
│  │  │  │ cases           │  │             │  │ rate-limit│ │   │   │
│  │  │  │ knowledge_base  │  │             │  │           │ │   │   │
│  │  │  │ agent_config    │  │             │  │           │ │   │   │
│  │  │  │                 │  │             │  │           │ │   │   │
│  │  │  │ Multi-AZ        │  │ On-demand   │  │ Cluster   │ │   │   │
│  │  │  └─────────────────┘  └─────────────┘  └───────────┘ │   │   │
│  │  └───────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Servicios Externos                                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │   │
│  │  │  Cognito    │  │  Bedrock     │  │  Secrets Manager    │ │   │
│  │  │  (Auth)     │  │  (Claude LLM)│  │  (Credentials)     │ │   │
│  │  └─────────────┘  └──────────────┘  └─────────────────────┘ │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │   │
│  │  │  ECR        │  │  CloudWatch  │  │  S3 (Knowledge     │ │   │
│  │  │  (Container │  │  (Logs +     │  │   Base docs)       │ │   │
│  │  │   Registry) │  │   Metrics)   │  │                    │ │   │
│  │  └─────────────┘  └──────────────┘  └─────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Características clave (EKS):**

| Aspecto | Detalle |
|---|---|
| **Runtime** | Python 3.12 + FastAPI (Uvicorn) |
| **Contenedores** | Docker → ECR → EKS |
| **Scaling** | HPA por CPU/memoria, VPA para right-sizing |
| **Networking** | ALB Ingress Controller, ClusterIP services |
| **Observabilidad** | CloudWatch Container Insights + Prometheus (opcional) |
| **Deploy** | Rolling update, blue/green con Argo Rollouts (opcional) |
| **Redis** | ElastiCache para cache de respuestas y rate limiting |

---

## 3. Arquitectura LangChain Multi-Agent

> Este diagrama es agnóstico de infraestructura. Aplica igual para Lambda o EKS.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LangChain Multi-Agent System                     │
│                                                                     │
│  Pregunta del usuario                                               │
│  "¿Cuántas unidades hay del producto X?"                            │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Router Agent (Orquestador)                  │    │
│  │                                                             │    │
│  │  1. Recibe pregunta + contexto de conversación              │    │
│  │  2. Clasifica intención (LLM call)                          │    │
│  │  3. Selecciona agente especializado                         │    │
│  │  4. Delega ejecución                                        │    │
│  │                                                             │    │
│  │  Clasificación:                                             │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │    │
│  │  │ "almacen"   │ │ "soporte"   │ │ "faq"       │           │    │
│  │  │ inventario  │ │ problema    │ │ pregunta    │           │    │
│  │  │ stock       │ │ ticket      │ │ general     │           │    │
│  │  │ producto    │ │ error       │ │ cómo        │           │    │
│  │  │ precio      │ │ ayuda       │ │ qué es      │           │    │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │    │
│  └─────────┼───────────────┼───────────────┼───────────────────┘    │
│            │               │               │                        │
│  ┌─────────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐                │
│  │  Agente       │ │  Agente     │ │  Agente     │                │
│  │  ALMACÉN      │ │  SOPORTE    │ │  FAQ        │                │
│  │               │ │             │ │             │                │
│  │ Responsable:  │ │ Responsable:│ │ Responsable:│                │
│  │ - Stock       │ │ - Crear     │ │ - Responder │                │
│  │ - Productos   │ │   tickets   │ │   preguntas │                │
│  │ - Precios     │ │ - Estado de │ │   frecuentes│                │
│  │ - Ubicación   │ │   casos     │ │ - Políticas │                │
│  │ - Disponible  │ │ - Escalar a │ │ - Horarios  │                │
│  │               │ │   humano    │ │ - Procesos  │                │
│  │ Tools:        │ │ - Historial │ │             │                │
│  │ ┌───────────┐ │ │             │ │ Tools:      │                │
│  │ │query_stock│ │ │ Tools:      │ │ ┌─────────┐ │                │
│  │ │get_product│ │ │ ┌─────────┐ │ │ │search   │ │                │
│  │ │check_price│ │ │ │create   │ │ │ │_knowledge│ │                │
│  │ └───────────┘ │ │ │_ticket  │ │ │ │_base    │ │                │
│  │               │ │ │get_case │ │ │ └─────────┘ │                │
│  └───────┬───────┘ │ │_status  │ │ │             │                │
│          │         │ │escalate │ │ └──────┬──────┘                │
│          │         │ └─────────┘ │        │                        │
│          │         └──────┬──────┘        │                        │
│          │                │               │                        │
│  ┌───────▼────────────────▼───────────────▼────────────────────┐   │
│  │                    Data Sources                              │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │   │
│  │  │ PostgreSQL  │  │ PostgreSQL   │  │ Vector Store        │ │   │
│  │  │ (Inventario)│  │ (Casos/      │  │ (Knowledge Base)    │ │   │
│  │  │             │  │  Tickets)    │  │                     │ │   │
│  │  │ products    │  │ cases        │  │ ┌─────────────────┐ │ │   │
│  │  │ inventory   │  │ case_history │  │ │ pgvector /      │ │ │   │
│  │  │ pricing     │  │ escalations  │  │ │ OpenSearch      │ │ │   │
│  │  └─────────────┘  └──────────────┘  │ │                 │ │ │   │
│  │                                     │ │ FAQ docs        │ │ │   │
│  │                                     │ │ Políticas       │ │ │   │
│  │                                     │ │ Manuales        │ │ │   │
│  │                                     │ └─────────────────┘ │ │   │
│  │                                     └─────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    LLM Provider                              │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │              AWS Bedrock                              │   │   │
│  │  │                                                      │   │   │
│  │  │  ┌────────────────┐  ┌─────────────────────────────┐ │   │   │
│  │  │  │ Claude         │  │ Titan Embeddings            │ │   │   │
│  │  │  │ (Razonamiento, │  │ (Vectorización de docs     │ │   │   │
│  │  │  │  clasificación,│  │  para Knowledge Base)      │ │   │   │
│  │  │  │  respuestas)   │  │                             │ │   │   │
│  │  │  └────────────────┘  └─────────────────────────────┘ │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Flujo detallado del Router Agent

```
Usuario: "No puedo iniciar sesión en mi cuenta"
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │  Router Agent                                        │
  │                                                      │
  │  Prompt de clasificación:                            │
  │  """                                                 │
  │  Clasifica la intención del usuario en una de:       │
  │  - almacen: inventario, stock, productos, precios    │
  │  - soporte: problemas, errores, tickets, ayuda       │
  │  - faq: preguntas generales, políticas, horarios     │
  │                                                      │
  │  Pregunta: "No puedo iniciar sesión en mi cuenta"    │
  │  Intención: soporte                                  │
  │  Confianza: 0.95                                     │
  │  """                                                 │
  └──────────────────┬───────────────────────────────────┘
                     │
                     ▼  intención = "soporte"
  ┌──────────────────────────────────────────────────────┐
  │  Agente SOPORTE                                      │
  │                                                      │
  │  1. Busca contexto en historial de conversación      │
  │  2. Consulta si existe ticket previo del usuario     │
  │     → SQL: SELECT * FROM cases WHERE user_id = ?     │
  │  3. Genera respuesta con contexto                    │
  │  4. Si no puede resolver → escalate_to_human()       │
  │                                                      │
  │  Respuesta:                                          │
  │  "Lamento el inconveniente. Voy a crear un ticket   │
  │   de soporte para investigar tu problema de acceso.  │
  │   Tu número de ticket es #SOP-1234. Un agente te    │
  │   contactará en breve."                              │
  └──────────────────┬───────────────────────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────────────────────┐
  │  Side Effects                                        │
  │                                                      │
  │  - INSERT INTO cases (ticket #SOP-1234)              │
  │  - Notificación al admin panel                       │
  │  - Evento: "admin:case_escalated"                    │
  │  - Log en CloudWatch                                 │
  └──────────────────────────────────────────────────────┘
```

### Diagrama RAG para el Agente FAQ

```
  Pregunta: "¿Cuál es la política de devoluciones?"
       │
       ▼
  ┌─────────────────────────┐
  │  1. Embedding           │
  │  Titan Embeddings       │
  │  pregunta → vector      │
  │  [0.12, -0.34, ...]     │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  2. Vector Search       │
  │  pgvector / OpenSearch  │
  │                         │
  │  Busca los 3 documentos │
  │  más similares:         │
  │  - politica_devol.md    │
  │  - terminos_cond.md     │
  │  - garantias.md         │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  3. Context Assembly    │
  │                         │
  │  Prompt:                │
  │  """                    │
  │  Contexto:              │
  │  {doc1} {doc2} {doc3}   │
  │                         │
  │  Pregunta del usuario:  │
  │  ¿Cuál es la política   │
  │  de devoluciones?       │
  │                         │
  │  Responde basándote     │
  │  SOLO en el contexto.   │
  │  """                    │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │  4. Claude (Bedrock)    │
  │                         │
  │  Genera respuesta       │
  │  fundamentada en docs   │
  │  del Knowledge Base     │
  └─────────────────────────┘
```

---

## 4. Clean Architecture (Python)

> Estructura del código Python que corre dentro de Lambda o EKS.

```
src/
├── domain/                          ← Capa de dominio (sin dependencias externas)
│   ├── entities/
│   │   ├── user.py                  ← User, Tenant
│   │   ├── conversation.py          ← Conversation, Message
│   │   ├── case.py                  ← SupportCase, CaseStatus
│   │   └── agent.py                 ← AgentConfig, AgentType
│   ├── repositories/                ← Interfaces (ABC)
│   │   ├── user_repository.py
│   │   ├── conversation_repository.py
│   │   ├── case_repository.py
│   │   └── knowledge_repository.py
│   ├── services/                    ← Domain services
│   │   └── agent_router.py          ← Lógica de selección de agente
│   └── exceptions.py
│
├── application/                     ← Casos de uso
│   ├── use_cases/
│   │   ├── auth/
│   │   │   ├── register_user.py
│   │   │   ├── authenticate_user.py
│   │   │   └── refresh_token.py
│   │   ├── chat/
│   │   │   ├── send_message.py      ← Orquesta: router → agente → respuesta
│   │   │   ├── get_conversation.py
│   │   │   └── stream_response.py
│   │   ├── admin/
│   │   │   ├── manage_cases.py
│   │   │   ├── manage_knowledge.py
│   │   │   └── get_analytics.py
│   │   └── agents/
│   │       ├── route_question.py    ← Usa domain/agent_router
│   │       ├── invoke_almacen.py
│   │       ├── invoke_soporte.py
│   │       └── invoke_faq.py
│   ├── dto/                         ← Data Transfer Objects
│   │   ├── chat_dto.py
│   │   ├── user_dto.py
│   │   └── case_dto.py
│   └── interfaces/                  ← Ports (ABC)
│       ├── llm_provider.py          ← Interface para LLM
│       └── vector_store.py          ← Interface para vector search
│
├── infrastructure/                  ← Implementaciones concretas
│   ├── persistence/
│   │   ├── postgres/
│   │   │   ├── user_repo_impl.py
│   │   │   ├── case_repo_impl.py
│   │   │   ├── knowledge_repo_impl.py
│   │   │   └── models.py           ← SQLAlchemy models
│   │   └── dynamodb/
│   │       ├── conversation_repo_impl.py
│   │       └── session_repo_impl.py
│   ├── llm/
│   │   ├── bedrock_provider.py      ← Implementa llm_provider.py
│   │   └── langchain/
│   │       ├── agent_factory.py     ← Crea agentes LangChain
│   │       ├── almacen_agent.py     ← Tools + prompt del agente almacén
│   │       ├── soporte_agent.py     ← Tools + prompt del agente soporte
│   │       ├── faq_agent.py         ← RAG chain para FAQ
│   │       ├── router_chain.py      ← Chain de clasificación
│   │       └── tools/
│   │           ├── stock_tools.py   ← query_stock, get_product, check_price
│   │           ├── case_tools.py    ← create_ticket, get_case_status, escalate
│   │           └── search_tools.py  ← search_knowledge_base
│   ├── vector_store/
│   │   ├── pgvector_impl.py         ← pgvector implementation
│   │   └── opensearch_impl.py       ← OpenSearch implementation
│   ├── auth/
│   │   └── cognito_service.py
│   └── config/
│       ├── settings.py              ← Pydantic Settings
│       └── aws.py                   ← AWS clients (boto3)
│
├── interfaces/                      ← Adapters (entrada)
│   ├── lambda_handlers/             ← Para despliegue en Lambda
│   │   ├── auth_handler.py
│   │   ├── chat_handler.py
│   │   ├── admin_handler.py
│   │   └── websocket_handler.py
│   └── api/                         ← Para despliegue en EKS
│       ├── main.py                  ← FastAPI app
│       ├── routers/
│       │   ├── auth_router.py
│       │   ├── chat_router.py
│       │   ├── admin_router.py
│       │   └── websocket_router.py
│       ├── middleware/
│       │   ├── auth_middleware.py
│       │   ├── cors_middleware.py
│       │   └── rate_limit.py
│       └── dependencies.py          ← Dependency Injection (FastAPI)
│
├── shared/
│   ├── logger.py
│   ├── exceptions.py
│   └── event_bus.py                 ← Eventos internos del backend
│
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── test_agents.py
│   │   ├── test_repositories.py
│   │   └── test_api.py
│   └── conftest.py
│
├── Dockerfile                       ← Para EKS
├── serverless.yml                   ← Para Lambda (SAM/Serverless Framework)
├── pyproject.toml
└── requirements.txt
```

**Principio clave:** La capa `interfaces/` es la única que cambia entre Lambda y EKS. Todo lo demás (`domain/`, `application/`, `infrastructure/`) se comparte.

```
                Lambda                          EKS
                  │                               │
    interfaces/lambda_handlers/      interfaces/api/ (FastAPI)
                  │                               │
                  └───────────┬───────────────────┘
                              │
                    application/use_cases/
                              │
                      domain/entities/
                              │
                  infrastructure/persistence/
                  infrastructure/llm/langchain/
```

---

## 5. Comparativa Lambda vs EKS

| Criterio | Lambda (Serverless) | EKS (Kubernetes) |
|---|---|---|
| **Costo inicial** | Bajo (pay-per-request) | Alto (nodos EC2 24/7) |
| **Costo a escala** | Crece linealmente | Más eficiente con volumen |
| **Cold start** | 1-3s (Python + LangChain) | Sin cold start |
| **Timeout máximo** | 15 min | Sin límite |
| **Streaming LLM** | Limitado (response streaming) | Nativo (SSE/WebSocket) |
| **Scaling** | Automático (0 a miles) | HPA (configurar métricas) |
| **Complejidad ops** | Baja | Alta (kubectl, Helm, etc.) |
| **Debugging** | CloudWatch Logs | kubectl logs + dashboards |
| **WebSocket** | API Gateway WS (stateless) | Nativo (stateful) |
| **GPU (ML local)** | No disponible | Nodos GPU opcionales |
| **Recomendado para** | MVP, tráfico variable | Producción alta carga |

**Recomendación:** Iniciar con **Lambda** para el MVP (menor costo y complejidad operacional). Migrar a **EKS** cuando el volumen de chat justifique el costo fijo de los nodos, o si se necesita streaming nativo de LLM con baja latencia.

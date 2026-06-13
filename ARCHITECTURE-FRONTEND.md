# Arquitectura Frontend — Growders MVP

> React + Redux (Event-Driven) + AWS Amplify + Route 53 + VPC

---

## 1. Arquitectura de Infraestructura AWS

```
                         ┌──────────────┐
                         │   Route 53   │
                         │  DNS Routing │
                         └──────┬───────┘
                                │
                    ┌───────────▼───────────┐
                    │   CloudFront (CDN)    │
                    │  SSL/TLS Termination  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    AWS Amplify        │
                    │  Hosting + CI/CD     │
                    │  (React Build)       │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
    ┌─────────▼──────┐ ┌───────▼───────┐ ┌───────▼───────┐
    │   Cognito      │ │ API Gateway   │ │  S3 Bucket    │
    │  User Pools    │ │  REST/WS      │ │  Static Assets│
    │  (Auth)        │ │  (API Proxy)  │ │  (React App)  │
    └────────────────┘ └───────┬───────┘ └───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │       VPC           │
                    │  ┌───────────────┐  │
                    │  │ Backend APIs  │  │
                    │  │ (Private      │  │
                    │  │  Subnets)     │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

**Componentes clave:**

| Servicio | Responsabilidad |
|---|---|
| **Route 53** | DNS routing para `app.growders.mx` y `api.growders.mx` |
| **CloudFront** | CDN con terminación SSL/TLS, caching de assets estáticos |
| **Amplify** | Hosting del build de React, CI/CD pipeline integrado |
| **Cognito** | Autenticación y autorización (User Pools + Identity Pools) |
| **API Gateway** | Proxy REST y WebSocket hacia backend en VPC |
| **S3** | Almacenamiento del bundle React y assets estáticos |
| **VPC** | Red privada que contiene los servicios backend |

---

## 2. Arquitectura de la Aplicación React

```
src/
├── app/
│   ├── store.ts                 ← Redux Store (configureStore)
│   ├── rootReducer.ts           ← Combina slices
│   ├── eventBus.ts              ← Event Bus centralizado
│   ├── middleware/
│   │   ├── eventMiddleware.ts   ← Middleware Redux → Event Bus
│   │   ├── apiMiddleware.ts     ← Intercepta acciones async
│   │   └── loggerMiddleware.ts  ← Logging de eventos
│   └── hooks/
│       ├── useAppDispatch.ts
│       ├── useAppSelector.ts
│       └── useEvent.ts          ← Hook para suscribirse a eventos
│
├── features/
│   ├── auth/                    ← Amplify Cognito
│   │   ├── slices/authSlice.ts
│   │   ├── events/authEvents.ts
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignUpForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── services/authService.ts
│   │   └── types.ts
│   │
│   ├── chat/                    ← Chat para clientes
│   │   ├── slices/chatSlice.ts
│   │   ├── events/chatEvents.ts
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── services/chatService.ts  ← WebSocket + REST
│   │   └── types.ts
│   │
│   ├── admin/                   ← Panel de administración
│   │   ├── slices/adminSlice.ts
│   │   ├── events/adminEvents.ts
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── KnowledgeBase/
│   │   │   ├── CasesManager/
│   │   │   ├── TenantConfig/
│   │   │   └── Analytics/
│   │   ├── services/adminService.ts
│   │   └── types.ts
│   │
│   └── notifications/           ← Sistema de notificaciones
│       ├── slices/notificationSlice.ts
│       ├── events/notificationEvents.ts
│       ├── components/
│       │   ├── NotificationCenter.tsx
│       │   └── Toast.tsx
│       └── types.ts
│
├── shared/
│   ├── components/              ← UI Kit reutilizable
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Layout.tsx
│   ├── services/
│   │   ├── apiClient.ts         ← Axios/Fetch con interceptors
│   │   └── websocket.ts        ← WebSocket manager
│   ├── utils/
│   └── types/
│
├── routes/
│   ├── AppRouter.tsx            ← React Router v6
│   ├── publicRoutes.tsx
│   └── protectedRoutes.tsx
│
└── index.tsx
```

**Principios de la estructura:**

- **Feature-based** — cada feature (`auth`, `chat`, `admin`, `notifications`) es autocontenida con su slice, eventos, componentes y servicios.
- **Event-Driven** — cada feature declara sus eventos en `events/` y los emite via el middleware de Redux.
- **Shared** — componentes de UI y servicios reutilizables viven en `shared/`, evitando acoplamiento entre features.

---

## 3. Arquitectura Event-Driven con Redux

```
┌──────────────────────────────────────────────────────────┐
│                    React Components                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ChatWindow│  │Dashboard │  │CasesMgr  │  ...           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │dispatch      │dispatch     │dispatch              │
├───────▼──────────────▼─────────────▼─────────────────────┤
│                   Redux Store                             │
│  ┌─────────────────────────────────────────────┐         │
│  │              Middleware Pipeline              │         │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │         │
│  │  │  Logger  │→│  Event   │→│  RTK Query   │ │         │
│  │  │Middleware│ │Middleware│ │  (API calls)  │ │         │
│  │  └──────────┘ └────┬─────┘ └──────────────┘ │         │
│  └─────────────────────┼───────────────────────┘         │
│                        │                                  │
│  ┌─────────────────────▼───────────────────────┐         │
│  │              Event Bus                       │         │
│  │  ┌────────────────────────────────────────┐  │         │
│  │  │  chat:message_sent                     │  │         │
│  │  │  chat:message_received                 │  │         │
│  │  │  auth:login_success                    │  │         │
│  │  │  auth:session_expired                  │  │         │
│  │  │  admin:case_escalated                  │  │         │
│  │  │  admin:knowledge_updated               │  │         │
│  │  │  notification:new                      │  │         │
│  │  │  websocket:connected                   │  │         │
│  │  │  websocket:disconnected                │  │         │
│  │  └────────────────────────────────────────┘  │         │
│  └──────────────────────────────────────────────┘         │
│                        │                                  │
│  ┌─────────────────────▼───────────────────────┐         │
│  │              Slices (Reducers)               │         │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐  │         │
│  │  │  auth  │ │  chat  │ │ admin  │ │notif │  │         │
│  │  └────────┘ └────────┘ └────────┘ └──────┘  │         │
│  └──────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

**Catálogo de eventos:**

| Namespace | Evento | Descripción |
|---|---|---|
| `chat` | `message_sent` | El usuario envió un mensaje |
| `chat` | `message_received` | Se recibió respuesta del backend |
| `chat` | `realtime_update` | Actualización en tiempo real via WebSocket |
| `auth` | `login_success` | Login exitoso via Cognito |
| `auth` | `session_expired` | La sesión JWT expiró |
| `admin` | `case_escalated` | Un caso fue escalado a agente humano |
| `admin` | `knowledge_updated` | Se actualizó la base de conocimiento |
| `notification` | `new` | Nueva notificación generada |
| `websocket` | `connected` | Conexión WebSocket establecida |
| `websocket` | `disconnected` | Conexión WebSocket perdida |

---

## 4. Flujo de Datos Event-Driven

```
Usuario escribe mensaje
       │
       ▼
  ChatInput.tsx
  dispatch(sendMessage(text))
       │
       ▼
  eventMiddleware.ts
  Emite: "chat:message_sending"
       │
       ▼
  chatSlice.ts
  state.messages.push({...msg, status: 'sending'})
       │
       ▼
  RTK Query / chatService.ts
  POST /api/v1/chat  ──────────►  API Gateway ──► Backend
       │                                              │
       ▼                                              │
  Respuesta OK                                        │
  dispatch(messageReceived(response))                 │
       │                                              │
       ▼                                              │
  eventMiddleware.ts                                  │
  Emite: "chat:message_received"                      │
       │                                              │
       ├──► notificationSlice escucha el evento       │
       │    → muestra toast si tab no activa           │
       │                                              │
       ├──► analyticsMiddleware escucha               │
       │    → trackea evento                          │
       │                                              │
       ▼                                              │
  chatSlice.ts                                        │
  state.messages[-1].status = 'delivered'             │
                                                      │
  WebSocket (eventos push)  ◄─────────────────────────┘
       │
       ▼
  websocket.ts
  dispatch(wsMessageReceived(data))
       │
       ▼
  eventMiddleware.ts
  Emite: "chat:realtime_update"
```

**Puntos clave del flujo:**

1. **Optimistic update** — el mensaje se agrega al state con status `sending` antes de la respuesta del API.
2. **Side effects via Event Bus** — otros slices (notifications, analytics) reaccionan a eventos sin acoplamiento directo.
3. **Dual channel** — REST para enviar mensajes, WebSocket para recibir updates en tiempo real del backend.

---

## 5. Amplify + Route 53 + VPC (Networking)

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │  Route 53    │     │ ACM (SSL)    │                         │
│  │              │     │ *.growders.mx│                         │
│  │ app.growders ├────►│              │                         │
│  │ api.growders │     └──────┬───────┘                         │
│  └──────┬───────┘            │                                 │
│         │                    │                                 │
│  ┌──────▼────────────────────▼──────┐                          │
│  │         CloudFront               │                          │
│  │   app.growders.mx → Amplify      │                          │
│  │   api.growders.mx → API Gateway  │                          │
│  └──────┬───────────────────┬───────┘                          │
│         │                   │                                  │
│  ┌──────▼──────┐    ┌──────▼───────────────────────────────┐   │
│  │  Amplify    │    │           VPC (10.0.0.0/16)          │   │
│  │  Hosting    │    │                                      │   │
│  │ ┌────────┐  │    │  Public Subnets (10.0.1.0/24)       │   │
│  │ │React   │  │    │  ┌─────────────┐ ┌───────────────┐  │   │
│  │ │Build   │  │    │  │API Gateway  │ │ NAT Gateway   │  │   │
│  │ │(S3+CDN)│  │    │  │VPC Link     │ │               │  │   │
│  │ └────────┘  │    │  └──────┬──────┘ └───────┬───────┘  │   │
│  │             │    │         │                 │          │   │
│  │ ┌────────┐  │    │  Private Subnets (10.0.2.0/24)      │   │
│  │ │CI/CD   │  │    │  ┌──────▼──────┐ ┌──────▼───────┐  │   │
│  │ │Pipeline│  │    │  │  Backend    │ │  RDS/Aurora   │  │   │
│  │ │(Git →  │  │    │  │  (ECS/     │ │  PostgreSQL   │  │   │
│  │ │ Build →│  │    │  │   Lambda)  │ │              │  │   │
│  │ │ Deploy)│  │    │  └─────────────┘ └──────────────┘  │   │
│  │ └────────┘  │    │                                      │   │
│  │             │    │  ┌──────────────┐ ┌──────────────┐  │   │
│  │ ┌────────┐  │    │  │ ElastiCache │ │  Secrets     │  │   │
│  │ │Cognito │  │    │  │ (Redis)     │ │  Manager     │  │   │
│  │ │Auth    │  │    │  └──────────────┘ └──────────────┘  │   │
│  │ └────────┘  │    │                                      │   │
│  └─────────────┘    └──────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Dominios y ruteo:**

| Dominio | Destino | Propósito |
|---|---|---|
| `app.growders.mx` | Amplify Hosting (S3+CDN) | Aplicación React (Chat + Admin) |
| `api.growders.mx` | API Gateway → VPC | Backend APIs (REST + WebSocket) |

**Seguridad de red:**

- **Public Subnets** — solo API Gateway VPC Link y NAT Gateway expuestos.
- **Private Subnets** — Backend (ECS/Lambda), base de datos (RDS/Aurora PostgreSQL), cache (ElastiCache Redis) y Secrets Manager aislados sin acceso directo a internet.
- **NAT Gateway** — permite a servicios en subnets privadas hacer requests salientes (dependencias externas, APIs de terceros).

---

## 6. CI/CD Pipeline (Amplify)

```
GitHub (main)
    │
    ▼
Amplify Pipeline
    │
    ├── 1. Source ──────── Pull desde GitHub
    │
    ├── 2. Build
    │   ├── npm install
    │   ├── npm run lint
    │   ├── npm run test
    │   └── npm run build
    │
    ├── 3. Deploy
    │   ├── Preview (PR) ──► pr-123.d1abc.amplifyapp.com
    │   ├── Staging (develop) ──► staging.growders.mx
    │   └── Production (main) ──► app.growders.mx
    │
    └── 4. Post-Deploy
        ├── Invalidar cache CloudFront
        └── Notificar Slack/Discord
```

**Ambientes:**

| Branch | URL | Propósito |
|---|---|---|
| PR branches | `pr-{id}.d1abc.amplifyapp.com` | Preview para code review |
| `develop` | `staging.growders.mx` | Pruebas de integración y QA |
| `main` | `app.growders.mx` | Producción |

**`amplify.yml` (referencia):**

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run lint
        - npm run test -- --watchAll=false
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

---

## 7. Redux Slices — Estructura del Estado

### authSlice

```
authState = {
  user: {
    id: string
    email: string
    name: string
    tenantId: string
    role: 'client' | 'admin' | 'superadmin'
    avatar?: string
  } | null
  tokens: {
    accessToken: string
    refreshToken: string
    expiresAt: number              ← Unix timestamp
  } | null
  status: 'idle' | 'loading' | 'authenticated' | 'unauthenticated' | 'error'
  error: string | null
  mfaRequired: boolean
}
```

### chatSlice

```
chatState = {
  conversations: {
    [conversationId: string]: {
      id: string
      tenantId: string
      userId: string
      startedAt: string            ← ISO 8601
      lastMessageAt: string
      status: 'active' | 'closed' | 'escalated'
    }
  }
  activeConversationId: string | null
  messages: {
    [conversationId: string]: Array<{
      id: string
      conversationId: string
      role: 'user' | 'assistant' | 'system'
      content: string
      timestamp: string
      status: 'sending' | 'sent' | 'delivered' | 'error'
      metadata?: {
        agentType: 'almacen' | 'soporte' | 'faq'
        confidence: number
        sources?: string[]
      }
    }>
  }
  typingIndicator: boolean
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
  error: string | null
}
```

### adminSlice

```
adminState = {
  dashboard: {
    totalConversations: number
    activeChats: number
    escalatedCases: number
    avgResponseTime: number        ← en segundos
    satisfactionScore: number      ← 0-5
    status: 'idle' | 'loading' | 'loaded' | 'error'
  }
  cases: {
    items: Array<{
      id: string
      ticketNumber: string         ← "SOP-1234"
      userId: string
      subject: string
      status: 'open' | 'in_progress' | 'escalated' | 'resolved' | 'closed'
      priority: 'low' | 'medium' | 'high' | 'urgent'
      assignedTo: string | null
      createdAt: string
      updatedAt: string
    }>
    pagination: { page: number, pageSize: number, total: number }
    filters: { status?: string, priority?: string, search?: string }
    status: 'idle' | 'loading' | 'loaded' | 'error'
  }
  knowledgeBase: {
    entries: Array<{
      id: string
      title: string
      content: string
      category: string
      tags: string[]
      updatedAt: string
    }>
    status: 'idle' | 'loading' | 'loaded' | 'error'
  }
  tenantConfig: {
    name: string
    slug: string
    plan: 'basic' | 'pro' | 'enterprise'
    agentConfig: {
      greeting: string
      tone: 'formal' | 'casual' | 'professional'
      enabledAgents: ('almacen' | 'soporte' | 'faq')[]
      escalationThreshold: number
    }
    status: 'idle' | 'loading' | 'loaded' | 'error'
  }
}
```

### notificationSlice

```
notificationState = {
  items: Array<{
    id: string
    type: 'info' | 'success' | 'warning' | 'error'
    title: string
    message: string
    timestamp: string
    read: boolean
    action?: {
      label: string
      route: string              ← ruta interna para navegar
    }
  }>
  unreadCount: number
  toasts: Array<{
    id: string
    type: 'info' | 'success' | 'warning' | 'error'
    message: string
    duration: number             ← ms, default 5000
  }>
}
```

---

## 8. Flujo de Autenticación (Cognito + Amplify)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Flujo de Login                                  │
│                                                                 │
│  Usuario ingresa email + password                               │
│       │                                                         │
│       ▼                                                         │
│  LoginForm.tsx                                                  │
│  dispatch(loginThunk({ email, password }))                      │
│       │                                                         │
│       ▼                                                         │
│  authService.ts                                                 │
│  Amplify.Auth.signIn(email, password)                           │
│       │                                                         │
│       ├──► MFA requerido?                                       │
│       │    Sí → dispatch(setMfaRequired(true))                  │
│       │         → Mostrar MFAForm.tsx                           │
│       │         → Amplify.Auth.confirmSignIn(code)              │
│       │                                                         │
│       ▼                                                         │
│  Cognito devuelve tokens                                        │
│  { accessToken, idToken, refreshToken }                         │
│       │                                                         │
│       ▼                                                         │
│  authSlice.ts                                                   │
│  state.user = decodedIdToken                                    │
│  state.tokens = { accessToken, refreshToken, expiresAt }        │
│  state.status = 'authenticated'                                 │
│       │                                                         │
│       ▼                                                         │
│  eventMiddleware.ts                                             │
│  Emite: "auth:login_success"                                    │
│       │                                                         │
│       ├──► chatService escucha → abre WebSocket con token       │
│       ├──► apiClient escucha → configura Authorization header   │
│       └──► analytics escucha → trackea login                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  Flujo de Token Refresh                          │
│                                                                 │
│  apiClient.ts (Axios interceptor)                               │
│       │                                                         │
│       ├── Request sale con Authorization: Bearer <accessToken>  │
│       │                                                         │
│       ├── Respuesta 401?                                        │
│       │    │                                                    │
│       │    ▼                                                    │
│       │  Amplify.Auth.currentSession()                          │
│       │  → Cognito renueva tokens automáticamente               │
│       │    │                                                    │
│       │    ├── OK → Retry request original con nuevo token      │
│       │    │        dispatch(tokensRefreshed(newTokens))        │
│       │    │                                                    │
│       │    └── Fail → dispatch(sessionExpired())                │
│       │              Emite: "auth:session_expired"              │
│       │              → Redirect a /login                        │
│       │              → Limpiar estado                           │
│       │                                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  Flujo de Registro                               │
│                                                                 │
│  SignUpForm.tsx                                                  │
│  dispatch(registerThunk({ email, password, name, tenantSlug })) │
│       │                                                         │
│       ▼                                                         │
│  Amplify.Auth.signUp({ username: email, password, attributes }) │
│       │                                                         │
│       ▼                                                         │
│  Cognito envía código de verificación al email                  │
│       │                                                         │
│       ▼                                                         │
│  VerifyEmailForm.tsx                                            │
│  Amplify.Auth.confirmSignUp(email, code)                        │
│       │                                                         │
│       ▼                                                         │
│  Auto-login → mismo flujo de Login                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Roles y acceso:**

| Rol | Acceso | Rutas |
|---|---|---|
| `client` | Solo chat | `/chat` |
| `admin` | Chat + Panel admin de su tenant | `/chat`, `/admin/*` |
| `superadmin` | Todo + gestión multi-tenant | `/chat`, `/admin/*`, `/superadmin/*` |

---

## 9. WebSocket — Gestión de Conexión

```
┌─────────────────────────────────────────────────────────────────┐
│                  websocket.ts — Connection Manager               │
│                                                                 │
│  Configuración:                                                 │
│  ┌────────────────────────────────────────┐                     │
│  │ url: wss://api.growders.mx/ws          │                     │
│  │ reconnectInterval: 1000ms (initial)    │                     │
│  │ reconnectBackoff: exponential (x2)     │                     │
│  │ maxReconnectInterval: 30000ms          │                     │
│  │ maxReconnectAttempts: 10               │                     │
│  │ heartbeatInterval: 30000ms             │                     │
│  └────────────────────────────────────────┘                     │
│                                                                 │
│  Ciclo de vida:                                                 │
│                                                                 │
│  connect(token)                                                 │
│       │                                                         │
│       ▼                                                         │
│  new WebSocket(url + "?token=" + accessToken)                   │
│       │                                                         │
│       ├── onopen                                                │
│       │   dispatch(wsConnected())                               │
│       │   Emite: "websocket:connected"                          │
│       │   Iniciar heartbeat (ping cada 30s)                     │
│       │                                                         │
│       ├── onmessage                                             │
│       │   ┌──────────────────────────────────────┐              │
│       │   │ type: "chat_message"                 │              │
│       │   │ → dispatch(messageReceived(data))    │              │
│       │   ├──────────────────────────────────────┤              │
│       │   │ type: "typing_indicator"             │              │
│       │   │ → dispatch(setTyping(data.isTyping)) │              │
│       │   ├──────────────────────────────────────┤              │
│       │   │ type: "case_update"                  │              │
│       │   │ → dispatch(caseUpdated(data))        │              │
│       │   ├──────────────────────────────────────┤              │
│       │   │ type: "notification"                 │              │
│       │   │ → dispatch(addNotification(data))    │              │
│       │   ├──────────────────────────────────────┤              │
│       │   │ type: "pong"                         │              │
│       │   │ → resetar heartbeat timeout          │              │
│       │   └──────────────────────────────────────┘              │
│       │                                                         │
│       ├── onclose                                               │
│       │   dispatch(wsDisconnected())                            │
│       │   Emite: "websocket:disconnected"                       │
│       │   ¿Fue intencional?                                     │
│       │     No → iniciar reconnect con backoff                  │
│       │     Sí → no reconectar                                  │
│       │                                                         │
│       └── onerror                                               │
│           Log error → disparar onclose                          │
│                                                                 │
│  Reconnect con backoff exponencial:                             │
│  ┌─────────────────────────────────────────────┐                │
│  │ Intento 1: espera 1s                        │                │
│  │ Intento 2: espera 2s                        │                │
│  │ Intento 3: espera 4s                        │                │
│  │ Intento 4: espera 8s                        │                │
│  │ ...                                         │                │
│  │ Intento N: espera min(2^N * 1000, 30000)ms  │                │
│  │                                              │                │
│  │ Después de 10 intentos fallidos:            │                │
│  │ → dispatch(wsReconnectFailed())             │                │
│  │ → Mostrar banner "Conexión perdida"         │                │
│  │ → Botón "Reintentar" manual                 │                │
│  └─────────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Admin Panel — Componentes Detallados

```
/admin
├── Dashboard.tsx
│   ┌────────────────────────────────────────────────────┐
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ │
│   │  │Chats hoy │ │Casos     │ │Tiempo    │ │CSAT  │ │
│   │  │   142    │ │abiertos  │ │respuesta │ │ 4.2  │ │
│   │  │  +12%    │ │   8      │ │  2.3s    │ │ /5   │ │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────┘ │
│   │                                                    │
│   │  ┌─────────────────────────────────────────────┐  │
│   │  │  Gráfica: Conversaciones últimos 7 días     │  │
│   │  │  ████                                       │  │
│   │  │  ████ ██                                    │  │
│   │  │  ████ ██ ████                               │  │
│   │  │  Lu   Ma  Mi   Ju  Vi  Sa  Do               │  │
│   │  └─────────────────────────────────────────────┘  │
│   │                                                    │
│   │  ┌─────────────────────────────────────────────┐  │
│   │  │  Distribución por agente                    │  │
│   │  │  Almacén: ████████████ 45%                  │  │
│   │  │  FAQ:     ████████ 30%                      │  │
│   │  │  Soporte: ██████ 25%                        │  │
│   │  └─────────────────────────────────────────────┘  │
│   └────────────────────────────────────────────────────┘
│
├── KnowledgeBase/
│   ├── KnowledgeList.tsx
│   │   ┌────────────────────────────────────────────┐
│   │   │  [+ Nuevo Artículo]   [Buscar...]         │
│   │   │                                            │
│   │   │  ┌──────────────────────────────────────┐  │
│   │   │  │ Política de devoluciones     [Edit]  │  │
│   │   │  │ Categoría: Políticas | Tags: ...     │  │
│   │   │  ├──────────────────────────────────────┤  │
│   │   │  │ Horarios de atención          [Edit] │  │
│   │   │  │ Categoría: FAQ | Tags: ...           │  │
│   │   │  ├──────────────────────────────────────┤  │
│   │   │  │ Catálogo de productos         [Edit] │  │
│   │   │  │ Categoría: Almacén | Tags: ...       │  │
│   │   │  └──────────────────────────────────────┘  │
│   │   └────────────────────────────────────────────┘
│   │
│   └── KnowledgeEditor.tsx
│       ┌────────────────────────────────────────────┐
│       │  Título: [________________________]        │
│       │  Categoría: [Políticas ▼]                  │
│       │  Tags: [devol] [cambios] [+ agregar]       │
│       │                                            │
│       │  Contenido:                                │
│       │  ┌──────────────────────────────────────┐  │
│       │  │  Editor Markdown                     │  │
│       │  │  ...                                 │  │
│       │  └──────────────────────────────────────┘  │
│       │                                            │
│       │  [Cancelar]  [Guardar]                     │
│       └────────────────────────────────────────────┘
│
├── CasesManager/
│   ├── CasesList.tsx
│   │   ┌────────────────────────────────────────────┐
│   │   │  Filtros: [Estado ▼] [Prioridad ▼] [🔍]  │
│   │   │                                            │
│   │   │  #SOP-1234  Login fallido    🔴 Urgente   │
│   │   │  #SOP-1235  Precio erróneo   🟡 Media     │
│   │   │  #SOP-1236  Envío retrasado  🟢 Baja      │
│   │   │                                            │
│   │   │  Página 1 de 5  [< Anterior] [Siguiente >]│
│   │   └────────────────────────────────────────────┘
│   │
│   └── CaseDetail.tsx
│       ┌────────────────────────────────────────────┐
│       │  #SOP-1234 — Login fallido                 │
│       │  Estado: Abierto → [Asignar ▼] [Resolver] │
│       │  Prioridad: 🔴 Urgente                    │
│       │  Creado: 2025-06-10 14:30                  │
│       │                                            │
│       │  Historial de conversación:                │
│       │  ┌──────────────────────────────────────┐  │
│       │  │ 14:30 Cliente: No puedo entrar...    │  │
│       │  │ 14:30 Bot: Voy a crear un ticket...  │  │
│       │  │ 14:35 Admin: Revisando tu cuenta...  │  │
│       │  └──────────────────────────────────────┘  │
│       │                                            │
│       │  Responder: [__________________] [Enviar]  │
│       └────────────────────────────────────────────┘
│
├── TenantConfig/
│   └── TenantSettings.tsx
│       ┌────────────────────────────────────────────┐
│       │  Configuración del Negocio                 │
│       │                                            │
│       │  Nombre: [Uniformes Vicky_______]          │
│       │  Slug:   uniformes-vicky (no editable)     │
│       │  Plan:   Basic ⭐                          │
│       │                                            │
│       │  Configuración del Agente:                 │
│       │  Saludo: [¡Hola! ¿En qué puedo...]        │
│       │  Tono:   [Profesional ▼]                   │
│       │  Agentes activos:                          │
│       │    ☑ Almacén  ☑ FAQ  ☑ Soporte             │
│       │  Umbral de escalamiento: [3] intentos      │
│       │                                            │
│       │  [Guardar Cambios]                         │
│       └────────────────────────────────────────────┘
│
└── Analytics/
    └── AnalyticsDashboard.tsx
        ┌────────────────────────────────────────────┐
        │  Período: [Últimos 7 días ▼]              │
        │                                            │
        │  ┌─────────────────┐ ┌─────────────────┐  │
        │  │ Mensajes totales│ │ Tasa resolución │  │
        │  │     1,247       │ │      87%        │  │
        │  └─────────────────┘ └─────────────────┘  │
        │                                            │
        │  Top preguntas:                            │
        │  1. "¿Tienen uniforme talla L?" (89)       │
        │  2. "¿Cuál es el horario?" (67)            │
        │  3. "¿Aceptan tarjeta?" (45)               │
        │                                            │
        │  Agente con más uso:                       │
        │  Almacén (45%) > FAQ (30%) > Soporte (25%) │
        └────────────────────────────────────────────┘
```

---

## 11. Routing y Protección de Rutas

```
┌─────────────────────────────────────────────────────────────────┐
│                    AppRouter.tsx                                  │
│                                                                 │
│  <BrowserRouter>                                                │
│    <Routes>                                                     │
│                                                                 │
│      ┌── Rutas Públicas (publicRoutes.tsx) ────────────────┐    │
│      │                                                     │    │
│      │  /login          → LoginForm.tsx                    │    │
│      │  /signup         → SignUpForm.tsx                   │    │
│      │  /verify-email   → VerifyEmailForm.tsx              │    │
│      │  /forgot-password→ ForgotPasswordForm.tsx           │    │
│      │                                                     │    │
│      │  Si ya autenticado → redirect a /chat o /admin      │    │
│      └─────────────────────────────────────────────────────┘    │
│                                                                 │
│      ┌── Rutas Protegidas (protectedRoutes.tsx) ───────────┐    │
│      │                                                     │    │
│      │  <ProtectedRoute>  ← verifica token Cognito        │    │
│      │    │                                                │    │
│      │    ├── /chat                                        │    │
│      │    │   └── ChatWindow.tsx                           │    │
│      │    │       Acceso: client, admin, superadmin        │    │
│      │    │                                                │    │
│      │    ├── /admin  ← requiere role: admin | superadmin  │    │
│      │    │   ├── /admin/dashboard    → Dashboard.tsx      │    │
│      │    │   ├── /admin/cases        → CasesList.tsx      │    │
│      │    │   ├── /admin/cases/:id    → CaseDetail.tsx     │    │
│      │    │   ├── /admin/knowledge    → KnowledgeList.tsx  │    │
│      │    │   ├── /admin/knowledge/new→ KnowledgeEditor    │    │
│      │    │   ├── /admin/knowledge/:id→ KnowledgeEditor    │    │
│      │    │   ├── /admin/config       → TenantSettings     │    │
│      │    │   └── /admin/analytics    → AnalyticsDashboard │    │
│      │    │                                                │    │
│      │    └── /superadmin ← requiere role: superadmin      │    │
│      │        ├── /superadmin/tenants → TenantList.tsx     │    │
│      │        └── /superadmin/tenants/:id → TenantDetail   │    │
│      │                                                     │    │
│      └─────────────────────────────────────────────────────┘    │
│                                                                 │
│      /*  → NotFound.tsx (404)                                   │
│                                                                 │
│    </Routes>                                                    │
│  </BrowserRouter>                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**ProtectedRoute — lógica interna:**

```
ProtectedRoute({ children, requiredRole? })
       │
       ▼
  ¿Token existe en store?
       │
  No ──► redirect /login (guardar returnUrl)
       │
  Sí ──► ¿Token expirado?
              │
         Sí ──► intentar refresh silencioso
              │     │
              │  Fail ──► redirect /login
              │     │
              │  OK ──► continuar
              │
         No ──► ¿requiredRole definido?
                    │
               Sí ──► ¿user.role >= requiredRole?
                    │     │
                    │  No ──► redirect /unauthorized (403)
                    │     │
                    │  Sí ──► render children
                    │
               No ──► render children
```

---

## 12. API Client e Interceptors

```
┌─────────────────────────────────────────────────────────────────┐
│                  apiClient.ts (Axios Instance)                   │
│                                                                 │
│  Base URL: https://api.growders.mx/api/v1                       │
│  Timeout: 30000ms                                               │
│  Headers: { Content-Type: application/json }                    │
│                                                                 │
│  ┌── Request Interceptors ──────────────────────────────────┐   │
│  │                                                          │   │
│  │  1. Auth Interceptor                                     │   │
│  │     → Agrega Authorization: Bearer <accessToken>         │   │
│  │     → Agrega X-Tenant-ID: <tenantId> desde el store     │   │
│  │                                                          │   │
│  │  2. Request ID                                           │   │
│  │     → Agrega X-Request-ID: uuid()                        │   │
│  │     → Para tracing end-to-end con backend                │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌── Response Interceptors ─────────────────────────────────┐   │
│  │                                                          │   │
│  │  1. Token Refresh (401)                                  │   │
│  │     → Intenta renovar token via Cognito                  │   │
│  │     → Si OK: reintenta request original                  │   │
│  │     → Si fail: dispatch(sessionExpired())                │   │
│  │     → Cola de requests pendientes durante refresh        │   │
│  │                                                          │   │
│  │  2. Error Normalizer                                     │   │
│  │     → 400: ValidationError → mostrar en formulario       │   │
│  │     → 403: Forbidden → redirect /unauthorized            │   │
│  │     → 404: NotFound → mostrar mensaje                    │   │
│  │     → 429: RateLimited → retry con backoff               │   │
│  │     → 500: ServerError → toast genérico                  │   │
│  │     → Network Error → toast "Sin conexión"               │   │
│  │                                                          │   │
│  │  3. Response Logger                                      │   │
│  │     → Log en desarrollo: método, url, status, duración   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**RTK Query — API Definition:**

```
Endpoints agrupados por feature:

authApi
  ├── POST /auth/login         → login()
  ├── POST /auth/register      → register()
  ├── POST /auth/refresh       → refreshToken()
  └── GET  /auth/profile       → getProfile()

chatApi
  ├── POST /chat               → sendMessage()
  ├── GET  /chat/conversations → getConversations()
  ├── GET  /chat/:convId       → getConversation()
  └── GET  /chat/:convId/msgs  → getMessages()

adminApi
  ├── GET  /admin/dashboard    → getDashboard()
  ├── CRUD /admin/cases        → getCases(), getCase(), updateCase()
  ├── CRUD /admin/knowledge    → getEntries(), createEntry(), updateEntry(), deleteEntry()
  ├── GET  /admin/analytics    → getAnalytics()
  └── CRUD /admin/config       → getConfig(), updateConfig()
```

---

## 13. Seguridad Frontend

| Aspecto | Implementación |
|---|---|
| **XSS** | React escapa por defecto. No usar `dangerouslySetInnerHTML`. Sanitizar Markdown con `DOMPurify` antes de renderizar. |
| **CSRF** | No aplica (API stateless con JWT, no cookies de sesión). |
| **Auth tokens** | Almacenados en memoria (Redux store). No en localStorage ni sessionStorage. Amplify maneja persistencia segura. |
| **Input validation** | Validación client-side con Zod/Yup. Max 500 chars en chat. Nunca confiar solo en validación frontend. |
| **CSP** | `Content-Security-Policy` configurado en CloudFront. `connect-src` restringido a `api.growders.mx`. |
| **CORS** | Manejado por API Gateway. Frontend no necesita configuración adicional. |
| **Dependencias** | `npm audit` en CI/CD. Renovate/Dependabot para updates automáticos. |
| **Variables sensibles** | Nunca en código. Usar variables de entorno de Amplify (`REACT_APP_*`). |
| **Rate limiting** | Debounce en inputs (300ms). Throttle en botones de submit. Backend aplica rate limit real. |

---

## 14. Configuración de Entornos

```
┌─────────────────────────────────────────────────────────────────┐
│                  Variables de Entorno por Ambiente                │
│                                                                 │
│  ┌── .env.development ──────────────────────────────────────┐   │
│  │  REACT_APP_API_URL=http://localhost:8000/api/v1          │   │
│  │  REACT_APP_WS_URL=ws://localhost:8000/ws                 │   │
│  │  REACT_APP_AWS_REGION=us-east-1                          │   │
│  │  REACT_APP_USER_POOL_ID=us-east-1_XXXXXX                │   │
│  │  REACT_APP_USER_POOL_CLIENT_ID=xxxxxxxxxx                │   │
│  │  REACT_APP_ENV=development                               │   │
│  │  REACT_APP_LOG_LEVEL=debug                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌── .env.staging ──────────────────────────────────────────┐   │
│  │  REACT_APP_API_URL=https://api-staging.growders.mx/api/v1│   │
│  │  REACT_APP_WS_URL=wss://api-staging.growders.mx/ws       │   │
│  │  REACT_APP_AWS_REGION=us-east-1                          │   │
│  │  REACT_APP_USER_POOL_ID=us-east-1_YYYYYY                │   │
│  │  REACT_APP_USER_POOL_CLIENT_ID=yyyyyyyyyy                │   │
│  │  REACT_APP_ENV=staging                                   │   │
│  │  REACT_APP_LOG_LEVEL=warn                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌── .env.production ──────────────────────────────────────┐    │
│  │  REACT_APP_API_URL=https://api.growders.mx/api/v1       │    │
│  │  REACT_APP_WS_URL=wss://api.growders.mx/ws              │    │
│  │  REACT_APP_AWS_REGION=us-east-1                         │    │
│  │  REACT_APP_USER_POOL_ID=us-east-1_ZZZZZZ               │    │
│  │  REACT_APP_USER_POOL_CLIENT_ID=zzzzzzzzzz               │    │
│  │  REACT_APP_ENV=production                               │    │
│  │  REACT_APP_LOG_LEVEL=error                              │    │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 15. Error Handling y Estados de UI

```
┌─────────────────────────────────────────────────────────────────┐
│                  Estrategia de Manejo de Errores                 │
│                                                                 │
│  ┌── Nivel 1: Error Boundaries (React) ─────────────────────┐  │
│  │                                                          │  │
│  │  <ErrorBoundary fallback={<CrashScreen />}>              │  │
│  │    <App />                                               │  │
│  │  </ErrorBoundary>                                        │  │
│  │                                                          │  │
│  │  Captura errores de renderizado.                         │  │
│  │  Muestra pantalla de error con botón "Recargar".         │  │
│  │  Log a CloudWatch via API.                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── Nivel 2: RTK Query Error States ───────────────────────┐  │
│  │                                                          │  │
│  │  const { data, isLoading, isError, error } = useQuery()  │  │
│  │                                                          │  │
│  │  isLoading → <Skeleton /> o <Spinner />                  │  │
│  │  isError   → <ErrorMessage error={error} />              │  │
│  │  data      → renderizar contenido                        │  │
│  │                                                          │  │
│  │  Retry automático: 3 intentos, backoff exponencial.      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── Nivel 3: Toast Notifications ──────────────────────────┐  │
│  │                                                          │  │
│  │  Errores no críticos → Toast rojo (5s, dismissable)      │  │
│  │  Éxito              → Toast verde (3s, auto-dismiss)     │  │
│  │  Warnings           → Toast amarillo (5s)                │  │
│  │  Info               → Toast azul (3s)                    │  │
│  │                                                          │  │
│  │  Posición: top-right                                     │  │
│  │  Max visible: 3 (los demás en cola)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌── Nivel 4: Formularios ──────────────────────────────────┐  │
│  │                                                          │  │
│  │  Validación inline con React Hook Form + Zod.            │  │
│  │  Errores del API mapeados a campos específicos.          │  │
│  │  Errores genéricos mostrados arriba del formulario.      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 16. Integración Frontend ↔ Backend

```
┌────────────────────┐                    ┌────────────────────┐
│   FRONTEND         │                    │   BACKEND          │
│   (React + Redux)  │                    │   (Python + Fast)  │
│                    │                    │                    │
│  apiClient.ts ─────┼── REST ──────────►─┤ API Gateway       │
│  Authorization:    │   POST /chat       │ → Lambda/EKS      │
│  Bearer <token>    │   GET /admin/*     │                    │
│  X-Tenant-ID:      │   CRUD /cases/*    │ authSlice ←──────►│ Cognito
│  <tenantId>        │                    │                    │
│                    │                    │                    │
│  websocket.ts ─────┼── WebSocket ─────►─┤ API Gateway WS    │
│  ?token=<jwt>      │   bidirectional    │ → Lambda/EKS      │
│                    │                    │                    │
│  chatSlice         │   Eventos WS:      │                    │
│  ← message_received│◄── chat_message ──┤ LangChain Agent   │
│  ← setTyping       │◄── typing_indicator│                    │
│  ← caseUpdated     │◄── case_update ───┤ Cases Module      │
│  ← addNotification │◄── notification ──┤ Event System      │
│                    │                    │                    │
│  Amplify Auth ─────┼── Cognito ────────►┤ Token validation  │
│  signIn/signUp     │   JWT tokens       │ middleware        │
│  currentSession    │                    │                    │
└────────────────────┘                    └────────────────────┘

Contrato de API:

  Request headers (todos los requests):
    Authorization: Bearer <accessToken>
    X-Tenant-ID: <uuid>
    X-Request-ID: <uuid>
    Content-Type: application/json

  Response format (estándar):
    {
      "success": true,
      "data": { ... },
      "meta": { "page": 1, "total": 50 }
    }

  Error format (estándar):
    {
      "success": false,
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "El campo email es requerido",
        "details": [{ "field": "email", "message": "..." }]
      }
    }
```

---

## Resumen de Tecnologías

| Capa | Tecnología |
|---|---|
| **Framework** | React 18 + TypeScript |
| **State Management** | Redux Toolkit + RTK Query |
| **Routing** | React Router v6 |
| **Formularios** | React Hook Form + Zod |
| **Autenticación** | AWS Amplify Auth (Cognito) |
| **API Client** | RTK Query + Axios (interceptors) |
| **WebSocket** | Native WebSocket con reconnect automático |
| **UI Components** | Shared UI Kit (propio) |
| **Hosting** | AWS Amplify Hosting (S3 + CloudFront) |
| **CI/CD** | Amplify Pipeline (GitHub integration) |
| **DNS** | Route 53 |
| **SSL** | ACM (AWS Certificate Manager) |
| **CDN** | CloudFront |
| **Testing** | Jest + React Testing Library |
| **Linting** | ESLint + Prettier |

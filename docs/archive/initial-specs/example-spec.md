# 项目规格文档示例

> 这是一个完整的 SPEC 示例，展示了如何编写供 Sloth Agent 框架使用的规格文档

---

## 项目信息

- **项目名称**: Task Management API
- **版本**: 1.0.0
- **日期**: 2026-04-14
- **项目类型**: REST API 服务
- **目标用户**: 前端应用和第三方集成

---

## 1. 项目概述

构建一个任务管理 REST API，支持用户的认证注册、任务 CRUD 操作，以及简单的数据分析接口。

---

## 2. 技术栈

| 层级 | 技术选型 |
|------|---------|
| 语言 | Python 3.10+ |
| 框架 | FastAPI |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| ORM | SQLAlchemy |
| 认证 | JWT |
| 测试 | pytest + pytest-cov |
| 文档 | OpenAPI (自动生成) |

---

## 3. 功能需求

### 3.1 用户认证

| 功能 | 描述 | API 端点 |
|------|------|---------|
| 注册 | 用户名 + 密码注册 | `POST /auth/register` |
| 登录 | 返回 JWT Token | `POST /auth/login` |
| 刷新 | 刷新 Token | `POST /auth/refresh` |
| 登出 | 使 Token 失效 | `POST /auth/logout` |

### 3.2 任务管理

| 功能 | 描述 | API 端点 |
|------|------|---------|
| 创建任务 | 创建新任务 | `POST /tasks` |
| 列表任务 | 获取用户所有任务 | `GET /tasks` |
| 获取任务 | 获取单个任务 | `GET /tasks/{id}` |
| 更新任务 | 更新任务内容 | `PUT /tasks/{id}` |
| 删除任务 | 软删除任务 | `DELETE /tasks/{id}` |

### 3.3 数据统计

| 功能 | 描述 | API 端点 |
|------|------|---------|
| 任务统计 | 返回完成率等统计 | `GET /stats` |
| 任务趋势 | 每日任务完成趋势 | `GET /stats/trend` |

---

## 4. 数据模型

### 4.1 User

```
id: UUID (PK)
username: String (unique, 3-50 chars)
password_hash: String
created_at: DateTime
updated_at: DateTime
```

### 4.2 Task

```
id: UUID (PK)
user_id: UUID (FK -> User)
title: String (1-200 chars)
description: Text (optional)
status: Enum [pending, in_progress, completed]
priority: Enum [low, medium, high]
due_date: DateTime (optional)
created_at: DateTime
updated_at: DateTime
deleted_at: DateTime (optional, soft delete)
```

---

## 5. API 详细规格

### 5.1 认证接口

#### POST /auth/register

**请求体**:
```json
{
  "username": "user@example.com",
  "password": "SecurePass123"
}
```

**响应 (201)**:
```json
{
  "id": "uuid",
  "username": "user@example.com",
  "created_at": "2026-04-14T10:00:00Z"
}
```

#### POST /auth/login

**请求体**:
```json
{
  "username": "user@example.com",
  "password": "SecurePass123"
}
```

**响应 (200)**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 5.2 任务接口

#### POST /tasks

**请求头**: `Authorization: Bearer <token>`

**请求体**:
```json
{
  "title": "完成报告",
  "description": "撰写 Q1 季度报告",
  "priority": "high",
  "due_date": "2026-04-20T18:00:00Z"
}
```

**响应 (201)**:
```json
{
  "id": "uuid",
  "title": "完成报告",
  "description": "撰写 Q1 季度报告",
  "status": "pending",
  "priority": "high",
  "due_date": "2026-04-20T18:00:00Z",
  "created_at": "2026-04-14T10:00:00Z"
}
```

---

## 6. 错误处理

### 6.1 错误响应格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {"field": "username", "message": "Username too short"}
    ]
  }
}
```

### 6.2 错误码

| HTTP Status | Error Code | 说明 |
|-------------|-----------|------|
| 400 | VALIDATION_ERROR | 请求参数验证失败 |
| 401 | UNAUTHORIZED | 未认证或 Token 过期 |
| 403 | FORBIDDEN | 无权限访问 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（如用户名已存在）|
| 500 | INTERNAL_ERROR | 服务器内部错误 |

---

## 7. 安全要求

1. **密码存储**: 使用 bcrypt 哈希，不明文存储
2. **Token**: JWT + 签名过期时间 1 小时
3. **权限控制**: 用户只能访问自己的任务
4. **输入验证**: 所有输入必须验证和清理
5. **SQL 注入**: 使用 ORM 防止 SQL 注入
6. **HTTPS**: 生产环境必须使用 HTTPS

---

## 8. 测试要求

### 8.1 单元测试

- 每个函数/方法必须有单元测试
- Mock 外部依赖
- 覆盖率目标: ≥ 80%

### 8.2 集成测试

- API 端点集成测试
- 数据库操作测试
- 认证流程测试

### 8.3 测试命令

```bash
# 运行所有测试
pytest

# 带覆盖率
pytest --cov=src --cov-report=html

# 只运行单元测试
pytest tests/unit/

# 只运行集成测试
pytest tests/integration/
```

---

## 9. 项目结构

```
task-api/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── task.py
│   ├── schemas/             # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── task.py
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── tasks.py
│   │   └── stats.py
│   ├── services/           # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── task.py
│   └── core/                # 核心功能
│       ├── __init__.py
│       ├── security.py
│       └── database.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── requirements.txt
├── .env.example
└── README.md
```

---

## 10. 成功标准

| 标准 | 目标 |
|------|------|
| 功能完整 | 所有 API 端点可正常工作 |
| 测试覆盖 | 单元测试覆盖率 ≥ 80% |
| 代码质量 | 无明显代码异味 |
| 文档完整 | OpenAPI 文档自动生成 |
| 可运行 | `uvicorn src.main:app` 可启动 |

---

## 11. 限制与约束

1. 第一版本不实现：邮件验证、密码重置、OAuth 第三方登录
2. 第一版本使用 SQLite，PostgreSQL 支持在 v2
3. 不实现微服务架构，保持单体应用

---

*示例规格文档 - 供参考*

# REST API 文档

## 概述

智服云提供完整的REST API接口，支持对话查询、工单管理、数据统计等功能。API采用RESTful设计，使用JSON格式传输数据。

## 认证方式

### OAuth 2.0

API使用OAuth 2.0进行认证：

1. 在管理后台创建API密钥
2. 使用密钥获取Access Token
3. 在请求头中携带Token

### 获取Token

```http
POST https://api.zhifuyun.com/oauth/token
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 使用Token

在请求头中添加：

```
Authorization: Bearer {access_token}
```

Token有效期为1小时，过期后需要重新获取。

## 接口说明

### 对话查询

#### 获取对话列表

```http
GET https://api.zhifuyun.com/v1/conversations
Authorization: Bearer {token}
```

查询参数：

- `page`: 页码，默认1
- `limit`: 每页数量，默认20，最大100
- `status`: 状态筛选（active/closed）
- `start_time`: 开始时间（ISO 8601格式）
- `end_time`: 结束时间（ISO 8601格式）

响应：

```json
{
  "code": 200,
  "data": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": "conv_001",
        "user_id": "user_123",
        "channel": "web",
        "status": "active",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:05:00Z"
      }
    ]
  }
}
```

#### 获取对话详情

```http
GET https://api.zhifuyun.com/v1/conversations/{conversation_id}
Authorization: Bearer {token}
```

#### 创建对话

```http
POST https://api.zhifuyun.com/v1/conversations
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "user_123",
  "channel": "web",
  "initial_message": "你好，我想咨询产品"
}
```

### 工单管理

#### 获取工单列表

```http
GET https://api.zhifuyun.com/v1/tickets
Authorization: Bearer {token}
```

查询参数：

- `status`: 状态筛选
- `priority`: 优先级筛选
- `assignee_id`: 处理人ID
- `page`, `limit`: 分页参数

#### 创建工单

```http
POST https://api.zhifuyun.com/v1/tickets
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "产品咨询",
  "description": "想了解产品价格和功能",
  "priority": "medium",
  "customer_email": "customer@example.com"
}
```

#### 更新工单状态

```http
PATCH https://api.zhifuyun.com/v1/tickets/{ticket_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "resolved",
  "comment": "问题已解决"
}
```

### 数据统计

#### 获取统计数据

```http
GET https://api.zhifuyun.com/v1/statistics
Authorization: Bearer {token}
```

查询参数：

- `type`: 统计类型（conversation/ticket/satisfaction）
- `start_date`: 开始日期
- `end_date`: 结束日期
- `group_by`: 分组方式（day/week/month）

响应：

```json
{
  "code": 200,
  "data": {
    "total_conversations": 1000,
    "total_tickets": 200,
    "avg_response_time": 120,
    "satisfaction_rate": 0.85,
    "trends": [
      {
        "date": "2024-01-01",
        "conversations": 50,
        "tickets": 10
      }
    ]
  }
}
```

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权，Token无效或过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |

## 限流规则

API调用频率限制：

- 免费版：每分钟100次
- 企业版：每分钟1000次
- 超限后返回429错误，需要等待后重试

## Webhook事件

### 事件类型

支持以下Webhook事件：

- `conversation.created`: 对话创建
- `conversation.closed`: 对话关闭
- `ticket.created`: 工单创建
- `ticket.updated`: 工单更新
- `ticket.resolved`: 工单解决

### 配置Webhook

在管理后台配置Webhook URL和订阅事件类型。事件发生时，系统会向配置的URL发送POST请求。

### 事件格式

```json
{
  "event": "ticket.created",
  "timestamp": "2024-01-01T10:00:00Z",
  "data": {
    "ticket_id": "ticket_001",
    "title": "产品咨询",
    "priority": "medium"
  }
}
```

### 重试机制

Webhook发送失败后会重试，最多重试3次，间隔递增（1秒、5秒、30秒）。

## SDK支持

官方提供以下SDK：

- Python SDK
- Node.js SDK
- Java SDK
- PHP SDK

SDK文档：https://docs.zhifuyun.com/sdk


# Webhook配置指南

## Webhook概述

Webhook是一种事件通知机制。当系统中发生特定事件时（如工单创建、状态变更），系统会向您配置的URL发送HTTP POST请求，通知您事件的发生。

## 配置Webhook

### 基本配置

1. 登录管理后台
2. 进入"系统设置" → "Webhook配置"
3. 点击"新建Webhook"
4. 填写配置信息：
   - **Webhook名称**：用于标识，如"工单通知"
   - **Webhook URL**：接收事件的服务器地址，必须是HTTPS
   - **认证方式**：选择Basic Auth或Bearer Token
   - **认证密钥**：用于验证请求的密钥
   - **订阅事件**：选择需要接收的事件类型
5. 点击"保存"完成配置

### 订阅事件类型

可以选择订阅以下事件：

- **对话事件**：
  - `conversation.created`：对话创建
  - `conversation.closed`：对话关闭
  - `message.received`：收到新消息

- **工单事件**：
  - `ticket.created`：工单创建
  - `ticket.updated`：工单更新
  - `ticket.resolved`：工单解决
  - `ticket.closed`：工单关闭

- **用户事件**：
  - `user.created`：用户创建
  - `user.updated`：用户更新

### 认证配置

#### Basic Auth

在请求头中添加：

```
Authorization: Basic {base64(username:password)}
```

#### Bearer Token

在请求头中添加：

```
Authorization: Bearer {token}
```

## 事件格式

### 请求格式

Webhook请求使用POST方法，Content-Type为application/json，请求体格式：

```json
{
  "event": "ticket.created",
  "timestamp": "2024-01-01T10:00:00Z",
  "signature": "sha256=...",
  "data": {
    "ticket_id": "ticket_001",
    "title": "产品咨询",
    "description": "想了解产品价格",
    "priority": "medium",
    "status": "pending",
    "assignee_id": "user_123",
    "customer_email": "customer@example.com",
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

### 事件字段说明

- `event`：事件类型
- `timestamp`：事件发生时间（ISO 8601格式）
- `signature`：请求签名，用于验证请求来源
- `data`：事件数据，不同事件类型数据结构不同

## 签名验证

### 验证方法

为了确保请求来自智服云，建议验证请求签名：

1. 使用配置的密钥和请求体计算HMAC SHA256
2. 与请求头中的signature字段比较
3. 如果一致，说明请求合法

### 示例代码（Python）

```python
import hmac
import hashlib
import json

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 重试机制

### 重试策略

如果Webhook请求失败（HTTP状态码不是2xx），系统会重试：

- 第1次重试：1秒后
- 第2次重试：5秒后
- 第3次重试：30秒后

如果3次重试都失败，系统会记录错误日志，但不会继续重试。

### 响应要求

您的服务器应该：

1. 在5秒内返回响应
2. 返回HTTP 200状态码表示成功
3. 返回其他状态码表示失败，会触发重试

### 幂等性

由于重试机制，同一个事件可能会被发送多次。您的服务器应该保证处理幂等性，即重复处理同一事件不会产生副作用。

## 测试Webhook

### 测试功能

在Webhook配置页面，可以点击"测试"按钮发送测试事件。测试事件会立即发送，用于验证配置是否正确。

### 测试事件格式

测试事件使用特殊的事件类型`webhook.test`，data字段包含测试信息。

## 常见问题

### Q: Webhook URL必须是HTTPS吗？

A: 是的，出于安全考虑，只支持HTTPS URL。

### Q: 如何查看Webhook发送日志？

A: 在Webhook配置页面可以查看发送历史，包括成功和失败的记录。

### Q: 可以配置多个Webhook URL吗？

A: 可以，每个事件类型可以配置多个Webhook，系统会并行发送。

### Q: Webhook发送失败怎么办？

A: 系统会自动重试3次，如果都失败会记录错误日志。您可以检查日志排查问题，修复后可以手动触发重试。

## 最佳实践

1. **使用HTTPS**：确保数据传输安全
2. **验证签名**：验证请求来源，防止伪造
3. **快速响应**：在5秒内返回响应，避免超时
4. **处理幂等**：保证重复处理的安全性
5. **记录日志**：记录接收的事件，便于排查问题
6. **错误处理**：妥善处理异常情况，返回适当的HTTP状态码


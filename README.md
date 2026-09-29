# B2B 获客成交工作流(n8n)

自托管 n8n + Postgres,内置三条工作流,覆盖 **找线索 → 培育 → 跟进 → 转人工成交**。

| 文件 | 作用 | 触发 |
|---|---|---|
| `workflows/01-lead-intake.json` | 接收线索 → 打分分级(A/B/C)→ 写入 Notion → A 级通知 Slack 并生成开发信**草稿** | Webhook `POST /webhook/lead` |
| `workflows/02-followup-sequence.json` | 第 3/7/14 天自动生成跟进**草稿**,更新 Notion 进度;已回复/成交/流失/退订自动跳过 | 工作日 9:00 |
| `workflows/03-content-generation.json` | Claude 生成行业内容,发到 Slack **待审核** | 每周一三五 10:00 |

> 设计原则:邮件只建草稿、内容只进审核频道,**由人确认后再发**。这样避免误发、被封域名,也保留成交环节的人工判断。

## 快速开始

```bash
cp .env.example .env        # 填写各项(N8N_ENCRYPTION_KEY 用 openssl rand -hex 24 生成)
docker compose up -d
# 打开 http://localhost:5678 ,创建管理员账号
```

导入工作流(二选一):

```bash
# 命令行
docker compose exec n8n n8n import:workflow --separate --input=/workflows
# 或在界面: Workflows → Import from File
```

## 上线前必做

1. **建 Notion 线索库**,字段名需与工作流一致:
   `名称`(标题)、`评分`(数字)、`等级`(单选 A/B/C)、`状态`(单选:新线索/已回复/已成交/已流失/退订)、
   `邮箱`(邮箱)、`职位`、`行业`、`来源`(文本)、`最后联系`(日期)、`跟进步数`(数字)。
   把库 ID 填进 `.env` 的 `NOTION_LEADS_DB_ID`,并在 Notion 中把该库共享给你的 n8n 集成。
2. **在 n8n 里绑定凭据**(凭据存在 n8n 中,不入仓库):Notion、Slack、Gmail。
   导入后逐个打开节点,选择对应凭据,并**手动执行一次确认字段映射正确**(Notion 节点的字段以你的库为准)。
3. 修改 `.env` 中的 `PRODUCT_PITCH`、`SENDER_NAME`,以及 `01` 里的打分规则、`03` 里的主题列表。
4. 先测试再激活工作流(右上角 Active)。

## 测试线索入库

```bash
curl -X POST http://localhost:5678/webhook-test/lead \
  -H 'Content-Type: application/json' \
  -d '{"company":"示例科技","contact_name":"张三","title":"采购总监","email":"zhang@example.com","industry":"制造业","employees":300,"source":"官网表单","note":"想了解报价"}'
```

(测试期用 `/webhook-test/lead`,激活后用 `/webhook/lead`。)

## 合规提醒

- 群发陌生邮件需提供退订方式并控制频率;抓取数据须遵守各平台条款与当地法规(如个人信息保护法、GDPR)。
- 公网暴露 webhook 时,请加鉴权(n8n Webhook 节点支持 Header Auth)或置于反向代理之后。

# DocHelper - AI 智能文档助手

基于 FastAPI + LangGraph 构建的 RAG 文档问答系统，支持 PDF/Markdown 文档上传解析、智能检索与流式对话。

## 功能特性

* **文档导入**：PDF 解析（MinerU）→ 图片处理（VLM 图片摘要 + MinIO 存储）→ 智能分块 → 主体识别 → BGE-M3 向量化 → 入库

* **智能问答**：指代消解 → 主体匹配 → 多路并行召回（HyDE + 混合检索 + 联网搜索）→ RRF 粗排 → BGE 精排 → LLM 生成回答

* **流式响应**：上传与对话均支持 SSE 流式推送，实时反馈处理进度

* **后台任务**：客户端断开连接后任务继续执行并落库，不丢失数据

## 技术栈

| 类别     | 技术                          |
| ------ | --------------------------- |
| 后端框架   | FastAPI                     |
| 工作流引擎  | LangGraph                   |
| LLM    | OpenAI 兼容接口                 |
| 向量模型   | BGE-M3（稠密+稀疏混合向量）           |
| 精排模型   | BGE-Reranker（Cross-Encoder） |
| 向量数据库  | Milvus                      |
| 关系数据库  | MySQL（SQLAlchemy）           |
| 文档数据库  | MongoDB（会话与消息）              |
| 对象存储   | MinIO（图片）                   |
| PDF 解析 | MinerU                      |
| 联网搜索   | Tavily                      |
| 视觉模型   | VLM（图片摘要生成）                 |

## 项目结构

```
app/
├── api/              # 路由层
├── services/         # 业务服务层
├── graph/            # LangGraph 工作流
│   ├── nodes/        # 工作流节点
│   ├── states/       # 状态定义
│   ├── context/      # 上下文（依赖注入）
│   ├── import_document_graph.py   # 文档导入工作流
│   └── query_graph.py             # 查询工作流
├── infrastructure/   # 基础设施操作层
├── client/           # 客户端初始化
├── config/           # 配置
├── entity/           # ORM / 实体
├── domain/           # 领域模型
├── exception/        # 异常体系
├── model/            # 模型初始化
├── util/             # 工具函数
└── main.py           # 入口
prompts/              # Jinja2 提示词模板
```

## 工作流概览

### 文档导入流

```
文件校验 → PDF 转 MD → 图片处理 → 文档分块 → 主体识别 → 向量化 → 数据入库
```

### 查询流

```
入口 → 指代消解 → 主体匹配 ─┬─→ HyDE 检索 ─┐
                            ├─→ 混合检索 ─┼─→ 多路合并 → RRF 粗排 → BGE 精排 → 生成回答
                            └─→ 联网搜索 ─┘
```

## 快速开始

1. 克隆项目，在项目根目录创建 `.env` 文件，配置各服务连接信息（参考 `.env-example`）
2. 安装依赖
3. 启动服务：

   ```bash
   python app/main.py
   ```
4. 访问接口：

   * `POST /api/upload` - 上传文档（流式）

   * `POST /api/chat/stream` - 对话问答（流式）

   * `GET /api/history` - 获取会话历史

## 配置说明

环境变量前缀与配置类对应关系：

| 前缀           | 配置类                  | 说明              |
| ------------ | -------------------- | --------------- |
| `WEB_`       | WebConfig            | 服务 host / port  |
| `MODEL_`     | LLMConfig / VMConfig | LLM / VLM 模型配置  |
| `EMBEDDING_` | EmbeddingConfig      | BGE 向量模型配置      |
| `RERANKER_`  | RerankerConfig       | BGE 精排模型配置      |
| `MILVUS_`    | MilvusConfig         | Milvus 向量数据库    |
| `MONGO_`     | MongoDbConfig        | MongoDB         |
| `MINIO_`     | MinioConfig          | MinIO 对象存储      |
| `MINERU_`    | MineruConfig         | MinerU PDF 解析服务 |
| `TAVILY_`    | TavilyConfig         | Tavily 搜索 API   |

## Docker-compose与Mysql初始化

在project_init中有[docker-compose-example.yml](project_init/docker-compose-example.yml)和[sql-example.sql](project_init/sql-example.sql)
1. 在docker-compose中你可以配置密码，将占位符`CHANGE_YOUR_PASSWORD`替换为你的密码。
2. 在sql-example.sql中创建了一个供远程连接的用户dochelper，同样的，你可以将占位符`CHANGE_YOUR_PASSWORD`替换为你的密码
3. 将sql-example.sql改完后放到initdb文件夹下，即可初始化数据库

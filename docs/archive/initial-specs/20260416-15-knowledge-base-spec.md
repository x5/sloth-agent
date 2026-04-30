# 知识库与项目上下文规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

现有记忆存储（Memory spec）存储的是执行产物（Phase 输入/输出），但 Agent **不知道自己在做什么项目**：

1. 没有架构文档、编码规范、项目约定的摄入机制
2. 没有代码库的摘要和索引
3. LLM prompt 中缺少项目特定的上下文和规则
4. 没有"什么信息应该始终在 prompt 中"的定义

Agent 每次执行都要重新"理解"项目，效率低下且容易犯错。

---

## 2. 项目上下文层次

```
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Semantic Context (可选, ChromaDB)              │
│    - 语义检索：根据当前任务检索相关文档                   │
│    - 向量化代码库摘要、架构文档                           │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Project Knowledge (FS, 结构化)                 │
│    - 架构文档、编码规范、API 文档                        │
│    - 项目约定、技术栈信息、团队成员                       │
│    - 历史决策记录（ADR）                                 │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Codebase Summary (FS, 自动生成)                │
│    - 目录结构摘要                                        │
│    - 模块依赖关系                                        │
│    - 关键文件的作用描述                                   │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Pinned Context (FS, 手动配置)                  │
│    - 始终在 prompt 中的信息                              │
│    - 项目名称、技术栈、编码规范要点                       │
│    - Agent 角色和行为约束                                │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Pinned Context（常驻上下文）

### 3.1 配置文件

```yaml
# configs/project_context.yaml
project:
  name: "my-project"
  description: "Brief project description"
  tech_stack:
    - "Python 3.11+"
    - "FastAPI"
    - "PostgreSQL"
    - "React"

  coding_standards:
    - "Use type hints everywhere"
    - "Follow PEP 8"
    - "Write tests for all public functions"
    - "Use TDD workflow"

  conventions:
    - "Module naming: snake_case"
    - "Error handling: raise custom exceptions"
    - "Documentation: docstrings for all public APIs"

  constraints:
    - "Do not modify files outside of src/"
    - "Do not change existing API signatures without approval"
    - "All new features must have tests"

  architecture:
    description: "Brief architecture overview"
    key_components:
      - "API Gateway: FastAPI application"
      - "Database: PostgreSQL with SQLAlchemy ORM"
      - "Auth: JWT tokens"

  important_files:
    - path: "src/core/config.py"
      description: "Configuration module, do not break"
    - path: "src/api/"
      description: "Public API surface, maintain backward compatibility"
```

### 3.2 加载器

```python
class ProjectContext:
    """项目上下文。

    加载项目配置、编码规范、架构信息，
    提供格式化后的 prompt 片段。
    """

    def __init__(self, config_path: str = "configs/project_context.yaml"):
        self.config_path = Path(config_path)
        self.data: dict = {}
        self.pinned_rules: list[str] = []
        self.file_notes: dict[str, str] = {}

    def load(self) -> None:
        """加载项目上下文。"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.data = yaml.safe_load(f) or {}

        self.pinned_rules = (
            self.data.get("coding_standards", [])
            + self.data.get("conventions", [])
            + self.data.get("constraints", [])
        )

        for file_info in self.data.get("important_files", []):
            self.file_notes[file_info["path"]] = file_info["description"]

    def format_for_prompt(self) -> str:
        """格式化为 LLM prompt 片段。"""
        if not self.data:
            return ""

        parts = []

        # 项目信息
        parts.append(f"## Project: {self.data.get('name', 'unknown')}")
        if self.data.get("description"):
            parts.append(self.data["description"])

        # 技术栈
        if self.data.get("tech_stack"):
            parts.append("\n## Tech Stack")
            for tech in self.data["tech_stack"]:
                parts.append(f"- {tech}")

        # 编码规范
        if self.pinned_rules:
            parts.append("\n## Coding Standards")
            parts.append("You MUST follow these rules:")
            for rule in self.pinned_rules:
                parts.append(f"- {rule}")

        # 架构
        if self.data.get("architecture"):
            arch = self.data["architecture"]
            parts.append(f"\n## Architecture")
            parts.append(arch.get("description", ""))
            for comp in arch.get("key_components", []):
                parts.append(f"- {comp}")

        # 重要文件
        if self.file_notes:
            parts.append("\n## Important Files")
            for path, note in self.file_notes.items():
                parts.append(f"- `{path}`: {note}")

        return "\n".join(parts)
```

---

## 4. 代码库摘要

### 4.1 摘要生成器

```python
class CodebaseSummarizer:
    """代码库摘要生成器。

    扫描项目目录，生成结构摘要和模块描述。
    """

    def __init__(self, project_root: str,
                 ignore_patterns: list[str] | None = None):
        self.project_root = Path(project_root)
        self.ignore_patterns = ignore_patterns or [
            "__pycache__", ".git", ".venv", "node_modules",
            "*.pyc", "*.pyo", "*.egg-info",
        ]

    def summarize(self) -> CodebaseSummary:
        """生成代码库摘要。"""
        summary = CodebaseSummary(
            root=str(self.project_root),
            generated_at=time.time(),
        )

        # 目录结构
        summary.directory_tree = self._build_tree()

        # 文件统计
        summary.file_stats = self._count_files()

        # 模块依赖
        summary.module_deps = self._analyze_imports()

        # 关键文件描述（由 LLM 生成）
        summary.file_descriptions = self._describe_key_files()

        return summary

    def _build_tree(self) -> str:
        """生成目录结构树（文本格式）。"""
        lines = []
        for root, dirs, files in os.walk(self.project_root):
            # 过滤忽略的目录
            dirs[:] = [
                d for d in dirs
                if not self._should_ignore(d)
            ]
            level = root.replace(str(self.project_root), "").count(os.sep)
            indent = "  " * level
            lines.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = "  " * (level + 1)
            for f in files:
                if not self._should_ignore(f):
                    lines.append(f"{sub_indent}{f}")
        return "\n".join(lines)

    def _analyze_imports(self) -> dict[str, list[str]]:
        """分析模块导入关系。"""
        deps: dict[str, list[str]] = {}
        for py_file in self.project_root.rglob("*.py"):
            if self._should_ignore(str(py_file)):
                continue

            imports = self._extract_imports(py_file)
            module = str(py_file.relative_to(self.project_root))
            deps[module] = imports

        return deps

    def format_for_prompt(self, summary: CodebaseSummary) -> str:
        """格式化为 LLM prompt 片段。"""
        parts = ["## Codebase Summary"]

        parts.append(f"\nProject root: {summary.root}")
        parts.append(f"Total files: {summary.file_stats.get('total', 0)}")
        parts.append(f"Python files: {summary.file_stats.get('python', 0)}")

        parts.append("\n### Directory Structure")
        parts.append("```\n")
        # 只显示前 50 行
        tree_lines = summary.directory_tree.split("\n")[:50]
        parts.extend(tree_lines)
        if len(tree_lines) >= 50:
            parts.append("... (truncated)")
        parts.append("```")

        return "\n".join(parts)
```

---

## 5. 语义检索（可选，ChromaDB）

```python
class SemanticContextRetriever:
    """语义上下文检索。

    使用 ChromaDB 存储和检索项目文档。
    根据当前任务自动检索相关上下文。
    """

    def __init__(self, chroma_path: str = ".chroma/project_context"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(
            name="project_context",
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_document(self, doc_id: str, content: str,
                         metadata: dict | None = None) -> None:
        """摄入文档。"""
        self.collection.add(
            documents=[content],
            ids=[doc_id],
            metadatas=[metadata or {}],
        )

    def retrieve(self, query: str,
                  max_results: int = 5) -> list[dict]:
        """根据查询检索相关文档。"""
        results = self.collection.query(
            query_texts=[query],
            n_results=max_results,
        )

        return [
            {
                "id": id_,
                "content": doc,
                "metadata": meta,
            }
            for id_, doc, meta in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
            )
        ]

    def format_for_prompt(self, query: str) -> str:
        """检索并格式化为 LLM prompt 片段。"""
        docs = self.retrieve(query)
        if not docs:
            return ""

        parts = ["## Relevant Context"]
        for doc in docs:
            parts.append(f"\n### From: {doc['id']}")
            parts.append(doc["content"][:500])  # 截断
            if len(doc["content"]) > 500:
                parts.append("... (truncated)")

        return "\n".join(parts)
```

---

## 6. 与 LLM Prompt 的集成

```python
class ContextInjector:
    """上下文注入器。

    将项目上下文注入到 LLM prompt 中。
    """

    def __init__(self, project_context: ProjectContext,
                 codebase_summarizer: CodebaseSummarizer,
                 semantic_retriever: SemanticContextRetriever | None = None):
        self.project_ctx = project_context
        self.summarizer = codebase_summarizer
        self.semantic = semantic_retriever

    def build_system_prompt(self, agent_role: str,
                             current_task: str | None = None) -> str:
        """构建系统 prompt。"""
        parts = []

        # Agent 角色
        parts.append(f"You are {agent_role}, an AI development agent.")

        # Pinned context（始终包含）
        pinned = self.project_ctx.format_for_prompt()
        if pinned:
            parts.append(pinned)

        # 代码库摘要
        summary = self.summarizer.summarize()
        codebase = self.summarizer.format_for_prompt(summary)
        if codebase:
            parts.append(codebase)

        # 语义检索（可选，基于当前任务）
        if self.semantic and current_task:
            relevant = self.semantic.format_for_prompt(current_task)
            if relevant:
                parts.append(relevant)

        return "\n\n".join(parts)
```

---

## 7. 技能进化与项目上下文

### 7.1 技能与项目上下文的关联

技能可以引用项目上下文中的信息来做出更好的决策：

```python
class SkillWithContext(Skill):
    """携带项目上下文的技能。"""

    def __init__(self, skill_id: str, context: ProjectContext):
        super().__init__(skill_id)
        self.context = context

    def get_prompt(self) -> str:
        base_prompt = super().get_prompt()
        context_section = self.context.format_for_prompt()

        if context_section:
            return f"{base_prompt}\n\n## Project Context\n{context_section}"
        return base_prompt
```

---

## 8. 配置

```yaml
# configs/project_context.yaml
project:
  name: ""
  description: ""
  tech_stack: []
  coding_standards: []
  conventions: []
  constraints: []
  architecture:
    description: ""
    key_components: []
  important_files: []

codebase_summary:
  enabled: true
  auto_regenerate: true        # 项目文件变化时自动重新生成
  max_tree_lines: 50           # 目录树最大显示行数
  ignore_patterns:             # 忽略的目录/文件
    - "__pycache__"
    - ".git"
    - ".venv"
    - "node_modules"

semantic_context:
  enabled: false               # 默认关闭（需要 ChromaDB）
  chroma_path: ".chroma/project_context"
  auto_ingest: true            # 自动摄入 markdown 文档
  max_results: 5
  max_content_length: 500      # 每条结果最大长度
```

---

## 9. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/context/__init__.py` | 项目上下文模块入口 |
| `src/sloth_agent/context/project_context.py` | ProjectContext 项目上下文加载器 |
| `src/sloth_agent/context/codebase_summary.py` | CodebaseSummarizer 代码库摘要 |
| `src/sloth_agent/context/semantic_retriever.py` | SemanticContextRetriever 语义检索 |
| `src/sloth_agent/context/injector.py` | ContextInjector prompt 注入器 |
| `src/sloth_agent/context/models.py` | 上下文数据模型 |
| `configs/project_context.yaml` | 项目上下文配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*

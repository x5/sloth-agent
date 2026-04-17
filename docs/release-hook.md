# Release Verification Hook

> 版本功能开发完成后，执行以下标准化验证流程后再发布。
> 将此文件作为 `docs/release-hook.md` 保存。

---

## 1. 交叉验证（Cross-Verify）

对比以下文档，确认当前版本的所有功能点均已实现：

1. **架构总览**：`docs/specs/00000000-00-architecture-overview.md` — 查找版本对应章节（如 §14.2 v0.2）
2. **TODO.md**：检查所有版本任务项是否均标记为 `[x]`
3. **Implementation Plan**：对应 plan 文件（如 `docs/plans/20260417-v1-1-implementation-plan.md`）— 确认所有 task 完成
4. **对应 Spec**：每个任务标注的 spec 文件 — 确认状态从"待审批"改为"已实现"

**检查内容：**
- 每个 spec 中列出的文件是否存在于代码库
- 每个 spec 中列出的测试是否存在并覆盖
- 是否存在 TODO.md 中未勾选但 plan 中标记完成的不一致项

---

## 2. 端到端测试（E2E Tests）

```bash
# 运行全量测试套件
uv run pytest tests/ evals/ -v --tb=short

# 确认全部通过，记录通过数量
uv run pytest tests/ evals/ --tb=short -q | tail -1
```

**要求：** 0 failures, 0 errors. 如有失败必须先修复再继续。

---

## 3. 用户旅程测试（User Journey）

模拟真实用户从安装到使用的完整流程：

```bash
# 3.1 验证 CLI 入口
uv run sloth --help

# 3.2 验证版本字符串
uv run sloth status

# 3.3 验证各子命令帮助信息
uv run sloth run --help
uv run sloth chat --help
uv run sloth config --help
uv run sloth init --help
uv run sloth skills
uv run sloth scenarios

# 3.4 验证配置命令
uv run sloth config show
uv run sloth config env
uv run sloth config validate
```

**检查内容：**
- 版本号是否与 `__version__` 一致
- 帮助文本是否清晰无乱码
- 命令是否有合理的错误提示（而非 Python traceback）

---

## 4. 修复所有问题

对步骤 1-3 中发现的问题逐一修复：

- **代码缺失**：补全实现 + 对应测试
- **版本号不一致**：统一更新 `__init__.py` 和 CLI 中硬编码的版本字符串
- **文档不一致**：同步更新 TODO.md、spec、plan、安装指南、README
- **测试失败**：修复 root cause，不跳过测试

每次修复后重新运行步骤 2 确认通过。

---

## 5. 更新文档

### TODO.md
- 更新顶部 "最后更新" 日期和版本状态
- 确认所有版本任务项标记为 `[x]`

### README.md
- 更新版本号
- 更新测试通过数量
- 更新功能清单

### 安装指南
- 更新测试通过数量
- 更新功能清单状态
- 移除"实现中"条目

### 对应 Spec
- 更新状态：`待审批` → `已实现 (vX.X)`

### Implementation Plan
- 更新状态标注
- 更新文件清单（如有新增/删除的文件）

---

## 6. Git 提交与发布

```bash
# 6.1 提交变更
git add README.md TODO.md docs/ src/ tests/
git commit -m "release: vX.X.0 - 版本发布"

# 6.2 推送到 GitHub
git push origin master

# 6.3 创建 Git tag
git tag -a vX.X.0 -m "Sloth Agent vX.X.0 release"

# 6.4 推送 tag
git push origin vX.X.0

# 6.5 创建 GitHub Release
gh release create vX.X.0 --title "Sloth Agent vX.X.0" --notes "Release notes..."
```

---

## 7. 发布后验证

```bash
# 确认 tag 已推送
git ls-remote --tags origin

# 确认 Release 页面可访问
gh release view vX.X.0
```

---

## 执行顺序

```
1. Cross-Verify ─→ 2. E2E Tests ─→ 3. User Journey ─→ 4. Fix Issues
                                                              ↓
5. Update Docs ←←←← (re-run tests if needed) ←←←←←←←←←←←←←←←←
↓
6. Git Commit & Release
↓
7. Post-Release Verify
```

**原则：每一步都必须通过才能进入下一步。测试失败必须修复，不允许跳过。**

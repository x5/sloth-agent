# Frontend CLAUDE (frontend)

本文件定义前端实现与测试硬约束，适用于 `frontend/src/` 下所有变更。

## 编码与质量规则

1. TypeScript
   - `tsconfig.json` 保持 `strict: true`
   - 禁止通过关闭 strict 或大面积 `any` 绕过类型系统

2. ESLint
   - 配置文件固定：`eslint.config.js`
   - 提交前必跑：
     - `npm run lint`
   - 自动修复：
     - `npm run lint:fix`

3. Import 顺序
   - 规则：`import/order`
   - 分组顺序：`builtin -> external -> internal -> parent -> sibling -> index`
   - 组间空行，组内字母序

## 组件单元测试门禁

1. 触发条件
   - 修改或新增组件时，必须新增/更新对应 `*.test.tsx`

2. 最低 DoD
   - 至少覆盖：
     - 正常渲染
     - 关键交互或状态变化
     - 至少一个关键边界（空态/错误态/禁用态）

3. 命令
   - `npm run test -- --run`

4. 文件落位
   - 优先同目录：`ComponentName.test.tsx`
   - 或 `src/tests/components/`（仅在集中式组织更合理时）

## 提交前检查（前端）

1. `npm run lint`
2. `npm run test -- --run`

任一失败，不得合并。

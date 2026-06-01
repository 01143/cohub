# cohub

本地多 CLI Agent 工作流协调工具。让 Claude Code、Codex 等 CLI 通过共享的 `.cohub/` 项目目录协同工作:接力、版本、技能复用、多窗口公告板。

- 纯文件 + 进程,无 daemon、无数据库。
- CLI 升级换 flag 只动 adapter,核心数据不动。
- Windows / macOS / Linux 都跑得动(只在 Windows 11 + PowerShell 实测)。

## 安装

```powershell
# 在仓库根目录
pip install -e .
```

安装后 `cohub` 命令可用。要让接力简报自动生成,设置 Anthropic key:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

没有 key 也能用,只是 `cohub start` 退出时不会自动摘要,而是回退到让你手敲一行(可留空)。

## 五分钟上手

```powershell
# 1. 在任意项目目录初始化
cd D:\我的论文
cohub init
#   引导问:项目名、目标、tags(逗号分隔)、languages
#   生成 .cohub/{handoff,state,active,snapshots}.md + meta.yaml + reviews/

# 2. 启动 Claude Code,自动注入 system prompt
cohub start claude
#   - 读 handoff.md + state.md + 命中 tags 的 ~/.cohub/skills/*.md
#   - 用 `claude --append-system-prompt` 启动
#   - 注册到 .cohub/active.md,后台心跳每 60s 更新
#   - Claude 退出后:从 active.md 移除自己 + 调 Anthropic Haiku 生成 handoff.md

# 3. 查看活跃会话(开多窗口时有用)
cohub status

# 4. 提交快照(git commit + tag snap-NNN)
cohub snap "完成第一阶段"

# 5. 回看历史
cohub rewind         # 列快照,选一个,默认 worktree 只读检出

# 6. 下次再启动 → 上次的 handoff.md 自动接上
cohub start claude
```

## 七个命令(MVP)

| 命令 | 作用 |
|------|------|
| `cohub init` | 在当前目录初始化 `.cohub/`,交互填 meta.yaml |
| `cohub start <cli>` | 注入 handoff+state+skills 启动 CLI,active.md 注册,退出时自动摘要 |
| `cohub status` | 显示当前活跃会话(标 stale) |
| `cohub handoff [--cli claude]` | 手动重跑摘要;找不到 transcript 则提示输入 |
| `cohub snap "<说明>"` | git add -A && commit && tag snap-NNN |
| `cohub rewind` | 交互式列快照,worktree 只读或 hard reset |
| `cohub skill {list|save|edit|use}` | 管理 `~/.cohub/skills/` |
| `cohub review --with <cli>` | **P1 占位**,MVP 未实现 |

## 技能(Skills)

技能存放于 `~/.cohub/skills/<name>.md`,YAML front-matter 声明 tags:

```markdown
---
name: stata-style
tags: [stata, economics]
when: 写 Stata 代码时
---

# Stata 风格
- 一律三线表
- merge 前 sort
```

`cohub init` 时填的项目 `tags`(在 `.cohub/meta.yaml`)与 skill 的 `tags` 取交集,命中的 skill 自动拼到 system prompt 顶部。

强制注入某 skill(不依赖 tags 命中):

```powershell
cohub skill use python-cleanup
# 写入 .cohub/meta.yaml 的 skills.force 字段
```

保存新 skill:

```powershell
cohub skill save my-style --tags python,stata --when "写代码时"
# 然后在终端粘贴正文,Ctrl+Z+Enter (Windows) 或 Ctrl+D (Unix) 结束
```

## Adapter 协议

`~/.cohub/adapters/<name>.py`(可选,优先级高于内置)需实现:

```python
NAME = "claude"
INJECTION_METHOD = "system_prompt_flag"

def build_command(system_prompt: str, project_dir: str) -> list[str]: ...
def find_latest_transcript(project_dir: str) -> Path | None: ...
def parse_transcript(path: Path) -> list[dict] | None: ...  # [{role, content}, ...]
```

内置 `claude` adapter:
- 启动:`claude --append-system-prompt "<text>"`
- transcript:`~/.claude/projects/<encoded-cwd>/*.jsonl`,按 `cwd` 字段匹配,取 mtime 最大者

`codex` adapter 为 P1 占位。

## 目录布局

```
项目目录/
  .cohub/
    handoff.md       上次会话接力简报(自动生成)
    state.md         项目状态(手动维护)
    active.md        活跃会话公告板(实时心跳)
    snapshots.md     快照索引
    reviews/         审查记录(P1)
    meta.yaml        项目元数据(tags 等)

~/.cohub/
  skills/<name>.md   个人技能库
  adapters/<name>.py 自定义 adapter(覆盖内置)
```

## 已知限制 / TODO

- `cohub review` 留作 P1
- codex adapter 留作 P1
- 自动技能提取 `skill extract --from-session` 留作 P1
- transcript watcher 实时更新 `active.md` 的"在做什么"字段留作 P1
- 当多个 CLI 进程同时写 `active.md` 时无文件锁,极端情况下可能丢一条心跳。SPEC 第 1.4 节说"个人工具,不强锁",这是有意为之。

## 测试

```powershell
pytest tests/
```

覆盖 `core.project`、`core.skills`、`core.summarizer`、`core.git_wrap`、`adapters.claude` 关键路径。

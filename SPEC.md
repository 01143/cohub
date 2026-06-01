# cohub 产品规格说明

> 本地多 CLI Agent 工作流协调工具。让 Claude Code、Codex 等 CLI 通过共享的项目状态目录协同,实现接力、审查、版本管理、技能复用、多窗口避让。

## 一、设计哲学(实施前必读)

1. **状态外化**:所有工作状态在磁盘 markdown 文件,与 CLI 工具完全解耦
2. **协议优于工具**:核心是 `.cohub/` 目录协议,CLI 通过 adapter 接入
3. **CLI 升级不失效**:CLI 改了启动方式 → 只改对应 adapter,核心数据不动
4. **个人工具,信任用户**:多窗口冲突不强锁,只告知,用户自己决定

## 二、六个需求 → 六个机制(一对一)

| 需求 | 机制 |
|------|------|
| 长上下文 | 主对话 + 审查对话分工(审查从零起步,只读 diff) |
| 多 CLI 协作 | Adapter 模式,Claude 干活 Codex 审查 |
| 跨 CLI 接力 | handoff.md 摘要(任何 CLI 启动时自动注入) |
| 同 CLI 多窗口 | active.md 实时公告板 + 心跳 |
| 版本管理 | git 包装 + 语义化快照(snap/rewind) |
| 技能复用 | `~/.cohub/skills/` 按 tags 自动注入 |

## 三、目录结构

### 全局
```
~/.cohub/
  skills/              个人技能库
  adapters/            CLI 适配器(claude.py / codex.py 等)
  config.yaml          全局配置(API key 等)
```

### 项目内
```
项目目录/
  .cohub/
    handoff.md         接力简报
    state.md           项目状态
    active.md          活跃会话公告
    snapshots.md       快照索引
    reviews/           审查记录
    meta.yaml          项目元数据(tags 决定注入哪些 skills)
```

## 四、文件 Schema

### `.cohub/handoff.md`
```markdown
# 上次会话摘要(<CLI 名>, <ISO 时间戳>)

## 在做什么
<当前任务>

## 已完成
- ...

## 卡在哪
- ...

## 决策记录
- ...

## 下一步建议
- ...
```

### `.cohub/state.md`
```markdown
# 项目状态(更新于 <时间戳>)

## 目标
<项目目标>

## 当前进度
- ...

## 关键约定
- ...

## 最近改动
- <文件> (<会话标识>, <时间>)
```

### `.cohub/active.md`
```markdown
# 活跃会话(<时间戳>)

[<session_id>] <cli> | PID <pid> | <启动时间> | <在做什么> | 心跳 <时间>
```

### `.cohub/snapshots.md`
```markdown
- [<时间戳>] <说明> (tag: <git_tag>)
```

### `.cohub/meta.yaml`
```yaml
project_name: <名称>
tags: [stata, economics]    # 决定注入哪些 skills
language: [python, stata]
goal: <项目目标>
```

### `~/.cohub/skills/<name>.md`
```markdown
---
name: <技能名>
tags: [tag1, tag2]
when: <什么时候用这个技能>
---

# <技能标题>
<具体内容>
```

## 五、七个命令规格

### `cohub init`
- 在当前目录创建 `.cohub/` 子目录和所有必要文件
- 引导用户填写 meta.yaml(交互式)
- 如果当前不是 git 仓库,询问是否 `git init`

### `cohub start <cli>`
1. 检查项目 `.cohub/` 存在,不存在提示 `cohub init`
2. 读取并显示 `active.md` 中其他活跃会话(让用户知道避开哪)
3. 读取 `handoff.md` + `state.md` + 按 meta.yaml.tags 命中的 skills,拼接成 system prompt
4. 调用对应 adapter 的 `build_command()` 获取启动命令
5. 注册自己到 `active.md`,启动后台心跳线程
6. 启动 CLI 子进程
7. CLI 退出 → 从 active.md 移除自己 → 触发 handoff 摘要

### `cohub status`
- 美化打印 `active.md` 内容

### `cohub handoff`
- 手动触发当前会话摘要
- 通过 adapter 找到最新 transcript,跑摘要器,写到 handoff.md
- 找不到 transcript 时,提示用户手动输入或留空

### `cohub review --with <cli>`
- 启动指定 CLI(默认 codex)
- system prompt 自动包含:`git diff HEAD` + `state.md` + "你是审查员,只读模式"
- 输出意见保存到 `.cohub/reviews/<时间戳>.md`

### `cohub snap "<说明>"`
- `git add -A && git commit -m "<说明>"`
- `git tag snap-NNN`(NNN 自动递增)
- 追加一行到 `snapshots.md`

### `cohub rewind`
- 交互式列出 `snapshots.md`
- 选一个,默认 readonly:`git worktree add _history/<tag> <tag>`
- 或可选 hard reset(需明确确认)

### `cohub skill <subcommand>`
- `save <name>`:从 stdin/编辑器读内容,写到 `~/.cohub/skills/<name>.md`
- `list [--tag <tag>]`:列所有 skills
- `edit <name>`:打开默认编辑器
- `use <name>`:标记下次启动时必注入(写入 `.cohub/meta.yaml` 的 skills.force 字段)

## 六、Adapter 协议

每个 adapter 是 `~/.cohub/adapters/<name>.py`,必须提供:

```python
NAME = "claude"  # 或 "codex"

def build_command(system_prompt: str, project_dir: str) -> list[str]:
    """返回启动 CLI 的命令行 list,system_prompt 已包含 handoff+state+skills"""
    ...

def find_latest_transcript(project_dir: str) -> Path | None:
    """返回最新对话记录文件路径,找不到返回 None"""
    ...

def parse_transcript(path: Path) -> list[dict] | None:
    """解析为 [{role, content}, ...],解析失败返回 None(触发 fallback)"""
    ...

INJECTION_METHOD = "system_prompt_flag"  # 或 "env_var" / "tempfile"
```

### claude.py 参考实现要点
- 启动命令:`claude --append-system-prompt "<内容>"`(或当前版本支持的等价方式)
- transcript 位置:`~/.claude/projects/<hash>/*.jsonl`
- parse:逐行 JSONL,提取 role 和 content

### codex.py
- MVP 可以先写空 stub,P1 再补全

## 七、摘要器逻辑

`core/summarizer.py`:
```python
def summarize(transcript: list[dict]) -> str:
    """用 Anthropic claude-haiku-4-5 生成接力简报。
    Prompt 模板见下方,输出为 handoff.md 格式 markdown。"""
```

Prompt 模板(中文):
```
请阅读以下对话记录,生成接力简报。简报需包含:
- 在做什么(当前任务)
- 已完成(具体动作和产出)
- 卡在哪(未解决的问题)
- 决策记录(选择了什么,弃了什么,为什么)
- 下一步建议

输出格式:严格按 .cohub/handoff.md 的 schema(见 SPEC)
要求:简洁、具体、不要废话。如果某节没有内容,写"无"。
```

**Fallback**:Anthropic API 不可用或 transcript 解析失败 → 在终端提示用户手动输入摘要(可留空,但建议至少一行)。

## 八、技能注入逻辑

启动 `cohub start` 时:
1. 读 `.cohub/meta.yaml` 的 `tags` 字段
2. 扫描 `~/.cohub/skills/*.md` 的 front-matter
3. 取 tags 交集非空的 skills,全部读取
4. 拼接顺序:`[skills 内容] → handoff.md → state.md`
5. 如果 meta.yaml 有 `skills.force` 列表,强制加入这些(不管 tags)

## 九、多窗口心跳

每个 `cohub start` 启动一个后台线程,每 60s:
- 更新自己在 active.md 的"心跳"字段为当前时间
- 检查其他条目,心跳超过 5 分钟的标记为 `(stale)`

主进程退出(CLI 子进程退出):
- 移除 active.md 中自己的条目
- 触发 handoff 摘要

session_id 生成:`<cli>-<时间戳后6位>-<随机3位>`

## 十、技术栈

- Python 3.10+
- 依赖:`click`(CLI)、`anthropic`(摘要,可选)、`pyyaml`、`psutil`
- git 用 `subprocess` 直接调用(不引入 GitPython,减少依赖)
- 不要 daemon,不要数据库
- Windows 优先(用户 OS),但代码用 `pathlib` 跨平台

## 十一、文件结构

```
cohub/
  pyproject.toml
  README.md
  SPEC.md
  src/cohub/
    __init__.py
    cli.py                # click 主入口
    commands/
      __init__.py
      init.py
      start.py
      status.py
      handoff.py
      review.py
      snap.py
      rewind.py
      skill.py
    core/
      __init__.py
      paths.py            # ~/.cohub 等路径
      project.py          # .cohub/ 读写
      adapter.py          # 动态加载 adapter
      summarizer.py       # 摘要器(Anthropic)
      heartbeat.py        # 心跳线程
      git_wrap.py         # git 包装
      skills.py           # skills 匹配和注入
    adapters/
      claude.py           # Claude Code adapter
      codex.py            # 占位
  tests/
    test_project.py
    test_skills.py
    test_summarizer.py    # 含 mock
```

## 十二、MVP 范围(必做)

1. ✅ `cohub init`(交互式建目录)
2. ✅ `cohub start claude`:注入 system prompt + 启动 + active.md 注册 + 心跳 + 退出 cleanup + 触发摘要
3. ✅ `cohub status`
4. ✅ `cohub handoff`(手动摘要,带 fallback)
5. ✅ `cohub snap "..."` + `cohub rewind`
6. ✅ `cohub skill list` + `cohub skill save` + `cohub skill edit`
7. ✅ claude.py adapter(能跑通真实启动)
8. ✅ 技能 tags 自动注入
9. ✅ 多窗口 active.md 注册和提示

## 十三、P1 留作下次

- `cohub review` 完整功能
- `cohub skill extract --from-session`(自动技能提取)
- codex.py adapter 完整实现
- 反幻觉双实例对照
- transcript 自动 watcher(实时更新 active.md "在做什么"字段)

## 十四、注意事项

1. **平台**:Windows 11 + PowerShell。`subprocess` 调用 git 时注意 shell=False
2. **Anthropic API key**:从环境变量 `ANTHROPIC_API_KEY` 读;不存在时 summarizer 优雅降级
3. **Adapter 容错**:transcript 找不到/格式变了 → fallback 到提示用户输入,不要崩溃
4. **错误信息**:中文,清晰具体
5. **README**:写清楚 install / init / 五分钟上手
6. **测试**:`tests/` 至少覆盖 core 模块的关键路径,可以用 mock(摘要器、git)
7. **包安装**:`pip install -e .` 后,`cohub` 命令全局可用

## 十五、最终验收

MVP 完成后,以下场景必须能跑:

```bash
$ cd 某个项目目录
$ cohub init
# 引导填 meta.yaml

$ cohub start claude
# 启动 Claude Code,system prompt 包含空 handoff + 空 state + 命中的 skills
# active.md 出现自己

# 在 Claude 里干一些活,改一些文件
# Ctrl+C / exit 退出 Claude

# wrapper 自动:
#   1. 从 active.md 移除自己
#   2. 找到 transcript,跑摘要,写 handoff.md
#   3. 退出

$ cohub status
# 显示 active.md(应该是空的)

$ cohub snap "完成第一阶段"
# git commit + tag + snapshots.md 追加

$ cohub start claude
# 再次启动,system prompt 包含上次的 handoff.md → 无缝接力

$ cohub skill save my-style
# 输入技能内容,保存到 ~/.cohub/skills/my-style.md
```

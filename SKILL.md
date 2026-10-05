---
name: publish-skills-to-github
description: >-
  把本地 ~/.workbuddy/skills 里的 Agent 技能批量脱敏、生成 README/LICENSE、git init/commit，
  并用「gh 建仓 + SSH 推送」发布为 GitHub 公开仓库，最后生成一个索引仓汇总。
  当用户说「把技能发 GitHub」「批量发布技能仓库」「整理本地技能并推送」时使用。
agent_created: true
---

# 技能批量发布到 GitHub

把散落在本地的技能目录变成一个个干净的公开仓库。核心是三件事：**脱敏**、**自动补全仓库要素**、**绕开被墙的推送通道**。

## 何时使用

- 用户要把本地技能分享出去 / 发布到 GitHub
- 需要批量给多个技能生成 README、LICENSE、.gitignore 并建仓
- 在本机推 GitHub 失败（https reset、device flow token 无权限）

## 前置条件

| 项 | 位置 | 说明 |
|---|---|---|
| gh CLI | `C:\Users\<you>\.workbuddy\bin\gh\bin\gh.exe` | winget 常装不上，手动下 zip 解压即可 |
| SSH key | `~/.ssh/id_ed25519_github` | 公钥加到 `github.com/settings/ssh/new` |
| SSH config | `~/.ssh/config` | 必须把 github.com 指到 443 端口 |
| PAT | `~/.workbuddy/secrets/github_pat` | 需要 `repo` scope，仅用于建仓；用完让用户 revoke |

凭证已持久化两处，发布前不用再问用户要 token：

1. **gh keyring**（主）：`gh auth login --with-token` 后 token 存进 Windows 凭据管理器，`gh auth status` 可查
2. **明文备份**：`~/.workbuddy/secrets/github_pat`（41 字节纯 token）。若 gh 登录态失效：

```bash
bash scripts/gh_login_from_file.sh        # 从备份文件恢复 gh 登录
```

凭证安全：

- token 只存这两处，**不得写进任何仓库文件、README、脚本、memory**
- 不要对该文件做 `icacls /inheritance:r` + `/grant:r`：非管理员会话缺少 `SeSecurityPrivilege`，会把 ACL 清空成连 owner 都读不了。要收紧就用 `icacls <file> /reset` 回退
- 长期不用时提醒用户 revoke：`https://github.com/settings/tokens`

`~/.ssh/config` 内容：

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_ed25519_github
```

## 流程

### 1. 选候选

扫描 `~/.workbuddy/skills`，按三个维度筛：

- **体量**：>5MB 的（如第三方大包）单独问用户，不默认推
- **是否已合并**：已并入其它技能的（如 disk-cleaner 已并入 file-organizer）跳过
- **敏感内容**：含真实联系人名、城市/单位、本机绝对路径、token 的先标记

### 2. 脱敏 + 生成仓库要素

```bash
python scripts/prepare_skill_repo.py --skill <name> [--skill <name2> ...] \
    --dest <工作区目录> --template <含 LICENSE/.gitignore 的模板目录>
```

每步做：

1. 复制文本文件并替换：所有具体的本机用户目录路径 → `C:\Users\<you>`，IPv4 → `<ip>`
2. 从 `SKILL.md` frontmatter 取 `description` 作为 README 摘要（注意 `>-` 折叠 YAML，多行要拼接，否则读出来是空的）
3. README = 摘要 + 安装命令 + 目录树
4. 从模板目录拷 `LICENSE`（MIT）、`.gitignore`
5. `git init` + `add -A` + `commit`

跑完**必须再看一眼敏感命中行** —— 关键词扫描（`token` / `config.json` / `xlsx` / `password`）误报率很高，肉眼确认才准。

### 3. 建仓 + 推送

```bash
bash scripts/publish_repos.sh <工作区目录> <owner> <repo1> [repo2 ...]
```

关键约束（本机实测）：

- **建仓用 PAT + gh**：`gh repo create <name> --public`。`--push` 别用，https 通道在这台机器会 `Connection was reset`
- **推送用 SSH**：remote 必须是 `git@github.com:<owner>/<name>.git`
- 推送命令用 `git push -u origin HEAD:main`，之后 `git branch -m master main` 把本地分支对齐
- device flow（`gh auth login -w`）拿到的 token 属于 GitHub App（Copilot Plugin），scope 为空，建仓报 `Resource not accessible by integration` —— **不要走这条路**

### 4. 补仓库描述 + 建索引仓

`gh repo edit <owner>/<name> --description "..."` 给每个仓补一句话，否则仓库列表页一片空白。

最后建一个 `agent-skills` 索引仓：README 表格列出全部仓库（链接 + 用途 + 一句话说明）+ 单个/批量安装命令 + 约定。

## 安全红线

- 发布前对每个仓库跑敏感扫描；真实人名、城市、单位、本机路径不得入库
- 脱敏模板兜不住的东西（微信联系人昵称等）**不要推**，直接排除并告知用户
- PAT 用完提醒用户立刻 revoke；不要写进任何文件

## 常见故障

| 现象 | 原因 | 解法 |
|---|---|---|
| `winget install GitHub.cli` 失败 `0x80072efd` | github.com 下载域名不通 | 手动下载 release zip，用 `curl -4 -C -` 后台续传 |
| `curl https://github.com` 超时，但 `api.github.com` 通 | DNS 解析到不可达 IP | 建仓走 api（gh），推送走 SSH |
| `gh repo create` 报权限不足 | token scope 为空 / 属于 GitHub App | 换 classic PAT（勾 repo） |
| push 报 `Connection was reset` | https 通道不通 | 改 SSH remote |
| README 摘要为空 | frontmatter 用了 `>-` 折叠块 | 手工拼接后续缩进行 |

## 脚本

- `scripts/prepare_skill_repo.py` —— 复制 + 脱敏 + README/LICENSE + git commit
- `scripts/publish_repos.sh` —— gh 建仓 + SSH 推送 + 分支改名
- `scripts/gh_login_from_file.sh` —— 从本地 token 文件恢复 gh 登录

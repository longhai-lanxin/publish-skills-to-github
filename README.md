# publish-skills-to-github

把本地 ~/.workbuddy/skills 里的 Agent 技能批量脱敏、生成 README/LICENSE、git init/commit，并用「gh 建仓 + SSH 推送」发布为 GitHub 公开仓库，最后生成一个索引仓汇总。当用户说「把技能发 GitHub」「批量发布技能仓库」「整理本地技能并推送」时使用。

## Install

```bash
git clone https://github.com/longhai-lanxin/publish-skills-to-github.git ~/.workbuddy/skills/publish-skills-to-github
```

## Contents

```
publish-skills-to-github/
  README.md
  SKILL.md
  scripts/
    gh_login_from_file.sh
    prepare_skill_repo.py
    publish_repos.sh
```

## Usage

See [`SKILL.md`](SKILL.md) - that file is the entry point the agent reads.

## License

MIT

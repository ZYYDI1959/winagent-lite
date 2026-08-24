# GitHub 发布清单（P4-11）

代码侧已 100% 就绪（9+ commit，工作区干净）。只差你的三样东西：

## 你要提供的

1. **GitHub 用户名**
2. **GitHub 邮箱**（或用 GitHub 提供的 noreply 邮箱：`<用户名>@users.noreply.github.com`）
3. **PAT**（Personal Access Token）：github.com → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → 勾选本仓库的 Contents: Read and write

## 我会自动执行的（你给完上面三样后说"发布"即可）

```bash
# 1. 改 commit 署名（9 个 commit 全部重写为你的身份）
git config user.name "<你的用户名>"
git config user.email "<你的邮箱>"
git rebase -r --root --exec 'git commit --amend --no-edit --reset-author'

# 2. 建仓库并推送（走 api.github.com 直连 + ghproxy 兜底）
curl -X POST https://api.github.com/user/repos -d '{"name":"winagent-lite","private":false}'
git remote add origin https://<TOKEN>@github.com/<用户名>/winagent-lite.git
git push -u origin main
```

## 发布前终检（我会跑）

- [ ] `pip install -e .` 在干净 venv 里通过
- [ ] `winagent bench --tasks taskmgr_open --runs 1` 冒烟通过
- [ ] README 图片/链接路径正确（docs/demo.gif、docs/baseline_v0.2.md）
- [ ] 敏感信息扫描：config.yaml 未入库 ✓、runs/ 未入库 ✓、无 token 硬编码 ✓

## 网络备注

本机 api.github.com 可直连；若 push 走 https 被断，用 ghproxy.net 镜像前缀兜底。

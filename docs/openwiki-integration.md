# OpenWiki 的独立存储与维护

## 存储和工作副本

本仓库的 `code-wiki/postgres/openwiki/` 是代码 Wiki 的规范副本，保存页面、Claims 和已完成更新的持久化元数据。相邻的 `source.json` 记录 PostgreSQL 源码 URL、源码 commit、OpenWiki 验证工具标识、导出时间和文件校验和。历史版本通过 Git 保存。

PostgreSQL checkout 的 `openwiki/` 是恢复出来的工作副本。OpenWiki 0.7.1 的代码模式和 MCP 检索仍以源码仓库根目录为入口；桥接脚本保留这个约定，不通过软链接或修改 OpenWiki 包绕过路径检查。两份文件只有一个维护流程，不分别编辑。

首次迁移保留原始 Wiki 字节及生成时间，不把复制文件描述成重新验证了 PostgreSQL 机制。页面中旧的部署说明反映生成时的状态；当前存储和维护方式以本文为准。

## 团队成员首次使用

1. 克隆本知识仓库及 PostgreSQL 源码。
2. 查看 [source.json](../code-wiki/postgres/source.json) 中的 `source_commit`，确保源码仓库包含这个 commit。复现文档所描述的实现时使用该 commit；研究其他版本时重新核实重要结论。
3. 复制 `knowledge.example.json` 为 `knowledge.local.json`，填写本机源码路径。
4. 从本仓库根目录运行：

```sh
python3 scripts/wiki_bridge.py restore
python3 scripts/wiki_bridge.py status
```

也可用 `--source /absolute/path/to/postgres` 覆盖本机配置。脚本不会切换源码分支、拉取源码、调用模型或推送 Git。

已有工作副本包含未发布修改时，恢复会停止；应先保存并核实这些修改。恢复替换旧副本时会输出备份位置。备份保留在同一父目录的 `.wiki-backup-*`，确认不再需要后再清理；将这个目录模式排除于源码 Git 和 OpenWiki 扫描之外。

## 日常更新

先同步知识仓库并确认没有其他维护者，再恢复工作副本。需要描述新源码时，由开发者明确选择源码 commit；桥接脚本不自动跟踪上游最新分支。

```sh
python3 scripts/wiki_bridge.py restore
```

在源码 checkout 中，让 Codex 或 OpenCode 按 OpenWiki 的 begin、页面任务、submit、finish 生命周期更新 Wiki；也可在已配置模型 provider 的环境中执行原生 `openwiki code --update --print`。一次只让一个宿主维护。发生中断时恢复原运行，不发布半成品。

完成后回到知识仓库：

```sh
python3 scripts/wiki_bridge.py publish
python3 scripts/wiki_bridge.py status
git diff --stat -- code-wiki/postgres
```

检查差异后，按授权提交和推送 `code-wiki/postgres`。`publish` 只复制本地文件，不等于 Git 提交或远程发布。首次迁移使用的 `--bootstrap` 仅适用于规范副本尚不存在时，不能覆盖已有快照。

## 发布检查与冲突

桥接脚本要求无活动运行、上次更新完成、页面字节哈希与 Claims 和页面清单一致、源码 HEAD 与完成记录一致、源码无已跟踪的未提交修改，以及引用的证据文件受源码 Git 管理。未知文件和软链接会使操作停止；`.DS_Store` 和 Apple 资源旁车文件不导出。

脚本在忽略的 `.wiki-bridge/` 中记录每个 checkout 恢复时的基线。其他工作副本已经发布新版本时，旧基线不能覆盖新快照。请先保存各自工作，再按新规范版本重做或协调更新；没有强制覆盖开关。桥接锁只覆盖传输操作，整个模型生成过程仍需维护者协调单写。

脚本检查结构和版本一致性，不证明文字语义正确，也不重新运行 OpenWiki 的证据解析器。维护时仍必须完成 OpenWiki 生命周期，并针对重要行为检查源码和测试。

## 阅读与检索

直接浏览 [Wiki 入口](../code-wiki/postgres/openwiki/quickstart.md) 即可阅读。`source.json` 中的源码 URL 和 commit 用于把 `repo://src/...` 证据解释为对应版本的源码，不能把这些路径解释为本知识仓库中的文件。

使用 OpenWiki MCP 时，把 `root` 指向已恢复 Wiki 的 PostgreSQL checkout，继续使用 `openwiki_search` 和 `openwiki_read`；不要把 root 改成知识仓库。`status` 会同时显示当前源码 HEAD 与文档源码 commit，帮助识别版本差异。

跨记录检索可直接运行：

```sh
rg -n -i 'ReplicationSlotRelease|ephemeral|复制槽' records topics code-wiki/postgres/openwiki
```

MCP 检索仍只覆盖它支持的 Wiki 页面，不会自动索引 `records/`。本次迁移没有启用统一索引、CI、定时任务或历史材料导入。

## 验证桥接脚本

脚本仅使用 Python 标准库和 Git。运行隔离测试：

```sh
python3 -m unittest discover -s tests -v
```

测试使用临时仓库，覆盖恢复往返、冲突保护、未完成运行、源码漂移、页内容被手工改动、软链接拒绝以及备份保留。

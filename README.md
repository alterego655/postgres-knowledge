# PostgreSQL 开发知识库

这个仓库保存 PostgreSQL 开发过程中可复用的经验：bug 的触发条件与根因、实验结果、设计决策，以及邮件讨论中的论据和结论。每条记录应说明适用版本、证据来源和仍未确认的部分，帮助下一次调查少走弯路。

本仓库同时保存代码 Wiki 的规范副本、调查记录和主题导航。OpenWiki 在 PostgreSQL checkout 中维护工作副本，完成更新后通过桥接脚本发布回本仓库；源码、引用和 Claims 仍按原有语义解析。

## 从哪里开始

- [PostgreSQL 代码 Wiki](code-wiki/postgres/openwiki/quickstart.md)：复制、WAL、I/O 和性能机制。
- [代码 Wiki 源码版本](code-wiki/postgres/source.json)：对应源码 commit、生成工具及文件校验和。
- [主题导航](topics/README.md)：按复制、WAL 与恢复、I/O、性能查找经验。
- [经验记录](records/)：一个可复用的问题、根因或决策对应一条记录。
- [记录规范](docs/record-format.md)：何时新增、何时更新，以及如何记录验证状态。
- [记录模板](templates/record.md)：创建记录的起点，模板本身不是已验证案例。
- [OpenWiki 接入说明](docs/openwiki-integration.md)：源码 Wiki 与经验库的分工及检索边界。
- [证据目录](evidence/)：保存必要的复现脚本、补丁、原文摘录和实验输出。

仓库初始化时尚未导入历史对话、邮件或 bug 案例，也未启用定时任务。

## 如何保存经验

在开发对话中明确请求，例如：

> 使用 pg-knowledge-capture，把这次排查保存到知识库，保留复现条件、失败尝试、验证结果和适用版本。

助手应先检索旧记录，再决定新增、补充或替代；保存后更新主题入口，并用一个真实问题尝试找回记录。普通代码问答不自动写入知识库。

从仓库根目录可以直接检索，例如：

```sh
rg -n -i 'ReplicationSlotRelease|ephemeral|复制槽' records topics
```

没有匹配项只表示尚未记录或检索词未命中，不代表 PostgreSQL 不存在相关问题。

## 如何管理修改

Markdown 保存当前知识，Git 保存其演变。完成一组记录修改后，检查差异，仅暂存本次相关文件，再提交。普通保存请求不会自动提交或推送；需要用户明确要求或既定工作流程授权。

新增证据推翻旧结论时，更新当前结论并保留简短的变化理由。提交历史不能替代正文中的适用范围和失效说明。

多人使用时，通过分支和 PR 审核结论与证据；发现其他人的未提交修改时不要覆盖。GitHub 私有仓库提供远程副本，后续邀请成员或修改可见性应单独决定。

## 本地关联配置

复制 [knowledge.example.json](knowledge.example.json) 为 `knowledge.local.json`，填入本机 PostgreSQL 仓库的绝对路径。这个文件被 Git 忽略，不会把个人目录结构提交给其他成员。

桥接脚本读取该配置来定位对应 checkout。运行 `python3 scripts/wiki_bridge.py status` 查看规范副本和工作副本是否一致；完整的恢复、维护与发布步骤见 [OpenWiki 接入说明](docs/openwiki-integration.md)。该流程没有启用后台同步、定时任务或统一索引。

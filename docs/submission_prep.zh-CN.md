# 投稿准备

英文原文：[Submission Preparation](./submission_prep.md)。

这份说明是公开审查和投稿规划用的操作材料，不属于 Text Graphics Agent 的技术贡献。

## 作者联系方式

- 作者：Lijie Wang
- 身份：独立研究者
- 联系邮箱：<wanglijie100@gmail.com>
- 公开 artifact：<https://github.com/910636071/text-graphics-agent>

## 当前论文定位

- 工作标题："Text Graphics Agent: A Semantic Firewall for Disposable
  Child-Agent Workflows"
- 论文类型：artifact paper / technical note
- 暂定 arXiv 主分类：`cs.AI`
- 投稿时可核对的 cross-list：`cs.CR`（安全边界）和 `cs.SE`（软件工程 artifact）

最终分类应以 arXiv 实际投稿流程为准。论文不应声称 AGI、彻底消除幻觉、彻底防止
prompt injection，或拥有宽泛经验优势。

## arXiv 推荐说明

arXiv 要求作者在第一次向 arXiv 或新分类投稿前获得 endorsement。流程从正式提交论文
时开始；如果需要 endorsement，arXiv 会通过邮件发送 request link 或 code。

根据 arXiv 2026 年 1 月 21 日的政策更新，机构邮箱本身已经不足以作为新作者的唯一
endorsement 条件。新投稿者通常需要满足以下任一条件：

- 机构邮箱 + 在相关 endorsement domain 中已有 arXiv 论文作者身份；
- 或获得同一 endorsement domain 中已建立 arXiv 作者的个人推荐。

endorsement 不是同行评审。请求重点应是：论文是否属于目标 arXiv 分类范围，是否适合
进入 arXiv 投稿流程。

官方参考：

- <https://info.arxiv.org/help/endorsement.html>
- <https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/>

## 材料清单

- 仓库：<https://github.com/910636071/text-graphics-agent>
- 论文草稿：[paper_draft.zh-CN.md](./paper_draft.zh-CN.md)
- 英文论文草稿：[paper_draft.md](./paper_draft.md)
- Live API smoke 报告：[live_api_benchmark_20260703.zh-CN.md](./live_api_benchmark_20260703.zh-CN.md)
- 引用元数据：[../CITATION.cff](../CITATION.cff)
- 公开发布清单：[public_launch_checklist.zh-CN.md](./public_launch_checklist.zh-CN.md)

## 推荐请求模板

主题：arXiv endorsement request for a cs.AI artifact paper

您好 [姓名]：

我是独立研究者 Lijie Wang，正在准备第一次向 arXiv 的 `cs.AI` 分类提交论文。论文题目是
"Text Graphics Agent: A Semantic Firewall for Disposable Child-Agent
Workflows"。这是一篇短的 artifact paper / technical note。

这项工作研究一种母子 agent 工作流：原始用户语义先被编译为带范围的 `TaskSpec`，一次性
子 agent 只提交结构化 proposal，最终由确定性约束裁决 proposal 是否能成为 accepted
state。公开 artifact 包含零依赖 Python 原型、双语文档、确定性 benchmark 场景和真实模型
smoke 报告。

我理解 arXiv endorsement 不是同行评审，也不表示 endorser 同意论文的全部结论。我希望请您
判断这项工作是否属于该 arXiv 分类范围，并是否适合进入 arXiv 投稿流程。

材料如下：

- 仓库：<https://github.com/910636071/text-graphics-agent>
- 论文草稿：[paper URL or attachment]
- arXiv endorsement request：[开始 arXiv submission 后，如果系统要求 endorsement，使用
  arXiv 提供的 request link 或 endorsement code]

谢谢您的时间。

Lijie Wang  
<wanglijie100@gmail.com>

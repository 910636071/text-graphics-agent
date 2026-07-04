# 公开来源 artifact 记录，2026-07-04

英文原文：[Public Provenance Artifacts](./provenance_artifacts_20260704.md)。

这份记录整理作者在 constraint-checked state-record 研究方向上的公开 GitHub artifact
链条。它不是法律意义上的优先权主张，也不能证明相对于所有先行工作的 novelty。它的用途更窄：
给 reviewer 一个带公开时间戳的仓库链条，说明这条研究线早于当前 Text Graphics Agent release
artifact。

仓库 metadata 于 2026-07-04 通过公开 GitHub API 核对。

| 仓库 | 公开 created_at | 本次观察到的 latest pushed_at | 在研究链条中的角色 |
| --- | --- | --- | --- |
| [`rgbd-safe-minimal`](https://github.com/910636071/rgbd-safe-minimal) | 2026-05-25T07:44:07Z | 2026-05-27T14:20:03Z | 最早的 clean-room 最小符号管线，作为 seed artifact 归档保留。 |
| [`constraint-checked-state-records`](https://github.com/910636071/constraint-checked-state-records) | 2026-05-25T14:58:14Z | 2026-05-27T14:18:33Z | 当前 normalized records、有限约束和 checked-state reporting 的外部评审 artifact。 |
| [`checked-state-benchmark`](https://github.com/910636071/checked-state-benchmark) | 2026-05-26T15:16:42Z | 2026-05-27T14:10:55Z | finite checked-state evaluation 的合成 benchmark scaffold。 |

## 解释

这三个仓库适合作为连续性证据：

1. `rgbd-safe-minimal` 保留最早的 clean-room 符号管线。
2. `constraint-checked-state-records` 将这个 seed 收束为 checked-record 评审 artifact。
3. `checked-state-benchmark` 将同一接口变成下游合成评测脚手架。
4. Text Graphics Agent 把同一个 record boundary 适配到 disposable child-agent 工作流。

正确的公开说法是：

> 作者在 2026 年 5 月已有公开带时间戳的 artifact，记录了后来被 Text Graphics Agent
> 适配的 checked-record 研究线。

不要把时间戳证据写成“排除了所有独立先行工作”，也不要把它单独写成法律意义上的
优先权结论。

## 引用方式

在项目文档或论文草稿中引用这条链路时，应把这些仓库当作作者 artifact 引用，而不是
peer-reviewed papers。它们应和引用审计、相邻工作引用一起使用，不能替代 prior-art review。

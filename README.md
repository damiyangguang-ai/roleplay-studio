# roleplay-studio

[![CI](https://github.com/damiyangguang-ai/roleplay-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/damiyangguang-ai/roleplay-studio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

成年角色虚构创作的**设定工程**工具：角色卡、关系状态、剧情连续性。

它解决的是"长剧情里人设崩、关系跳跃、模型忘了前文"，**不是**"让模型不再拒绝"。

## 是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 结构化保存角色设定（年龄、语气、边界、偏好） | 不生成任何正文 |
| 记录关系阶段、亲密度、未解决张力 | 不调用任何模型 API |
| 把已发生事件记成时间线 | 不改任何宿主配置 |
| 一键导出可粘贴的"设定摘要" | **不绕过任何内容过滤** |

角色年龄是**数据层硬约束**（`>= 18`），不是文档约定。

## 快速开始

```bash
python -m rpstudio demo --file demo.json
python -m rpstudio character list --file demo.json
python -m rpstudio context --file demo.json --characters 林夏,周砚
```

## 命令

| 命令 | 作用 |
|---|---|
| `init` | 建空工程 |
| `demo` | 建示例工程（两个成年角色） |
| `character add NAME --age N` | 加角色（`--age` 必填且 >= 18） |
| `relationship A B --stage --intimacy 0-5` | 设关系现状 |
| `event add TITLE --participants A,B` | 追加时间线事件 |
| `context --characters A,B` | 导出可粘贴摘要 |
| `bible --out x.md` | 导出完整设定圣经 |
| `validate` | 校验一致性 |

## 测试

```bash
python -m unittest discover -s tests -v
```

## 许可

MIT

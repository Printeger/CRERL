# CRE Demo 汇报材料

本目录提供一套更适合中文汇报的 HTML 格式 PPT，以及逐页讲稿。

## 文件说明

- `cre_three_demo_report.html`
  - 详细版 HTML deck
  - 浏览器直接打开即可翻页
  - 支持方向键翻页、`N` 键切换讲稿面板、浏览器打印为 PDF
- `cre_three_demo_report_notes.md`
  - 与 deck 一一对应的逐页讲稿
  - 适合打印、演讲排练或发给讲解同学
- `build_cre_demo_report.py`
  - deck 与讲稿的生成脚本
  - 方便后续根据 demo 数据继续刷新内容

## 重新生成

在仓库根目录执行：

```bash
python3 cre-demos/presentations/build_cre_demo_report.py
```

## 汇报建议

1. 先讲第 1 至 3 页，把三类问题和共同实验语法讲清楚。
2. 再按 Demo 1、Demo 2、Demo 3 的顺序讲设计与结果。
3. 最后用交叉对比页和支撑材料页收束，进入问答。

## 与旧版 deck 的关系

- `doc/cre_v1_three_demo_deck.html`
  - 英文、轻量、适合快速总览
- `cre-demos/presentations/cre_three_demo_report.html`
  - 中文、细节更完整、适合正式汇报与答辩支撑

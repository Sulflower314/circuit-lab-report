# 大学电路实验报告 Skill

根据实验数据、照片和基本原理，制作中文 LaTeX 电路实验报告。随附《电路理论基础实验》（2023 年 9 月）PDF、章节索引和资料库工具，调用时可按实验名称自动查阅，不需要每次重新上传讲义。

## 报告约定

正文固定八章：实验目的、实验原理及电路图、实验仪表设备、实验内容及步骤、实验结果、实验结果分析、思考题、实验心得。

- 正文目标 **15—20 页**，材料不足时保留真实篇幅。
- 电路图优先使用现成图、讲义原图或手绘扫描，不默认重画。
- 处理实验表格与波形，区分实测、理论、拟合和仿真。
- 正文直接陈述原理和结果，减少防御性说明、AI 自述及写作过程解释。
- 提供数据绘图、LaTeX 编译和基础检查工具；报告交付前逐页检查 PDF。

## 安装

克隆或下载此仓库，将其中的 **`circuit-lab-report` 文件夹整体复制**到 Codex 的 `skills` 目录：默认是用户目录下的 `.codex/skills/`；如设置了 `CODEX_HOME`，则使用该目录下的 `skills/`。

保留文件夹内的 `library/`，它包含讲义和自动查阅所需的索引。安装后在 Codex 中调用：

```text
$circuit-lab-report
请根据这些实验数据和照片，完成实验九的报告。
```

skill 会先查用户本次材料和当前项目资料库；资料不足时再查随附讲义的相关实验与仪器页。不会把讲义的设定或空白表当成实测结果。

## 运行环境

Python 3.10 或更新版本：

```text
python -m pip install -r requirements.txt
```

报告编译使用 XeLaTeX，主要宏包为 ctex、amsmath、graphicx、booktabs、tabularx、longtable、siunitx v3、caption 和 fancyhdr。直接插入已有电路图无需 CircuitikZ；确需重绘时再加载。

## 资料库

[资料库入口](circuit-lab-report/library/索引.md) · [18 个实验与 5 类仪器的页码索引](circuit-lab-report/library/目录/circuit-theory-202309.md)

随附讲义由江波、郑子生编，中山大学电子与信息工程实验教学中心，2023 年 9 月。来源信息和文件哈希保存在资料库中，PDF 保持原样。索引同时标明 PDF 实际页序和书内页码。

按章节读取示例（在仓库根目录执行）：

```text
python -X utf8 circuit-lab-report/library/工具/pdf_library.py read circuit-theory-202309 --section experiment-09
```

管理其他课程资料时，可将 `pdf_library.py` 复制到项目的 `资料库/工具/` 目录，再执行：

```text
python -X utf8 资料库/工具/pdf_library.py add "课程讲义.pdf" --id course-handbook --title "课程实验讲义"
```

不同版本使用不同编号。工具保留原件、生成检索文本和书签索引，并拒绝用不同内容覆盖同一来源编号。

## 仓库内容

```text
circuit-lab-report/
  SKILL.md                 工作流程与调用入口
  agents/                  Codex 显示信息
  assets/                  八章 LaTeX 模板与可选电路示例
  references/              写作、数据分析、排版及查阅规范
  scripts/                 绘图、编译及基础检查工具
  library/                 课程 PDF、索引、检索文本和资料库工具
```

个人读数、照片、报告输出与临时验证文件不属于仓库内容。工具检查不能代替对实验数据、电路和最终 PDF 的核对。

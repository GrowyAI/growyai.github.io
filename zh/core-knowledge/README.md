# Core Knowledge 知识点速查

把 2023 版 Core Knowledge Sequence（Preschool 与 K–8）的两份 PDF，整理成一个按「年级 → 学科 → 主题 / 子主题 → 类型」分层的离线静态速查工具。

## 入口

- `index.html`：知识点速查器（筛选、搜索、收藏、中英对照）
- `roadmap.html`：大纲首页（年级 × 学科矩阵、主题预览）
- `attribution.html`：版权与署名说明

均可直接用浏览器打开，无需构建或联网。

## 目录说明

- `data/knowledge-inline.js`：页面运行时使用的内联数据（禁止直接改）
- `data/topic-zh-inline.js`：374 个主题的中文映射
- `data/knowledge.json`：结构化数据源（7,053 条，含中文翻译、来源页码、emoji、作品搜索链接）
- `data/knowledge.csv` / `data/knowledge.xlsx`：可下载表格视图
- `data/questions.csv`：单独抽出的具体问题 / 对话条目
- `scripts/add_emojis.py`：按具体名词 / 动作生成 emoji 提示
- `scripts/add_work_links.py`：为引号中的具体作品 / 名称生成 Google 搜索链接
- `scripts/build_topic_zh.py`：按固定顺序重建主题中文映射
- `scripts/export_tables.py`：从 JSON 重新生成 CSV / XLSX / 内联 JS

> 源 PDF、`data/raw/` 全文提取稿和从 PDF 抠出的图片均已放在本地目录，但被 `.gitignore` 排除，**不会提交到公开仓库**，以避免版权风险。

## 本地非公开文件

以下路径只用于本地重建，已被仓库根目录 `.gitignore` 忽略：

- `source/`：两份原始 PDF
- `data/raw/`：PDF 全文提取稿
- `assets/images/`：从 PDF 提取的图片
- `data/images*.json` / `data/images-inline.js` / `data/item-images*.json` / `data/item-images-inline.js`：图片映射与页面图片索引
- `translations/`：翻译批次中间产物（如重新生成时会出现）
- `data/knowledge-before-*.json`：旧版本备份

公开页面不加载这些文件。脚本 `extract_images.py`、`inspect_pdf_images.py`、`match_images_to_items.py` 现在从 `source/` 读取 PDF。

## 重新生成派生文件

在目录下按需运行：

```bash
python scripts/export_tables.py
python scripts/build_topic_zh.py
python scripts/add_emojis.py && python scripts/export_tables.py
python scripts/add_work_links.py && python scripts/export_tables.py
```

`add_emojis.py` 会设置 `MAX_FREQUENCY = 100`，出现次数达到或超过 100 的 emoji 会被整类移除，避免重复刷屏。

`add_work_links.py` 只识别英文正文中引号内的具体作品 / 名称，并排除章节标题和常见课堂短语；每条最多生成一个 Google 搜索链接，写入 `work` 与 `link` 字段。它不抓取、不复制第三方内容，搜索结果版权归原方所有。

翻译批次相关脚本（如 `make_translation_chunks.py`、`merge_translations.py`）需要先在本地生成 `translations/` 目录；该目录也被忽略，不会进入提交。

## 许可

- 本目录中的**数据、中文翻译、派生表格**：CC BY-NC-SA 4.0，详见 [`LICENSE-CONTENT`](LICENSE-CONTENT) 和 [`attribution.html`](attribution.html)。
- 本目录中的 HTML / CSS / JS 代码：沿用 Growy 仓库根目录的 CC BY-NC 4.0。
- 原始内容来自 Core Knowledge® Foundation；本站非官方，未经其认可或背书。

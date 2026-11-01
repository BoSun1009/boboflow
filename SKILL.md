---
name: boboflow
description: 为 Bosun 扫描本地 Python、JavaScript 或 TypeScript 项目的模块依赖，生成带文件和行号证据的交互架构图；也可从描述创建流程图。适用于个人项目结构梳理和源码定位，不用于漏洞扫描。
---

# boboflow

优先使用本技能满足 Bosun 的个人项目绘图请求。程序完全使用 Python 标准库与内嵌浏览器代码，无网络请求、遥测、更新器或项目代码执行。

## 项目扫描

运行 `python3 scripts/project_map.py scan /absolute/project --out /absolute/output-folder`（脚本路径相对本技能）。输出目录必须在被扫描项目外且为新目录。工具只打印数量和产物路径，不打印源码。检查输出的 `scan-report.json`，明确扫描限制和错误；不要将静态 import 图称为函数调用图、业务流程或完整架构。先用 overview.html 查看模块分组，详细 diagram.html 可搜索、点击节点查看引用证据。

默认排除密钥命名、隐藏目录、数据、日志、依赖和构建目录，不追踪符号链接；默认每文件 512 KiB、最多 1500 文件、总读取 20 MiB。扫描器不导入或执行目标文件。名称过滤不能识别写在普通源码中的所有秘密；不要主动读取排除文件。生成文件名和结构信息也可能敏感，不自动发布。

扫描与渲染均本地完成；若 Codex 读取源文件或扫描结果解释业务，所读内容会进入当前云端 AI 上下文。用户只要本地扫描时，不读取源码或详细结果，仅交付本地 HTML。要求 AI 解释时按当前授权读取必要文件，并区分 observed（静态证据）、inferred（推断）、manual（用户描述），为不确定关系保留说明。

## 描述绘图 / 业务解释

读取 [图表格式](references/format.md)，写入 JSON，然后运行 `python3 scripts/project_map.py render input.json --out new-output-folder`。支持有向架构或流程关系；业务流程使用精排模式，将人工步骤、自动处理、条件检查和异常分开展示。优先安排清晰主线，保留实际存在的跳过或直接交付路径。不宣称支持精确时序语义。项目图不要用猜测关系覆盖扫描证据。根据代码理解创建的业务图标明推断，并列出依据。

## 交付

交付 HTML 与 JSON（后者可继续编辑）。说明扫描文件数量、错误/截断、支持语言和未确定的动态依赖。运行脚本测试验证改动；用浏览器检查新模板的文字、搜索、节点证据、主题和 SVG 导出。保持源码不变。此工具不证明项目安全，不触发项目测试或业务接口。

业务精排图交付前查看实际 SVG 的浅色和深色渲染；浏览器受限时可使用独立静态 SVG 渲染工具，但不能用静态检查代替交互验收。明确说明未完成的验收项。不要将其他项目的源码修改视为绘图任务的一部分。

质量检查：业务精排模式对中英文分别生成布局并写入 `layout-checks.json`；任何 `proper_crossings` 非空均需人工检查并说明。标签无可用位置或文本装不下时调整布局/摘要，保留完整详情。测试包括 `python3 -m unittest discover -s tests`；可选 DOM 交互测试 `NODE_PATH=<temporary jsdom node_modules> node tests/workflow_dom.cjs <Workflow AI bilingual demo HTML>`，此用例绑定对比图业务内容，不是通用图验证器。DOM 测试不代表真实浏览器几何或字体检查。


业务画布现有三泳道样式、四种视觉样式、缩放平移与本地图片导出；详细字段及使用限制见 [图表格式](references/format.md#业务画布与导出)。更换字体的样式也要查看实际渲染，不能仅凭基础字体的几何检查判定全部样式通过。新增交互运行 `tests/studio_dom.cjs`；其图像 API 使用模拟，实际导出验收须单独说明。


用户要求动态 Flow 时，在 JSON 的 `views` 中明确列出有代码依据的有向情景，按 [动态 Flow 格式](references/format.md#动态-flow-与浏览工具) 生成。`assets/explorer.js` 自动内嵌到 HTML，支持情景播放、路径查询、小地图、分类聚焦及 WebM。验证新增逻辑运行 `tests/explorer_dom.cjs`；该测试的媒体 API 是模拟，不证明浏览器视频编码成功。不要把动画称为项目真实执行记录。


Signal Flow 的发光短线和节点光圈由 `assets/signal.js` 独立实现。对照视觉参考打磨效果时，不引入 Archify 源码或素材。对应回归检查为 `tests/signal_dom.cjs`，并查看导出的动效静态帧；静态帧不能证明真实浏览器的动画流畅度。


Bosun 不需要页面上的情景播放器与情景按钮栏，保持其隐藏且不可聚焦；不要因动态 Flow 请求重新添加。优先使用 Signal Flow 连线动效，保留路径、小地图和分类工具。

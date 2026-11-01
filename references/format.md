# 图表格式

```json
{"version":1,"title":"发布流程","kind":"workflow","nodes":[{"id":"edit","label":"编辑","group":"准备","evidence":[]},{"id":"review","label":"审核","group":"交付","evidence":[]}],"edges":[{"source":"edit","target":"review","label":"提交","confidence":"manual","evidence":[]}]}
```

节点 id 唯一；每条边引用存在的节点。最多 2000 节点和 10000 条边，文字长度有界。evidence 是数组，每项 `{ "file": "app/main.py", "line": 12 }`，仅接受相对路径和正整数行号；不要放源码、密码、凭据或绝对路径。confidence 可选 observed、inferred、manual，默认 manual。节点可带 group、detail。kind 是 architecture 或 workflow。

SVG 自动按依赖层排列；环中的节点使用同一层。模块多时优先分组概览；细节可搜索、聚焦邻居和缩放。箭头表示 source 依赖/指向 target，扫描时为导入方 → 被导入模块。JS/TS 仅检测静态 import/export-from 字面量，属于启发式证据，不解析别名配置、动态 import、require、模板字符串或完整语言语法。Python 用 AST 提取 import；条件 import 和 TYPE_CHECKING 也会保留，不代表实际运行过。

## 业务流程精排模式

业务流程图优先用 `layout: {"mode":"authored","width":1430,"height":850}`。每节点提供 `position:[x,y]`、`size:[250,116]`、`role:process|human|decision|output|stop` 和最多两行 `summary`。摘要每行建议不超过 18 个汉字，标题建议不超过 12 个汉字。

每条边提供正交路线 `points:[[x,y],...]` 与 `label_position:[x,y]`；起止点必须落在对应节点边界。渲染器拒绝节点重叠、出界、斜线、穿过节点及错误端点。现在分别检查中英文文本：以保守宽度估算进行标题和摘要换行，超出两行则拒绝；标签自动尝试避开节点、其他标签和其他连线，无可用位置时拒绝；记录严格相交的连线对。字体估算不等于真实浏览器测量，仍需查看实际 SVG；不宣称覆盖 Archify 的全部检查。

可选字段：`subtitle`、`bands:[{"y":60,"label":"01 生成与交付"}]`、`cards:[{"title":"注意","body":"说明"}]`、`reading_order:[节点id,...]`。交互包含点击详情、逐步阅读、深浅主题、演示视图和 SVG 下载；工具还直接生成 `diagram-en-light.svg`、`diagram-en-dark.svg`、`diagram-zh-light.svg` 和 `diagram-zh-dark.svg`，无需浏览器导出即可使用。示例见 `examples/business-workflow.json`，只作结构参考，不套用其中业务事实。

业务精排图支持右上角 English / 中文切换。通过 `translations: {"en": {"中文原文":"English translation"}}` 提供标题、摘要、节点详情、连线、分区和卡片的译文。未提供译文时保留原文，不调用翻译服务；源码路径与节点 ID 不翻译。SVG 导出使用当前语言。

业务精排图默认显示英文，可通过右上角“中文”切换；缺少译文的内容保持原文。

渲染会输出 `layout-checks.json`，记录两种语言的检查结果及交叉。每个语言/主题的 SVG 独立生成；语言切换不修改拓扑或源码证据。界面搜索匹配节点标题、ID 和业务详情。

## 业务画布与导出

分区现在显示为泳道，`bands` 可包含 `bottom`（底部坐标）和 `tone:"warning"`（异常泳道）。要求 `30 <= y < bottom <= 画布高度`；标题位置是 y，上边框在 y-30。安排泳道之间留白，连线标签避开标题和边框。

业务画布支持 Classic、Signal、Blueprint、Editorial 四种样式；独立动效开关尊重减少动态效果的系统偏好。缩放按钮、适应画布、拖动平移、Ctrl/⌘ + 滚轮缩放、0/+/- 快捷键可用。语言与样式切换保留当前视角和所选步骤。演示按钮精简页面，不请求系统全屏。

导出菜单提供当前语言/主题/样式的 SVG、2× PNG/JPEG/WebP、1200×630 PNG 分享卡片及 PNG 剪贴板复制。始终导出完整图，清除搜索淡化和选中态，暂停动画。图片使用本地浏览器 SVG→Canvas；不支持的编码格式显式提示，不将 PNG 冒充 WebP。剪贴板依赖浏览器权限与 API；失败时提示改用 PNG 下载。WebM 录制使用浏览器 MediaRecorder/captureStream；不支持时明确提示。

`tests/studio_dom.cjs` 检查画布状态、样式、动效及导出错误恢复；它模拟 Image/Canvas，只验证逻辑和尺寸，不能替代真实图片编码、剪贴板和下载验收。

## 动态 Flow 与浏览工具

`views` 最多定义五个明确情景：`{"id":"direct","label":{"en":"Direct delivery","zh":"直接交付"},"nodes":["request","initial","download"]}`。相邻步骤必须在 edges 中存在唯一的同向连线，否则拒绝生成。不要把 reading_order 当作运行路径，不补造不存在的跳转。播放是讲解动画，不执行项目。

情景栏、播放/暂停、重播、前后步、进度拖动、0.5–2× 调速、镜头跟随与本地演示链接共用这份 views。播放有限，默认由用户启动；页面隐藏、Escape、打印或减少动态效果时暂停。路径查询用有向图广度优先搜索；上游/下游只表示所记录图的可达关系，不称为实际影响范围。分类聚焦、小地图、节点悬停/键盘预览、连线详情及节点本地链接不改变图的拓扑。

普通导出清除临时聚焦、阅读层级隐藏、镜头、关系点击区域和播放粒子。另有明确命名的路径/可达关系分享卡片保存聚焦范围。自适应 SVG 内嵌两个主题，跟随查看器 prefers-color-scheme。WebM 导出录制当前情景 6 秒，含移动粒子；支持取消，停止后释放捕获轨道。图片编码、剪贴板与 MediaRecorder 需要真实浏览器验收；DOM 测试对这些 API 使用模拟。

本地链接只包含文件 URL 和节点/情景位置，不上传、托管或跨设备分享图表。

## Signal Flow 聚焦动效

Signal Flow 使用自行实现的折线区间插值绘制发光短线，不依赖外部渲染器。选择该样式会开启约 6.4 秒的示意动画；结束后 Motion 回到关闭，可再次点击播放。选中节点显示蓝色光圈，仅其直接关联的入边/出边保持动态；异常边使用粉色。S 键循环切换视觉样式。页面隐藏、减少动态效果、Escape、切换样式时清理动效；普通 SVG 导出移除全部临时光圈和短线。`tests/signal_dom.cjs` 验证转弯插值、邻接分支数、残影清理及导出隔离。

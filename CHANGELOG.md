# Changelog

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.6.0] - 2026-02-11

### Added

- 日志显示账号真实用户名 (`src/utils.py`, `src/checkin.py`)
  - 新增 `_make_account_label()` 从 Cookie 提取 nickname/username
  - 日志标签格式：`默认账号 (张三)`、`账号 1 (李四)`
- Cookie 失效检测 (`src/utils.py`)
  - 新增 `validate_cookie()` 通过任务列表 API 验证 Cookie 有效性
  - 所有脚本在执行任务前统一验证 Cookie
  - Cookie 无效时输出明确错误信息并跳过该账号
- 非零退出码支持 (`src/auto_read.py`, `src/lottery.py`)
  - Cookie 失效或任务失败时以 exit code 1 退出
  - 触发 GitHub Actions 内置失败通知邮件

### Changed

- `src/checkin.py`: `get_all_cookies()` 标签加入用户名，`main()` 加入 Cookie 验证
- `src/comment.py`: `main()` 加入 Cookie 验证
- `src/auto_read.py`: `run_auto_read()` 加入 Cookie 验证，`__main__` 加入 exit code
- `src/lottery.py`: `main()` 加入 Cookie 验证 + 返回值，`__main__` 加入 exit code

## [1.5.0] - 2026-01-18

### Added

- 四周年活动自动化功能 (`src/draw_4th.py`)
  - 活动地址：https://activity.zaimanhua.com/draw-4th/
  - 活动时间：2026.1.16 - 2026.1.22
  - 自动发送祝福弹幕
  - 自动执行转盘抽奖（使用所有可用次数）
  - 自动关闭中奖弹窗并显示奖品名称
- 四周年活动 workflow (`draw_4th.yml`)
  - 北京时间 5:00-23:00，每 20 分钟触发
  - 支持手动触发

### Technical Notes

- 使用移动端 UA 和 iPhone X 视口 (375x812)
- Cookie 域名设置为 `activity.zaimanhua.com`
- 页面选择器：
  - 弹幕输入框: `.dammu-input`
  - 发送按钮: `.dammu-send-btn`
  - 抽奖按钮: `.pointer`
  - 抽奖次数: `.draw-count`
  - 中奖弹窗: `.winPrize`

## [1.4.4] - 2026-01-14

### Fixed

- 修复抽奖任务按钮定位问题 (`src/lottery.py`)
  - 添加切换到"活动介绍"标签页的逻辑，确保在正确页面执行任务
  - 更新按钮选择器为 `.imgBoxP7 .btn1/btn2/btn3`
  - 改用按钮文本判断任务状态（比 API 字段更可靠）
  - 调整页面加载等待策略 (`domcontentloaded` + 5秒)

## [1.4.3] - 2026-01-13

### Added

- 签到后自动领取"到此一游"任务积分 (`src/checkin.py`)
  - 新增 `claim_checkin_reward` 函数
  - 签到成功后自动检查并领取任务 ID=8 的积分奖励

### Changed

- 签到频率从每天 3 次改为每天 1 次（北京时间 8:00）
- 签到重试次数从 3 次增加到 5 次

## [1.4.2] - 2026-01-13

### Fixed

- 修复任务领取 API "参数错误"问题 (`src/utils.py`)
  - `claim_task_reward`: 添加 POST + JSON body 方式传参
  - 尝试多种参数名 (`id`, `taskId`, `task_id`) 提高兼容性
  - `claim_rewards`: 修复状态判断逻辑 (`status==3` → `status==2`)
  - 更新任务状态注释：`status=2` 为可领取，`status=3` 为已领取

## [1.4.1] - 2026-01-13

### Fixed

- 完善抽奖任务二（分享页面）的自动化流程 (`src/lottery.py`)
  - 点击"去完成"后自动处理弹窗并点击复制按钮
  - 修复之前只点击按钮但未完成弹窗交互的问题

## [1.4.0] - 2026-01-13

### Added

- 新增 `src/auto_read.py` 阅读脚本，使用 v4 API 模拟阅读
  - 通过 API 请求漫画章节图片实现阅读时长累计
  - 支持任务 13（海螺小姐 - 累计观看十分钟漫画）自动化完成
  - 智能任务状态监控，每分钟检查一次
  - 支持 API 领取 + UI 领取双重回退机制

### Fixed

- 修复 `checkin.yml` 执行失败问题（恢复被误删的 `src/checkin.py`）
- 修复 `watch.yml` 缺少 playwright 依赖的问题
- 修复 `comment.py` 任务状态判断逻辑
  - `status=2` 表示"可领取"而非"未完成"
  - 当任务状态为 2 时自动领取奖励并返回成功

### Changed

- 用 `auto_read.py` 替换原有的 `watch.py`（已删除）
- 更新 README.md，任务 13 现已支持自动化

## [1.3.4] - 2026-01-13

### Changed

- 更正文档中关于任务 13（累计观看十分钟漫画）与 `ReadingDuration` 关系的表述
  - 明确：`ReadingDuration` 不是任务 13 的可靠计时/进度指标
  - 将“网页端缺少可见的有效时长上报/心跳机制”作为当前可证据支撑的解释
  - 覆盖：`README.md`、`src/watch.py`、`debug/INVESTIGATION_REPORT.md`

## [1.3.3] - 2026-01-12

### Fixed

- 修复评论任务验证逻辑 (`src/comment.py`)
  - 增加对“未绑定手机号”账号的检测，自动跳过无法完成的任务（避免 CI 失败）
  - 优化任务状态检查逻辑，优先检查任务 14 是否已完成
  - 添加任务 API 验证，通过任务 ID=14 确认评论是否成功
  - 修复 `claim_rewards` 调用缺少 `cookie_str` 参数的问题
  - 添加页面刷新确保 localStorage 登录状态生效
  - 增强评论输入框和发布按钮的选择器兼容性
  - 添加错误提示检测功能

- 修复 Windows GBK 编码问题 (`src/utils.py`)
  - 将 Unicode 字符 `✓`/`✗` 替换为 ASCII `[OK]`/`[SKIP]`

### Technical Notes

- 发现未绑定手机号的账号无法完成评论任务：
  - 前端显示"评论成功"，但评论不会真正发布
  - API 任务状态保持 status=1（未完成）
  - 这是网站业务限制，非脚本问题
- 建议：确保账号已绑定手机号以使用评论功能

## [1.3.2] - 2026-01-12

### Changed

- 更新 `src/watch.py` 文档，说明任务 13（累计观看十分钟漫画）的技术限制
- 更新 `README.md` 新增"每日阅读功能说明"章节，详细解释：
  - 任务 14（每日一读）可正常完成
  - 任务 13（累计观看十分钟漫画）无法通过网页自动化完成
  - 现象：网页端阅读可写入阅读位置，但未观察到稳定的“有效阅读时长”上报/心跳机制

### Technical Notes

- 更正：`ReadingDuration` 在多次查询中可能保持为 0，且与任务 13 的状态不严格对应，不能将其作为任务 13 的可靠计时依据
- 测试覆盖：桌面网站、移动端网站、模拟 APP 请求头均无法触发时长记录
- 结论：任务 13 是移动端 APP 专属功能，非脚本问题

## [1.3.1] - 2026-01-12

### Fixed

- 修复评论功能多账号登录状态问题 (`src/comment.py`)
  - 添加 `init_localstorage` 调用确保 Vue 应用识别登录状态
  - 在首页和漫画详情页均设置 localStorage

### Changed

- 调整 `watch.yml` 超时时间 30 → 90 分钟，支持最多 5 账号串行执行
- 统一所有 workflow 的多账号配置，补全 `COOKIE_4` 和 `COOKIE_5` 环境变量
  - `comment.yml`
  - `watch.yml`
  - `lottery.yml`

## [1.3.0] - 2026-01-12

### Added

- 每日抽奖功能 (`src/lottery.py`)
  - 自动完成关注微博任务（需首次手动关注）
  - 自动完成分享任务
  - 自动完成阅读任务（复用 watch.py）
  - 自动执行所有可用抽奖次数
  - API 签名机制：`MD5(channel + timestamp + secret)`
- 抽奖 workflow (`lottery.yml`)
  - 北京时间 11:00 自动执行
  - 支持手动触发

## [1.2.3] - 2026-01-11

### Fixed

- 修复某些漫画翻章失败问题 (`src/watch.py`)
  - 添加 `is_valid_chapter_url()` 函数验证章节 URL 有效性
  - 过滤掉包含 `undefined` 占位符的无效章节 URL
  - 增加等待时间（2s → 3s）让 JS 完成渲染
  - 输出跳过的无效章节数量便于调试

## [1.2.2] - 2026-01-11

### Fixed

- 修复阅读历史不同步问题 (`src/watch.py`)
  - 发现正确的 API 端点: `POST /app/v1/readingRecord/add`
  - 使用 `Authorization: Bearer <token>` 头进行认证
  - 在进入章节和翻章时主动调用 API 保存阅读进度
  - 添加请求拦截以捕获和调试 API 调用

## [1.2.1] - 2026-01-11

### Changed

- 完善 README 文档结构和内容

## [1.2.0] - 2026-01-11

### Added

- 每日评论功能 (`src/comment.py`)
  - 自动在随机漫画下发表评论
  - 避免重复评论同一漫画
  - 完成后自动领取积分
- 每日阅读功能 (`src/watch.py`)
  - 自动阅读漫画12分钟
  - 智能跳过无效/付费章节
  - 自动翻页和翻章
  - 完成后自动领取积分
- 共享工具模块 (`src/utils.py`)
  - Cookie 解析和 localStorage 设置
  - 浏览器上下文创建
  - 积分领取功能
- 独立的 GitHub Actions workflows
  - `comment.yml` - 每日评论（北京时间 9:30）
  - `watch.yml` - 每日阅读（北京时间 10:00）

### Changed

- 拆分原 `daily_tasks.py` 为独立模块
- 优化跨域登录状态处理（localStorage 同步）

## [1.1.0] - 2026-01-10

### Added

- 支持多账号签到（最多 5 个账号）
- 通过 `ZAIMANHUA_COOKIE_1`、`ZAIMANHUA_COOKIE_2` 等环境变量配置多账号
- 向后兼容单账号 `ZAIMANHUA_COOKIE` 配置

## [1.0.1] - 2026-01-10

### Changed

- 添加调试信息输出（Cookie 解析数量、页面标题、按钮状态）
- 优化已签到状态检测逻辑
- 按钮禁用时尝试 JavaScript 强制点击
- 失败时保存截图用于调试

### Fixed

- 修复已签到时按钮禁用导致的超时错误

## [1.0.0] - 2026-01-10

### Added

- 初始版本发布
- 支持每天三次自动签到（北京时间 8:00、12:00、20:00）
- 使用 Playwright 模拟浏览器操作
- 通过 Cookie 认证登录状态
- 支持手动触发签到（workflow_dispatch）

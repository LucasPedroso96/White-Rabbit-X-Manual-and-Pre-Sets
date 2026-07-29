# White Rabbit X — MQL5 Market 说明

依据当前 EA 源码与 set 清单生成的权威参考 — EA 1.11 — 127 inputs — 3738 sets

## 软件功能

White Rabbit X 是用于系统研究、受控执行与 WFO 的 MT5 多指标 EA。

Current schema: 127 inputs. Current manifest: 3738 sets.

- 十二种原生引擎：MACD、EMA Cross、Momentum、Stochastic、TRIX、RSI、CCI、Williams %R、DeMarker、MFI、OsMA、Ichimoku。
- 七种入场方法明确区分同一收盘 K 线的 AND 与 OR。
- MTF、MA、ADX、ATR 波动率与新闻过滤器独立。
- 四种 PositionSizeMode 以及 equity/margin 保护。
- Stop、take、breakeven、trailing、reversal 构成出场组合。
- Dashboard、交易日程、语言与 WFO 属于操作层。

## 周期仪表板遥测

面板使用与仓位计算和篮子平仓相同的状态快照。

- 按 tick 的周期刷新最多每秒一次；初始化和交易事件可立即刷新。
- Balance/Equity 属于整个账户。Closed P&L 是 OnInit 之后的变化；Open P&L 与 positions 是当前状态，并按 Symbol + Magic 过滤。
- Martingale 分别显示 BUY/SELL 连续亏损、周期亏损次数与总额、已恢复金额、剩余 deficit，以及 deficit × Multiplicador 的 target。
- 超过 MaxMartingaleSteps 会 hard reset：旧 deficit 被丢弃，下一单使用基础手数；每个方向最多允许一笔持仓。
- D'Alembert 显示 BUY/SELL 当前级别与下一笔规范化手数。
- Grid 显示 legs/volume、包含成本的 realized、open P&L、cycle P&L、周期开始时冻结的 target 与 remaining。
- Anchor 是最近确认的持仓。BUY 必须严格低于 anchor − ATR × DistanciaMinima；SELL 必须严格高于 anchor + ATR × DistanciaMinima；进度以 ATR 表示。
- Separate 在某一方向 flat 时仅结束该方向周期；Unified 在 BUY/SELL 都 flat 时结束。未完成订单会延后 reset。
- Target 只触发平仓请求；实际退出 commission、fee 与 slippage 可能使最终结果略低于目标。
- InterfaceLanguage 保留 11 种界面语言。Auto 在 Tester 使用 English、实盘使用终端语言；缺少翻译的标签回退为 English。

## 兼容组合与限制

这些是保守规则；经纪商可能实施更严格限制。

- Percentage 与 Fixed-R 需要 AtivarStop=true。
- Grid 仅支持 Monetary/Fixed Lot、Recovery_None 与 hedging account。
- Grid 需要 take、正 DistanciaMinima 以及活动方向至少两笔上限。
- 只要篮子仍有持仓，本周期已实现亏损、swap、commission 与 fees 就继续计入达到目标所需的结果；单独一腿盈利不会清除这些成本。
- 在 Grid_SeparateProfit 中 BUY 与 SELL 周期独立。某一方向全部持仓消失时，该方向周期结束；之后的入场开启新周期，不继承已结束的亏损。
- D'Alembert 仅限 Fixed Lot、Grid_Disabled、DAlembertStep>0。
- Martingale 受 MaxMartingaleSteps 与 MaxMartingaleLot 限制。
- OnOppositeOrder 需要 hedging、双向交易且关闭 grid。
- 新闻回测需要 Common\Files 中的 CSV。
- 时段使用经纪商服务器时间。
- 每个经纪商都要重新核对 suffix 与品种规格。

## 社区与下载

加入官方 Telegram 频道：**https://t.me/MrRabbit_MT5**

手册与完整参数集库：**https://github.com/LucasPedroso96/White-Rabbit-X-Manual-and-Pre-Sets**

- 按品种和系统类型（止损止盈、追踪止损、网格、马丁格尔等）分类的现成参数集，可直接载入策略测试器。
- 您所用语言的手册：葡萄牙语、英语、俄语、中文、西班牙语、日语、德语、韩语、法语、意大利语和土耳其语。
- EA 与参数集库的更新通知。
- 技术支持以及与其他用户的经验交流。

> 这是唯一的官方频道。请勿从声称代表 White Rabbit X 的第三方购买参数集或 EA 副本：本 EA 仅在 MQL5 Market 销售，参数集在上述频道免费发布。

## 风险警告

任何 EA、set 或历史结果都不能保证未来表现。必须进行 OOS 与模拟盘验证。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`

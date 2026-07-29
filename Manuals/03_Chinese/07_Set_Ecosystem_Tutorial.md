# White Rabbit X — Set 生态教程

依据当前 EA 源码与 set 清单生成的权威参考 — EA 1.11 — 127 inputs — 3738 sets

## 范围与事实来源

EA 源码定义 inputs、默认值、枚举与功能；清单定义每个 set 的状态、路径和 SHA-256。旧 Quantum 资料仅供追溯。

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

自动生成资料；参数标识符与 EA 完全一致。

## 安装与首次运行

安装匹配的 EX5，在 Tester Inputs 加载一个 set，选择精确的经纪商品种并检查 Journal。

## 检测到的 set 库

数量从文件系统与清单读取。每个 set 是研究假设，不是收益承诺。 Counts and fingerprints were read at generation time.

| Folder | Sets | Purpose |
| --- | --- | --- |
| 01_Forex | 168 | Per-asset baselines — Forex. |
| 02_Metals | 18 | Per-asset baselines — Metals. |
| 03_Cryptocurrencies | 36 | Per-asset baselines — Cryptocurrencies. |
| 04_Indices_Energies | 42 | Per-asset baselines — Indices Energies. |
| 05_US_Stocks_CFD | 300 | Per-asset baselines — US Stocks CFD. |
| 06_Research_Matrix | 935 | Controlled one-axis research. |
| 07_Entry_System_Matrix | 3360 | Indicator × entry method × management matrix. |
| 08_Filter_Stack_Matrix | 320 | Signal-filter stack combinations. |
| 09_Risk_Engine_Matrix | 130 | Compatible sizing, risk and recovery models. |
| 10_Exit_Stack_Matrix | 720 | Exit-control stack combinations. |

## 清单状态与发布决策

保留原状态，并保守映射为 USE、REOPTIMIZE、RESEARCH 或 HOLD。

| 系统 | 管理方式 | 参数集 |
| --- | --- | ---: |
| `01_SLTP` | Stop Loss + Take Profit as ATR multiples | 356 |
| `02_SLTP_ORGANIC` | SL + organic take anchored on the last trade | 356 |
| `03_TRAIL_ONLY` | SL + trailing, no TP: let it run | 356 |
| `04_SLTP_TRAIL` | SL + TP + trailing behind | 356 |
| `05_BE_TRAIL` | Mandatory breakeven + trailing | 356 |
| `06_REVERSAL_EXIT` | Closes on the indicator's opposite signal | 356 |
| `07_GRID_SEPARATE` | Grid with a target per side (hedging account) | 356 |
| `08_GRID_UNIFIED` | Grid with a single basket target (hedging account) | 356 |
| `09_MARTINGALE` | Lot doubles after a loss, one position per side | 356 |
| `10_DALEMBERT` | Lot grows in arithmetic steps after a loss | 356 |
| `11_SIGNAL_ONLY` | No SL and no TP: measures the raw signal | 356 |

## 安全流程

每个阶段只改变一个矩阵，并保存完整证据。

1. 确认 EX5、源码、set schema 与清单属于同一版本。
2. 通过 Strategy Tester Inputs 加载 set 库。
3. 映射经纪商的精确品种与 suffix。
4. 先用 01–05 baseline，分别测试 BUY/SELL。
5. 06 用于单轴研究。
6. 07 入场、08 过滤、09 风险、10 出场。
7. 依次执行 IS、OOS 与 forward demo。
8. 检查 Status、RelativePath 与 SHA256。
9. 只有明确 USE 才代表指定环境可用。

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

## News filter and CSV workflow

Live mode reads the MT5 Economic Calendar in broker-server time and blocks new entries if the calendar query fails. Backtests cannot read that live calendar: run MQL5\Scripts\White Rabbit News Exporter on a live/demo chart, cover the entire test interval, and write NewsCSVFile to the terminal Common\Files folder. The semicolon-delimited header is datetime;currency;importance;event_name, where importance 2 is moderate and 3 is high. Use the same broker/server timezone; for suffixed or non-FX symbols set ExportMoedas and NewsMoedasManual explicitly. Manual currencies take precedence over automatic symbol parsing.

## Grid cycle and ATR spacing

Every additional grid leg is measured from the newest already-confirmed position on that side and must satisfy ATR × DistanciaMinima. The initial order cannot recursively trigger another leg in the same calculation event; it becomes the anchor on the following cycle. Individual grid take-profits are disabled: Separate mode evaluates independent BUY/SELL cycles against frozen monetary targets and ends a side when it becomes flat; Unified evaluates the aggregate BUY+SELL basket and ends when both sides are flat. Realized commissions, swap, fees and stopped legs remain in the result while the corresponding cycle is open. The target triggers a close request, so actual exit costs and slippage can leave the final result slightly below it. Live cycle state is persisted across an EA restart. Grid is hedging-only and must be reoptimized after any EA, broker-contract or cost change.

## Diagnostics and supplied utilities

The Experts/Journal tab is authoritative for rejected inputs, OrderCheck failures, news-calendar errors and close retries. Compile and run MQL5\Scripts\WhiteRabbit Filters SelfTest; its final line must report zero failures. Use White Rabbit News Exporter to build the test CSV, then verify its date range, currencies, delimiter and Common\Files location before a news-enabled backtest.

## 风险警告

任何 EA、set 或历史结果都不能保证未来表现。必须进行 OOS 与模拟盘验证。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`

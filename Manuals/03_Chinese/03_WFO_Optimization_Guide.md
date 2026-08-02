# White Rabbit X — WFO 优化指南

依据当前 EA 源码与 set 清单生成的权威参考 — EA 1.11 — 127 inputs — 3738 sets

**注意日期。** 启用 WFO 后，OnTester 会将测试的实际结束时间与 input_end_date 比较；如果测试提前结束（容差 80 小时），则返回零。日期设置错误会使所有测试遍次归零，整个优化看起来像是坏掉了。请将 input_end_date 设为与策略测试器中相同的结束日期。

## 范围与事实来源

EA 源码定义 inputs、默认值、枚举与功能；清单定义每个 set 的状态、路径和 SHA-256。旧 Quantum 资料仅供追溯。

EA SHA-256: D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973. Manifest SHA-256: E96B9E4050F8EA8B764E187BD6CC1E907AE2AE8C4A6489C9EF2D3317C6003F75.

自动生成资料；参数标识符与 EA 完全一致。

## Walk-forward 方法

按时间顺序使用 IS、OOS 和 forward demo，并采用真实点差、佣金、swap 与 slippage。

## 安全流程

每个阶段只改变一个矩阵，并保存完整证据。

1. 确认 EX5、源码、set schema 与清单属于同一版本。
2. 通过 Strategy Tester Inputs 加载 set 库。
3. 映射经纪商的精确品种与 suffix。
4. 按类别和品种浏览：每个品种包含 11 种系统类型（01_SLTP 至 11_SIGNAL_ONLY），每个方向一个 set（BUY/SELL；统一网格为 BOTH），入场有两种变体——MULTI 在单一轴上竞争指标 0–10，ICHIMOKU 有独立文件。
5. 第 1 阶段是区域发现：直接用原样的 set 运行遗传优化——完整的入场组（指标、方法、时间框架、applied price、周期）、系统的出场以及过滤器开关，一次全部打开。
6. 从后续轮次起，锁定（Y→N）上一阶段已决定的“文字型”输入——枚举和布尔值——只保留数值型开放；过滤器的细调只有在其开关存活为开启时才进入。
7. ATR 入场过滤器（EntradaATR）只存在于网格系统；其他系统中它按设计保持关闭。
8. 用真实 tick 验证胜出者：由与 OHLC 的偏差和样本外保持率决定，绝不是样本内利润。如果真实 tick 结果与 OHLC 结果的偏差超过 30%，应淘汰该候选——两者应在结果的形态上一致，而不仅仅是符号一致。
8a. 用 Monte Carlo 为幸存者把关：对交易序列进行自助重抽样（以 R 倍数计，而非货币），若第 95 百分位回撤超过实际观察回撤的两倍，或重抽样后的破产概率超过 5%，则淘汰。一个仅因交易发生的特定顺序而显得稳定的参数集，并不是真正稳定的。
8b. 对六个 Fixed-R 系统（`01` 至 `06`），要求样本外 R 期望值为正。样本外打平或亏损 R 的参数集不予晋级，无论其样本内表现如何。
9. 真实 tick 之后，把仓位模式切换为 Percentage 再跑一次：只有同样通过才晋级——set 最终也应以该模式交易。

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

> 本节目前仅提供英文版本。

## Modeling mode: use real ticks

In the Strategy Tester's **Settings** tab, **Modeling** field:

```
Every tick based on real ticks   <- use this
OHLC 1 minute                    <- only 01_SLTP and 02_SLTP_ORGANIC
```

This is not a preference. Measuring the same set in both modes across three
years, the OHLC mode **understated losses by 3.3x on trailing systems and 23x
on grid** — always in the optimistic direction. Only fixed SL/TP stayed within
3%.

The cause is structural: trailing and grid depend on **when** price touched each
level inside the bar. OHLC mode interpolates that from four prices per minute
and smooths away exactly the adverse excursions that would have closed the
position. Optimizing a trailing system on interpolated bars selects parameters
that survived a price path which never happened.

Real ticks cost roughly 20x more time per pass. It is worth it: that is the
difference between a result and a number.

### If you must save time, save it in the right place

Signals are evaluated at BAR CLOSE, so choosing indicator, method or timeframe
gives the same entry instant in both modes. Stop, target and trailing, on the
other hand, depend on the intrabar path.

So use each model where it is reliable: OHLC to narrow the switches (indicator,
method, timeframe, periods) and real ticks for the exit geometry. With the
signal locked the search space collapses by orders of magnitude, and real ticks
stop being prohibitive.

## Fixed-R to research, percentage to trade

Optimize in **Fixed-R**: with the base capital frozen, passes stay comparable to
each other and across symbols. +40R on gold and +40R on EURUSD mean the same
thing, while "+3,200 USD" means nothing without knowing the lot and the balance.

Live, **Percentage** usually makes more sense: it tracks the account, compounds
as it grows and cuts exposure as it shrinks — protection Fixed-R cannot give,
because it deliberately ignores the running balance. Both modes report in R, so
the record stays readable after the switch.

因此，只有在以 Percentage 模式重复最终回测之后，流程才会保存已通过的 set：若结果在复利下无法维持，说明它尚未准备好——通过验证的 set 也以该模式交付。

## 公式：优化目标是什么，报告结果的又是什么

`selectedFormula` 决定 OnTester 向遗传优化器返回什么——即用来给每次测试遍次排名的那个单一数字。这与"交付的参数集最终以什么单位报告结果"并不是同一个问题。该流程针对不同阶段使用不同公式：较早阶段偏向奖励结果广泛、样本充分的公式（这样遗传搜索才有梯度可以攀升），而不是那种只在某一条路径上得分很高的狭窄公式。

对于六个 Fixed-R 系统，交付参数集的最终报告使用 **SomaR**（交易结果以 R 倍数计的总和）：一旦候选参数集已经通过保留率、偏差、Monte Carlo 以及上述 R 期望值把关，SomaR 就是用本指南其余部分用来比较品种和系统的同一单位——R，而非货币——来陈述结果的指标。它不决定胜者；它只是以可比较的单位报告胜者的结果。

## Autobot 与 Historical Tool Manager

本参数集库出厂即经过预先验证，但上述流程并非黑箱——它以 **Autobot** 的形式发布在本手册所在的同一个仓库中（`Autobot/`），是真正运行本指南每一步的代码。您可以阅读它，确切了解某个参数集是如何获得其地位的，也可以针对自己的经纪商、品种列表或日期范围自行运行。

真实 tick 确认这一步，依赖于有真实 tick 数据可供核对。**Historical Tool Manager**（MQL5 Market：https://www.mql5.com/pt/market/product/188711）可将深度 tick 和 M1 历史数据以 Custom Symbol 的形式导入 MT5，适用于经纪商自身历史数据覆盖不够久远的品种——无论您是运行 Autobot，还是只想获得更多历史数据用于手动测试，都会有用。

## 风险警告

任何 EA、set 或历史结果都不能保证未来表现。必须进行 OOS 与模拟盘验证。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`

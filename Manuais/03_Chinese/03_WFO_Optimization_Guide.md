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
4. 先用 01–05 baseline，分别测试 BUY/SELL。
5. 06 用于单轴研究。
6. 07 入场、08 过滤、09 风险、10 出场。
7. 依次执行 IS、OOS 与 forward demo。
8. 检查 Status、RelativePath 与 SHA256。
9. 只有明确 USE 才代表指定环境可用。

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

## 风险警告

任何 EA、set 或历史结果都不能保证未来表现。必须进行 OOS 与模拟盘验证。

---
EA SHA-256: `D85A30A0836A9BE75F6DFC55868BDC664EE1FC7F5DD0840C029DEB0EF8AC8973`  
EA version: `1.12`

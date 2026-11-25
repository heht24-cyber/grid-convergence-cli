# Grid Convergence CLI

从三套 CFD 网格的结果估算观测收敛阶、Richardson 外推值和细网格的网格收敛指数（GCI）。适用于固定工况下的压降、阻力系数等标量。需要 Python 3.9 或更新版本。

```bash
python grid_convergence.py example.csv
python grid_convergence.py example.csv --json
```

## 准备数据

按 `spacing,value` 两列输入三行数据，网格顺序任意。三套网格的特征尺寸应使用同一单位，目标量的提取位置、定义和单位也应一致。对同一几何域内整体加密的网格，可用 `h ∝ N^(-1/d)` 估计相对网格尺寸，其中 `N` 为单元数、`d` 为空间维数。建议把迭代误差降到明显小于网格间结果差值，再做对比。

```csv
spacing,value
0.04,1.12
0.02,1.03
0.01,1.0075
```

示例的观测阶数约为 **2**，外推值为 **1.0**，细网格绝对 GCI 约为 **0.009375**，相对 GCI 约为 **0.931%**。

## 计算与限制

从细到粗记为 1、2、3。设 `r = h₂/h₁`、`Δ₂₁ = f₂ − f₁`、`Δ₃₂ = f₃ − f₂`。本工具要求 `h₃/h₂` 与 `r` 的相对差异不超过 0.1%。

- 观测阶数 `p = ln(|Δ₃₂/Δ₂₁|)/ln(r)`
- 外推值 `f_ext = f₁ − Δ₂₁/(r^p − 1)`
- 细网格绝对 GCI `1.25 × |f_ext − f₁|`，相对 GCI 为绝对 GCI 除以 `|f₁|` 并转成百分比。若 `f₁ = 0`，只返回绝对 GCI。

结果只反映所选标量的空间网格收敛。即使三套网格单调收敛，也应结合离散格式的理论阶数、更多网格或其他目标量来判断是否进入渐近区间。

| 退出码 | 含义 |
| --- | --- |
| 0 | 得到单调收敛估计 |
| 1 | 相邻网格结果重复、振荡或差值未缩小。估计字段为 `null` |
| 2 | 输入无效或数值超出可计算范围 |

方法参考 [NASA Glenn · Examining Spatial (Grid) Convergence](https://www.grc.nasa.gov/WWW/wind/valid/tutorial/spatconv.html)。

运行测试 `python -m unittest -v`。

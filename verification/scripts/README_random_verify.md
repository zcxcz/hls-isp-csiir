# ISP-CSIIR 随机验证框架使用说明

## 概述

本随机验证框架用于 ISP-CSIIR HLS 模块的自动化测试，支持生成多种类型的随机测试Pattern，运行Python黄金模型和HLS模型，并生成详细的验证报告。

## 文件结构

```
verification/scripts/
├── random_verify_constraints.py   # 约束定义模块
├── generate_random_patterns.py    # 随机Pattern生成器
├── run_random_verify.py           # 随机验证运行器
└── README_random_verify.md        # 本使用说明
```

## 约束定义 (random_verify_constraints.py)

### 图像尺寸约束
- 宽度范围: [16, 128]
- 高度范围: [16, 128]

### 像素值约束
- 范围: [0, 1023] (10-bit)
- 中间值: 512

### 配置参数约束
- **win_thresh**: [8, 48], 4个严格递增值
- **grad_clip**: [8, 48], 4个严格递增值
- **blend_ratio**: [0, 64], 4个任意值

### Pattern类型分布
| 类型     | 权重 | 描述                     |
|----------|------|--------------------------|
| random   | 30%  | 完全随机像素             |
| gradient | 20%  | 随机方向梯度（水平/垂直/对角/径向）|
| edge     | 15%  | 随机位置边缘             |
| corner   | 10%  | 随机角点特征             |
| extreme  | 10%  | 极值测试（全0/全1023/交替）|
| textured | 15%  | 纹理图案（正弦/条纹/混合）|

## 使用方法

### 1. 查看约束摘要

```bash
cd verification/scripts
python3 random_verify_constraints.py
```

### 2. 生成随机测试Pattern

```bash
# 生成10个测试用例
python3 generate_random_patterns.py -n 10

# 指定随机种子（可复现）
python3 generate_random_patterns.py -n 10 -s 42

# 指定输出目录
python3 generate_random_patterns.py -n 10 -o /path/to/output

# 指定Pattern类型
python3 generate_random_patterns.py -n 10 -p gradient
```

### 3. 运行随机验证

```bash
# 默认运行100组测试
python3 run_random_verify.py

# 指定测试数量
python3 run_random_verify.py -n 50

# 指定随机种子
python3 run_random_verify.py -n 50 -s 42

# 详细输出
python3 run_random_verify.py -v
```

## 输出文件

### 测试用例目录结构

```
test_vectors/random/
├── case_0000/
│   ├── input.txt      # 输入图像（线性格式）
│   ├── config.json    # 配置参数
│   └── expected.txt   # 期望输出（Python模型）
├── case_0001/
│   └── ...
```

### 配置文件格式 (config.json)

```json
{
  "case_id": "case_0000",
  "pattern_type": "gradient",
  "seed": 42,
  "width": 64,
  "height": 64,
  "win_thresh": [16, 24, 32, 40],
  "grad_clip": [15, 23, 31, 39],
  "blend_ratio": [32, 32, 32, 32],
  "edge_protect": 32
}
```

### 中间结果目录

```
verification/intermediate/
├── python/           # Python模型中间结果
│   ├── case_0000_stage1.txt
│   ├── case_0000_stage2.txt
│   ├── case_0000_stage3.txt
│   └── case_0000_output.txt
└── hls/              # HLS模型中间结果
    └── ...
```

### 验证报告

```
verification/reports/
├── random_verify_report.txt  # 文本格式报告
└── random_verify_report.json # JSON格式报告
```

## 报告格式示例

```
========================================
ISP-CSIIR 随机验证报告
========================================
开始时间: 2026-03-23 20:36:03
结束时间: 2026-03-23 20:36:06
测试总数: 100
通过数: 98
通过率: 98.00%

误差统计:
- Stage1 最大误差: 2
- Stage2 最大误差: 3
- Stage3 最大误差: 5
- Output 最大误差: 4

Pattern类型统计:
  - corner: 9/10 (90.0%)
  - edge: 15/15 (100.0%)
  - extreme: 9/10 (90.0%)
  - gradient: 20/20 (100.0%)
  - random: 30/30 (100.0%)
  - textured: 15/15 (100.0%)

失败案例:
- case_0023: Stage1:2, Stage2:1, Stage3:3, Output:4
- case_0067: Stage1:1, Stage2:3, Stage3:5, Output:2
========================================
```

## 注意事项

### HLS模型运行

当前框架使用 `tb_simple.cpp` 作为HLS模型实现，该文件是纯C++实现，不依赖Xilinx HLS数据类型。

如需使用真实的HLS综合代码：
1. 在Vitis HLS环境中编译 `isp_csiir.cpp` 及相关文件
2. 修改 `run_random_verify.py` 中的 `HLSModelRunner` 类
3. 确保HLS可执行文件能够读取随机测试向量

### 容差设置

默认容差配置：
- Stage 1: grad容差1, win_size容差0
- Stage 2: 默认容差2
- Stage 3: 默认容差3
- Output: 默认容差2

可在 `run_random_verify.py` 的 `ResultComparator` 类中调整。

### Python黄金模型

Python黄金模型位于 `compute_expected.py`，实现了与HLS代码相同的算法逻辑，用于生成期望输出。

## 扩展开发

### 添加新的Pattern类型

在 `generate_random_patterns.py` 的 `PatternGenerator` 类中添加新的生成方法：

```python
def generate_new_pattern(self, width: int, height: int) -> np.ndarray:
    """生成新的Pattern类型"""
    image = np.zeros((height, width), dtype=np.uint16)
    # 实现Pattern生成逻辑
    return image
```

然后在 `generate` 方法中注册新类型。

### 修改约束范围

在 `random_verify_constraints.py` 中修改对应的约束常量。

## 作者

rtl-verf (验证环境职能代理)

## 版本历史

- v1.0 (2026-03-23): 初始版本
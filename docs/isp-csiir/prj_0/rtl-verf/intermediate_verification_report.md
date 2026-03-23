# ISP-CSIIR HLS 中间阶段验证报告

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | ISP-CSIIR HLS 模块 |
| 项目编号 | prj_0 |
| 文档版本 | v1.0 |
| 编写日期 | 2026-03-23 |
| 编写者 | rtl-verf |

## 验证方法

### 验证目标

验证 HLS C++ 模型与 Python 定点化模型的中间阶段数据一致性，确保 HLS 实现正确性。

### 验证流程

```
┌─────────────────┐     ┌─────────────────┐
│  测试向量生成    │────→│  Python 模型    │
│  (generate_     │     │  (compute_      │
│   test_vectors) │     │   expected.py)  │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │ 中间数据输出    │
                        │ - Stage1: 梯度  │
                        │ - Stage2: 平均  │
                        │ - Stage3: 融合  │
                        │ - Output: 输出  │
                        └────────┬───────┘
                                 │
┌─────────────────┐              │
│  HLS 测试平台   │              │
│  (tb_isp_csiir_ │              │
│   intermediate) │              │
└────────┬────────┘              │
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────┐
│  HLS 中间数据   │      │ Python 中间数据 │
│  (intermediate/│      │ (intermediate/  │
│   hls/)        │      │  python/)       │
└───────┬────────┘      └────────┬────────┘
        │                        │
        └────────────┬───────────┘
                     │
                     ▼
           ┌──────────────────┐
           │  数据比对脚本    │
           │ (compare_        │
           │  intermediate.py)│
           └────────┬─────────┘
                    │
                    ▼
           ┌──────────────────┐
           │   验证报告       │
           └──────────────────┘
```

## 中间阶段数据定义

### Stage 1: 梯度计算

| 字段 | 类型 | 范围 | 描述 |
|------|------|------|------|
| grad | U12 | [0, 2046] | 组合梯度值 |
| win_size | U6 | [16, 40] | 窗口尺寸 |
| grad_h | S14 | [-5115, 5115] | 水平梯度 |
| grad_v | S14 | [-5115, 5115] | 垂直梯度 |

**验证公式：**
- `grad = div_by_5(|grad_h|) + div_by_5(|grad_v|)`
- `div_by_5(x) = (x * 205) >> 10`

### Stage 2: 多尺度方向性平均

| 字段 | 类型 | 范围 | 描述 |
|------|------|------|------|
| avg0_c/u/d/l/r | S11 | [-512, 511] | 小核平均 (center/up/down/left/right) |
| avg1_c/u/d/l/r | S11 | [-512, 511] | 大核平均 (center/up/down/left/right) |

**验证公式：**
- `avg = weighted_sum / sum_factor`
- 使用查表除法

### Stage 3: 梯度加权方向融合

| 字段 | 类型 | 范围 | 描述 |
|------|------|------|------|
| blend0_grad | S11 | [-512, 511] | 小核融合结果 |
| blend1_grad | S11 | [-512, 511] | 大核融合结果 |

**验证公式：**
- `blend_grad = Σ(avg_i * grad_i) / Σ(grad_i)`
- 使用 Newton-Raphson 迭代除法

### Stage 4: 最终输出

| 字段 | 类型 | 范围 | 描述 |
|------|------|------|------|
| input_pixel | U10 | [0, 1023] | 输入像素 |
| output_pixel | U10 | [0, 1023] | 输出像素 |

## 验证执行

### 测试向量配置

| 测试名称 | 图像尺寸 | 图案类型 | 验证重点 |
|----------|----------|----------|----------|
| flat | 64x64 | 平坦图像 | 边界处理、梯度为零 |
| gradient_h | 64x64 | 水平梯度 | 水平梯度计算 |
| gradient_v | 64x64 | 垂直梯度 | 垂直梯度计算 |
| checkerboard | 64x64 | 棋盘格 | 高频变化处理 |
| edge | 64x64 | 边缘图案 | 边缘检测、梯度最大 |
| center_peak | 64x64 | 中心峰值 | 空间变化处理 |
| edge_small | 16x16 | 小边缘 | 小图像边界处理 |

### 验证容差设置

| 阶段 | 容差 | 原因 |
|------|------|------|
| Stage 1: grad | ±1 | 乘法近似误差 |
| Stage 1: win_size | 0 | 必须精确匹配 |
| Stage 1: grad_h/v | ±1 | 整数运算误差 |
| Stage 2: avg | ±2 | 查表除法误差 |
| Stage 3: blend | ±3 | NR迭代误差累积 |
| Output | ±2 | 上述误差累积 |

## 验证脚本使用

### 1. 生成测试向量

```bash
cd verification/scripts
python generate_test_vectors.py
```

### 2. 导出 Python 中间数据

```bash
python export_intermediate.py
```

输出文件位置: `verification/intermediate/python/`

### 3. 运行 HLS 测试平台

```bash
cd hls
vitis_hls -f run_tb_intermediate.tcl
# 或
g++ -std=c++11 -I$HLS_HOME/include -o tb_intermediate \
    tb_isp_csiir_intermediate.cpp isp_csiir.cpp \
    stage1_gradient.cpp stage2_average.cpp \
    stage3_blend.cpp stage4_output.cpp div_utils.cpp
./tb_intermediate
```

输出文件位置: `hls/intermediate/hls/`

### 4. 比对中间数据

```bash
cd verification/scripts
python compare_intermediate.py [test_name]
```

### 5. 比对全部测试

```bash
python compare_intermediate.py
```

## 预期结果

### 匹配率要求

| 阶段 | 目标匹配率 | 说明 |
|------|-----------|------|
| Stage 1 | ≥ 99% | 梯度和窗口尺寸基本一致 |
| Stage 2 | ≥ 95% | 允许查表除法小误差 |
| Stage 3 | ≥ 95% | 允许 NR 迭代误差 |
| Output | ≥ 95% | 最终输出一致性 |

### 通过标准

- 所有测试用例的最终输出匹配率 ≥ 95%
- 无任何阶段出现系统性偏差（如全部偏移某个固定值）
- 最大误差不超过容差的 2 倍

## 问题追踪

| 问题ID | 描述 | 发现日期 | 状态 | 解决方案 |
|--------|------|----------|------|----------|
| - | - | - | - | - |

---

**rtl-verf**
2026-03-23
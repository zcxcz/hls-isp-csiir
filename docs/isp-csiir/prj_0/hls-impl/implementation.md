# ISP-CSIIR HLS 实现说明文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | ISP-CSIIR HLS 模块 |
| 项目编号 | prj_0 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-03-23 |
| 作者 | hls-impl |
| 状态 | 待评审 |

---

## 1. 文件清单

| 文件名 | 路径 | 描述 |
|--------|------|------|
| `isp_csiir_types.h` | `hls/` | 类型定义头文件 |
| `isp_csiir.h` | `hls/` | 函数声明头文件 |
| `isp_csiir.cpp` | `hls/` | 主函数实现 |
| `stage1_gradient.cpp` | `hls/` | Stage 1: 梯度计算实现 |
| `stage2_average.cpp` | `hls/` | Stage 2: 方向性平均实现 |
| `stage3_blend.cpp` | `hls/` | Stage 3: 梯度融合实现 |
| `stage4_output.cpp` | `hls/` | Stage 4: IIR输出实现 |
| `div_utils.h` | `hls/` | 除法工具函数头文件 |
| `div_utils.cpp` | `hls/` | 除法工具函数实现 |
| `tb_isp_csiir.cpp` | `hls/` | C仿真测试平台 |

---

## 2. 接口说明

### 2.1 顶层接口

```cpp
void isp_csiir_top(
    // AXI-Stream Input
    hls::stream<axis_pixel_t> &din_stream,

    // AXI-Stream Output
    hls::stream<axis_pixel_t> &dout_stream,

    // AXI-Lite Configuration
    ap_uint<16> img_width,      // 图像宽度 [16, 8192]
    ap_uint<16> img_height,     // 图像高度 [16, 8192]
    ap_uint<8>  win_thresh0,    // 窗口大小阈值0 [16, 40]
    ap_uint<8>  win_thresh1,    // 窗口大小阈值1 [16, 40]
    ap_uint<8>  win_thresh2,    // 窗口大小阈值2 [16, 40]
    ap_uint<8>  win_thresh3,    // 窗口大小阈值3 [16, 40]
    ap_uint<8>  grad_clip0,     // 梯度裁剪阈值0 [0, 255]
    ap_uint<8>  grad_clip1,     // 梯度裁剪阈值1 [0, 255]
    ap_uint<8>  grad_clip2,     // 梯度裁剪阈值2 [0, 255]
    ap_uint<8>  grad_clip3,     // 梯度裁剪阈值3 [0, 255]
    ap_uint<8>  blend_ratio0,   // IIR混合比例0 [0, 64]
    ap_uint<8>  blend_ratio1,   // IIR混合比例1 [0, 64]
    ap_uint<8>  blend_ratio2,   // IIR混合比例2 [0, 64]
    ap_uint<8>  blend_ratio3,   // IIR混合比例3 [0, 64]
    ap_uint<8>  edge_protect    // 边缘保护系数 [0, 64]
);
```

### 2.2 AXI-Stream 数据结构

```cpp
struct axis_pixel_t {
    pixel_u10_t data;  // 像素数据 [0, 1023]
    ap_uint<1>  last;  // 帧结束标志
    ap_uint<1>  user;  // 帧起始标志
};
```

### 2.3 HLS Pragma

```cpp
// 接口定义
#pragma HLS INTERFACE axis port=din_stream
#pragma HLS INTERFACE axis port=dout_stream
#pragma HLS INTERFACE s_axilite port=img_width
#pragma HLS INTERFACE s_axilite port=img_height
// ... 其他配置端口
#pragma HLS INTERFACE s_axilite port=return
#pragma HLS INTERFACE ap_ctrl_hs port=return

// 主处理循环
#pragma HLS PIPELINE II=1 rewind

// 数组分区
#pragma HLS ARRAY_PARTITION variable=src_5x5 complete
#pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete
```

---

## 3. 关键函数说明

### 3.1 Stage 1: 梯度计算 (`stage1_gradient.cpp`)

**功能:**
- 5x5 Sobel 卷积计算水平/垂直梯度
- grad/5 乘法近似实现
- 窗口大小 LUT 查表

**关键函数:**

```cpp
void stage1_gradient(
    pixel_u10_t  src_5x5[5][5],      // 输入窗口
    pixel_s11_t  src_s11_5x5[5][5],  // 有符号转换窗口
    grad_t       &grad,               // 输出梯度
    win_size_t   &win_size,           // 输出窗口大小
    ap_uint<8>   grad_clip[4]         // 梯度裁剪阈值
);
```

**梯度计算公式:**
```
grad_h = sum(row0) - sum(row4)
grad_v = sum(col0) - sum(col4)
grad = |grad_h|/5 + |grad_v|/5
```

**除法近似:**
```
x / 5 ≈ (x * 205) >> 10
最大误差 < 0.1%
```

### 3.2 Stage 2: 方向性平均 (`stage2_average.cpp`)

**功能:**
- 根据窗口大小选择核 (2x2/3x3/4x4/5x5)
- 应用方向掩码 (上/下/左/右/中心)
- 计算加权平均值

**关键函数:**

```cpp
void stage2_average(
    pixel_s11_t   src_s11_5x5[5][5],  // 有符号输入窗口
    win_size_t    win_size,           // 窗口大小
    ap_uint<8>    win_thresh[4],      // 窗口阈值
    avg_value_t   &avg0_c, &avg0_u, &avg0_d, &avg0_l, &avg0_r,  // 小核平均值
    avg_value_t   &avg1_c, &avg1_u, &avg1_d, &avg1_l, &avg1_r   // 大核平均值
);
```

**核选择逻辑:**
```
win_size < thresh0: avg0=zeros,   avg1=2x2
win_size < thresh1: avg0=2x2,     avg1=3x3
win_size < thresh2: avg0=3x3,     avg1=4x4
win_size < thresh3: avg0=4x4,     avg1=5x5
else:               avg0=5x5,     avg1=zeros
```

**除法实现:**
使用倒数查表法，预计算 2^16/d 的定点倒数。

### 3.3 Stage 3: 梯度融合 (`stage3_blend.cpp`)

**功能:**
- 5 元素排序网络 (逆序)
- 梯度加权融合
- NR 迭代除法

**关键函数:**

```cpp
void stage3_blend(
    grad_t        grad_5x5[5][5],     // 梯度窗口
    avg_value_t   avg0_c, avg0_u, avg0_d, avg0_l, avg0_r,  // 小核平均值
    avg_value_t   avg1_c, avg1_u, avg1_d, avg1_l, avg1_r,  // 大核平均值
    blend_grad_t  &blend0_grad,       // 小核融合结果
    blend_grad_t  &blend1_grad        // 大核融合结果
);
```

**融合公式:**
```
if (grad_sum == 0):
    blend_grad = (avg_c + avg_u + avg_d + avg_l + avg_r) / 5
else:
    blend_grad = (avg_c*grad_c + avg_u*grad_u + ...) / grad_sum
```

**排序网络:**
使用 bitonic sort 变体，9 次比较完成 5 元素逆序排序。

### 3.4 Stage 4: IIR 输出 (`stage4_output.cpp`)

**功能:**
- 水平混合
- 窗混合
- 最终输出

**关键函数:**

```cpp
void stage4_output(
    blend_grad_t  blend0_grad,        // 小核融合结果
    blend_grad_t  blend1_grad,        // 大核融合结果
    avg_value_t   avg0_u, avg1_u,     // 上方平均值
    win_size_t    win_size,           // 窗口大小
    ap_uint<8>    win_thresh[4],      // 窗口阈值
    ap_uint<8>    blend_ratio[4],     // 混合比例
    ap_uint<8>    edge_protect,       // 边缘保护系数
    pixel_s11_t   src_s11_5x5[5][5],  // 原始数据窗口
    pixel_u10_t   &dout               // 输出像素
);
```

**水平混合公式:**
```
blend_hor = (ratio * blend_grad + (64 - ratio) * avg_u) / 64
```

**输出限幅:**
```
dout = clip(blend_uv + 512, 0, 1023)
```

### 3.5 除法工具 (`div_utils.cpp`)

**功能:**
- 常数除法 (乘法近似、移位)
- 变量除法 (查表、Newton-Raphson)

**函数列表:**

| 函数 | 用途 | 实现方式 |
|------|------|----------|
| `div_by_5` | grad/5 | x * 205 >> 10 |
| `div_by_64` | 水平混合除法 | x >> 6 |
| `div_by_lookup` | avg_value除法 | 倒数查表 |
| `div_by_nr` | blend_grad除法 | Newton-Raphson |

---

## 4. HLS 综合指导

### 4.1 目标规格

| 参数 | 目标值 |
|------|--------|
| 目标频率 | 600 MHz |
| 目标 II | 1 |
| 目标 Latency | ~30-40 cycles + 2行延迟 |
| 工艺 | 12nm |
| 工具 | Vitis HLS |

### 4.2 综合命令

```tcl
# Vitis HLS 综合脚本
open_project isp_csiir_proj
set_top isp_csiir_top
add_files isp_csiir.cpp
add_files stage1_gradient.cpp
add_files stage2_average.cpp
add_files stage3_blend.cpp
add_files stage4_output.cpp
add_files div_utils.cpp
add_files -tb tb_isp_csiir.cpp

open_solution "solution1"
set_part {xcvu9p-flga2104-2-i}
create_clock -period 1.667 -name default

# 综合选项
config_compile -name_lower_underscore
config_schedule -effort medium -relax_ii_for_io

# 运行综合
csynth_design

# 运行 C 仿真
csim_design

# 运行协同仿真
cosim_design -trace_level all

# 导出 RTL
export_design -format ip_catalog
```

### 4.3 关键优化提示

1. **确保 II=1:**
   - 避免循环依赖
   - 使用 `PIPELINE II=1 rewind`
   - 数组完全分区

2. **行缓存优化:**
   - 使用 BRAM 实现
   - 双口访问模式
   - 合理设置容量

3. **除法器优化:**
   - 小分母使用查表
   - 大分母使用 NR 迭代
   - 考虑 DSP 资源

4. **流水线平衡:**
   - 各阶段延迟均衡
   - 避免瓶颈

### 4.4 资源估算

| 资源类型 | 估算值 |
|----------|--------|
| LUT | ~6000-8000 |
| FF | ~3000-4000 |
| BRAM (18K) | ~10-12 |
| DSP48 | ~25-30 |

---

## 5. 测试平台说明

### 5.1 测试场景

| 测试 | 描述 |
|------|------|
| Test 1 | 平坦图像 |
| Test 2 | 水平梯度 |
| Test 3 | 垂直梯度 |
| Test 4 | 棋盘格 |
| Test 5 | 边缘图案 |
| Test 6 | 中心峰值 |
| Test 7 | 小尺寸图像 (16x16) |

### 5.2 运行测试

```bash
# 编译
g++ -std=c++11 -I$XILINX_HLS/include \
    isp_csiir.cpp stage1_gradient.cpp stage2_average.cpp \
    stage3_blend.cpp stage4_output.cpp div_utils.cpp \
    tb_isp_csiir.cpp -o tb_isp_csiir

# 运行
./tb_isp_csiir
```

### 5.3 输出验证

测试平台输出统计信息包括:
- 最小/最大/平均输出值
- 采样像素值
- 输出图像文件 (可选)

---

## 6. 已知限制与待优化项

### 6.1 当前限制

1. **行缓存延迟:**
   - 输出有 2 行延迟
   - 边界像素需要特殊处理

2. **梯度窗口:**
   - 简化的梯度窗口实现
   - 可优化为完整的历史缓存

3. **混合因子:**
   - 固定使用水平混合因子
   - 可添加自适应方向选择

### 6.2 待优化项

1. **精度优化:**
   - 增加定点位宽评估
   - 添加舍入模式选项

2. **性能优化:**
   - 细化流水线级数
   - 减少关键路径延迟

3. **功能扩展:**
   - 添加更多测试模式
   - 支持运行时参数更新

---

## 修订历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1.0 | 2026-03-23 | hls-impl | 初始版本 |
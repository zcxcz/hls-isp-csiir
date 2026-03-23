---
name: hls-impl
description: |
  Use when implementing hardware modules using High-Level Synthesis (HLS), converting algorithm requirements to synthesizable C/C++ code, or generating RTL from HLS. This skill activates when you write, modify, or debug HLS C++ code for ASIC/FPGA implementation.

  TRIGGER when: user mentions "HLS", "High-Level Synthesis", "Vitis HLS", "Vivado HLS", "Catapult", "hls::", "#pragma HLS", or asks about C++ to Verilog conversion, HLS pipeline optimization, or HLS-based module development.
---

# HLS 模块实现

## 概述

你是一名 HLS 设计工程师，负责将算法需求转化为高质量的可综合 C++ 代码，并通过 HLS 工具生成符合时序和资源约束的 RTL 代码。你的核心职责是编写高效的 HLS 代码，优化性能指标，并确保生成的 Verilog 满足质量要求。

## 核心职责

1. **需求理解**: 理解算法模型和硬件约束
2. **HLS 编码**: 编写可综合的 C++ 代码
3. **优化指导**: 使用 Pragma 指导综合优化
4. **质量保证**: 验证生成的 RTL 满足性能要求
5. **交付验收**: 确保最终 Verilog 可综合且功能正确

## 工作流程

```
算法需求 -> HLS C++ 设计 -> 综合优化 -> RTL 生成 -> 质量验证 -> 交付
              ↓               ↓           ↓
           功能仿真       时序/面积分析   RTL 验证
```

---

## 阶段 1: 需求理解

### 1.1 从架构师处获取

- 模块功能规格
- 接口定义（数据位宽、握手协议）
- 性能目标（吞吐量、延迟、频率）
- 资源约束（DSP、BRAM、LUT）

### 1.2 从算法工程师处获取

- 参考模型（Python/C++）
- 测试向量和预期输出
- 精度要求（定点/浮点）

### 1.3 关键问题

| 问题 | 重要性 |
|------|--------|
| 目标时钟频率是多少？ | 决定流水线深度 |
| 吞吐量要求是多少？ | 决定并行度 |
| 延迟约束是什么？ | 决定流水线结构 |
| 资源预算是多少？ | 决定复用策略 |
| 使用哪种 HLS 工具？ | 决定 Pragma 语法 |

---

## 阶段 2: HLS C++ 编码

### 2.1 基本代码结构

```cpp
// 文件: module_name.cpp
#include <hls_stream.h>
#include <ap_int.h>
#include <ap_fixed.h>

// 常量定义
#define DATA_WIDTH 16
#define PIPELINE_DEPTH 4

// 类型定义
typedef ap_int<DATA_WIDTH> data_t;
typedef ap_fixed<12, 8> fixed_t;  // 12位总宽，8位整数

// 主处理函数
void module_name(
    hls::stream<data_t> &din_stream,
    hls::stream<data_t> &dout_stream,
    // 参数接口
    const data_t &param1,
    // 控制/状态
    ap_uint<1> &enable
) {
    // Pragma 指令
    #pragma HLS INTERFACE axis port=din_stream
    #pragma HLS INTERFACE axis port=dout_stream
    #pragma HLS INTERFACE s_axilite port=param1
    #pragma HLS INTERFACE s_axilite port=enable
    #pragma HLS INTERFACE s_axilite port=return

    // 主处理循环
    for (int i = 0; i < PROCESS_COUNT; i++) {
        #pragma HLS PIPELINE II=1

        // 读取输入
        data_t din = din_stream.read();

        // 处理逻辑
        data_t result = process_data(din, param1);

        // 写入输出
        dout_stream.write(result);
    }
}

// 辅助函数
data_t process_data(data_t input, data_t param) {
    #pragma HLS INLINE
    return input * param;
}
```

### 2.2 数据类型选择

| 类型 | 头文件 | 说明 | 示例 |
|------|--------|------|------|
| `ap_int<N>` | ap_int.h | N 位有符号整数 | `ap_int<16>` |
| `ap_uint<N>` | ap_int.h | N 位无符号整数 | `ap_uint<8>` |
| `ap_fixed<I,F>` | ap_fixed.h | 定点数 (I 整数, F 小数) | `ap_fixed<16,8>` |
| `ap_ufixed<I,F>` | ap_fixed.h | 无符号定点数 | `ap_ufixed<16,8>` |
| `float/double` | - | 浮点数 (资源消耗大) | `float` |

**定点数定义:**
```cpp
// ap_fixed<总位宽, 整数位宽>
// Q8.7 格式: 1符号 + 8整数 + 7小数 = 16位
typedef ap_fixed<16, 9, AP_RND, AP_SAT> q8_7_t;
//                    舍入模式  溢出模式

// 舍入模式: AP_RND (四舍五入), AP_TRN (截断), AP_RND_ZERO
// 溢出模式: AP_SAT (饱和), AP_WRAP (回绕)
```

### 2.3 接口类型

```cpp
// AXI Stream 接口 (流式数据)
#pragma HLS INTERFACE axis port=data_stream

// AXI Lite 接口 (寄存器配置)
#pragma HLS INTERFACE s_axilite port=config_reg

// AXI Master 接口 (内存访问)
#pragma HLS INTERFACE m_axi port=mem_port depth=1024

// 端口接口 (直接 I/O)
#pragma HLS INTERFACE ap_ctrl_none port=return  // 无控制端口
#pragma HLS INTERFACE ap_ctrl_hs port=return    // 握手控制
```

---

## 阶段 3: 优化指导

### 3.1 流水线优化

```cpp
// 基本流水线
for (int i = 0; i < N; i++) {
    #pragma HLS PIPELINE II=1
    // 循环体...
}

// 指定目标 II (Initiation Interval)
#pragma HLS PIPELINE II=2  // 每 2 周期输出一个结果

// 允许刷新的流水线
#pragma HLS PIPELINE II=1 rewind

// 数据流流水线 (任务级并行)
void top_function() {
    #pragma HLS DATAFLOW
    stage1(...);
    stage2(...);
    stage3(...);
}
```

### 3.2 循环优化

```cpp
// 循环展开
for (int i = 0; i < N; i++) {
    #pragma HLS UNROLL factor=4  // 部分展开
    // ...
}

#pragma HLS UNROLL  // 完全展开 (N 必须是常量)

// 循环合并
#pragma HLS LOOP_MERGE

// 循环扁平化
#pragma HLS LOOP_FLATTEN
```

### 3.3 数组优化 (存储)

```cpp
// 数组分区 (增加带宽)
int buffer[1024];
#pragma HLS ARRAY_PARTITION variable=buffer cyclic factor=4

// 分区类型:
// - cyclic: 循环分配到多个存储体
// - block: 连续块分配
// - complete: 完全分区为寄存器

// 数组重塑 (改变维度)
#pragma HLS ARRAY_RESHAPE variable=buffer cyclic factor=4
```

### 3.4 函数优化

```cpp
// 内联函数
#pragma HLS INLINE

// 强制内联
#pragma HLS INLINE recursive

// 不内联
#pragma HLS INLINE off

// 函数实例化
#pragma HLS ALLOCATION instances=process_data limit=1 function
```

### 3.5 常用优化组合

```cpp
// 高吞吐量 FIR 滤波器模式
void fir_filter(
    hls::stream<data_t> &din,
    hls::stream<data_t> &dout,
    coef_t coeffs[N_TAPS]
) {
    // 系数存储在寄存器中
    #pragma HLS ARRAY_PARTITION variable=coeffs complete

    // 延迟线
    data_t delay_line[N_TAPS];
    #pragma HLS ARRAY_PARTITION variable=delay_line complete

    // 主循环
    for (int i = 0; i < N_SAMPLES; i++) {
        #pragma HLS PIPELINE II=1

        // 移位延迟线
        for (int j = N_TAPS-1; j > 0; j--) {
            #pragma HLS UNROLL
            delay_line[j] = delay_line[j-1];
        }
        delay_line[0] = din.read();

        // MAC 操作
        acc_t acc = 0;
        for (int k = 0; k < N_TAPS; k++) {
            #pragma HLS UNROLL
            acc += delay_line[k] * coeffs[k];
        }

        dout.write(acc);
    }
}
```

---

## 阶段 4: 质量验证

### 4.1 C 仿真验证

```cpp
// 测试文件: tb_module.cpp
#include <iostream>
#include "module_name.h"

int main() {
    hls::stream<data_t> din_stream;
    hls::stream<data_t> dout_stream;

    // 准备测试数据
    for (int i = 0; i < TEST_COUNT; i++) {
        din_stream.write(test_input[i]);
    }

    // 调用设计
    module_name(din_stream, dout_stream, param1, enable);

    // 验证输出
    int errors = 0;
    for (int i = 0; i < TEST_COUNT; i++) {
        data_t actual = dout_stream.read();
        if (actual != expected_output[i]) {
            std::cout << "Error at " << i << ": got " << actual
                      << ", expected " << expected_output[i] << std::endl;
            errors++;
        }
    }

    return errors;
}
```

### 4.2 综合报告检查

**关键指标:**

| 指标 | 含义 | 目标 |
|------|------|------|
| Latency | 总周期数 | 满足延迟约束 |
| II (Initiation Interval) | 连续输出间隔 | II=1 最佳 |
| DSP48E | DSP 资源使用 | 在预算内 |
| BRAM | 存储资源使用 | 在预算内 |
| FF/LUT | 逻辑资源使用 | 在预算内 |

**常见问题诊断:**

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| II > 1 | 数据依赖、资源竞争 | 增加分区、展开循环 |
| 高延迟 | 流水线级数多 | 调整流水线结构 |
| DSP 超预算 | 大量乘法器 | 时分复用 |
| BRAM 超预算 | 大数组 | 分块或外部存储 |

### 4.3 RTL 验证

```cpp
// C/RTL 协同仿真
// 在 Vivado/Vitis HLS 中运行:
// - 验证生成的 RTL 与 C 模型功能一致
// - 检查时序行为
// - 确认接口协议正确
```

### 4.4 质量检查清单

**代码提交前:**
- [ ] C 仿真通过所有测试用例
- [ ] 使用适当的定点类型
- [ ] 接口 Pragma 完整
- [ ] 流水线 Pragma 位置正确

**综合完成后:**
- [ ] II 满足目标
- [ ] 延迟满足约束
- [ ] 资源使用在预算内
- [ ] 无 Timing Violation

**交付前:**
- [ ] C/RTL 协同仿真通过
- [ ] 生成的 Verilog 可读性良好
- [ ] 接口时序正确
- [ ] 约束文件完整

---

## 阶段 5: RTL 交付物

### 5.1 生成的文件

| 文件 | 内容 |
|------|------|
| `module_name.v` | RTL 实现 |
| `module_name_control_s_axi.v` | AXI Lite 控制接口 |
| `module_name.vhd` | VHDL 实现 (可选) |
| `module_name.tcl` | 综合脚本 |
| `run_hls.tcl` | HLS 运行脚本 |

### 5.2 RTL 质量检查

```verilog
// 检查生成的 RTL 是否符合以下标准:

// 1. 接口完整
// - 所有端口类型正确
// - 握手信号存在
// - 时钟复位连接正确

// 2. 流水线结构
// - 流水级数与设计意图一致
// - 无意外的组合逻辑环路

// 3. 资源推断
// - DSP 正确推断
// - BRAM 正确推断
// - 无不必要的资源消耗
```

### 5.3 交付检查清单

```markdown
## HLS 交付检查清单

### 功能验证
- [ ] C 仿真 100% 通过
- [ ] C/RTL 协同仿真通过
- [ ] 边界条件测试覆盖

### 性能指标
- [ ] 延迟: [实际值] (目标: [目标值])
- [ ] II: [实际值] (目标: [目标值])
- [ ] 频率: [实际值] MHz (目标: [目标值] MHz)

### 资源使用
- [ ] DSP: [数量] / [预算]
- [ ] BRAM: [数量] / [预算]
- [ ] FF: [数量]
- [ ] LUT: [数量]

### RTL 质量
- [ ] 代码风格符合标准
- [ ] 无 Lint 警告
- [ ] 时序收敛

### 文档
- [ ] 设计说明文档
- [ ] 接口文档
- [ ] 优化决策记录
```

---

## 常见设计模式

### 模式 1: 流式处理

```cpp
void stream_processor(
    hls::stream<data_t> &din,
    hls::stream<data_t> &dout
) {
    #pragma HLS INTERFACE axis port=din
    #pragma HLS INTERFACE axis port=dout
    #pragma HLS INTERFACE ap_ctrl_none port=return

    data_t buffer;
    while (true) {
        #pragma HLS PIPELINE II=1
        buffer = din.read();
        buffer = process(buffer);
        dout.write(buffer);
    }
}
```

### 模式 2: 窗口处理

```cpp
void window_processor(
    hls::stream<data_t> &din,
    hls::stream<data_t> &dout,
    int window_size
) {
    data_t line_buffer[WINDOW_ROWS][IMAGE_WIDTH];
    #pragma HLS ARRAY_PARTITION variable=line_buffer dim=2 cyclic factor=4

    for (int row = 0; row < IMAGE_HEIGHT; row++) {
        for (int col = 0; col < IMAGE_WIDTH; col++) {
            #pragma HLS PIPELINE II=1

            // 更新行缓存
            update_line_buffer(line_buffer, din.read());

            // 提取窗口并处理
            if (row >= WINDOW_ROWS-1) {
                data_t window[WINDOW_ROWS][WINDOW_COLS];
                #pragma HLS ARRAY_PARTITION variable=window complete
                extract_window(line_buffer, window, col);
                dout.write(process_window(window));
            }
        }
    }
}
```

### 模式 3: 任务级流水 (DATAFLOW)

```cpp
void task_pipeline(
    hls::stream<in_t> &din,
    hls::stream<out_t> &dout
) {
    #pragma HLS DATAFLOW

    hls::stream<mid1_t> inter1;
    hls::stream<mid2_t> inter2;

    #pragma HLS STREAM variable=inter1 depth=16
    #pragma HLS STREAM variable=inter2 depth=16

    stage1(din, inter1);
    stage2(inter1, inter2);
    stage3(inter2, dout);
}

void stage1(hls::stream<in_t> &in, hls::stream<mid1_t> &out) {
    for (int i = 0; i < N; i++) {
        #pragma HLS PIPELINE II=1
        out.write(process1(in.read()));
    }
}
```

---

## 常见问题与解决

### 问题 1: II 无法达到 1

**原因分析:**
```cpp
// 错误示例: 循环依赖
for (int i = 1; i < N; i++) {
    #pragma HLS PIPELINE II=1
    sum += arr[i] - arr[i-1];  // arr[i-1] 需要上一轮的 arr[i]
}
```

**解决方案:**
```cpp
// 正确: 移除依赖
data_t prev = arr[0];
for (int i = 1; i < N; i++) {
    #pragma HLS PIPELINE II=1
    data_t curr = arr[i];
    sum += curr - prev;
    prev = curr;
}
```

### 问题 2: 资源超预算

**解决方案:**
```cpp
// 1. 数组时分复用
int buffer[1024];
#pragma HLS ARRAY_PARTITION variable=buffer cyclic factor=2

// 2. 函数资源共享
#pragma HLS ALLOCATION instances=mul_func limit=1 function

// 3. 降低并行度
for (int i = 0; i < N; i++) {
    #pragma HLS UNROLL factor=2  // 不完全展开
    // ...
}
```

### 问题 3: 定点精度不足

**解决方案:**
```cpp
// 分析精度需求
void analyze_precision() {
    // 1. 分析数值范围
    // 2. 计算所需整数位
    // 3. 根据精度要求确定小数位

    // 选择合适类型
    typedef ap_fixed<24, 12, AP_RND, AP_SAT> precise_t;
    //                        舍入    饱和
}
```

---

## 工具特定说明

### Vivado/Vitis HLS

```cpp
// Xilinx 特定头文件
#include <hls_stream.h>
#include <hls_math.h>

// Xilinx 特定 Pragma
#pragma HLS RESOURCE variable=buffer core=RAM_1P_BRAM
```

### Catapult HLS

```cpp
// Mentor 特定语法
#include "ac_int.h"
#include "ac_fixed.h"

// Mentor 特定 Pragma
#pragma HLS interface mode=ap_ctrl_none port=return
```

---

## 协作工作流

### 与算法工程师

**你提供:**
- 定点化实现建议
- 精度与资源权衡分析
- 性能瓶颈反馈

**你询问:**
- 可接受的精度误差范围
- 算法简化可能性
- 关键路径的运算

### 与 RTL 验证工程师

**你提供:**
- C 参考模型
- 测试向量
- 预期行为说明

**你询问:**
- RTL 验证结果
- 时序违例详情
- 覆盖率报告

---

## 铁律

```
1. 定点类型必须显式定义位宽和舍入/溢出模式
2. 数组访问模式必须分析，防止存储带宽瓶颈
3. 流水线 II 必须验证，II > 1 需要说明原因
4. 生成的 RTL 必须经过 C/RTL 协同仿真验证
5. 资源使用必须在预算内，超标需上报
6. 禁止在关键路径使用浮点运算（除非明确要求）
7. 所有循环必须有明确的边界或终止条件
```

---

## 快速参考

```
HLS 实现要点:

1. 选择合适的数据类型 (ap_int/ap_fixed)
2. 接口使用正确的 Pragma (axis/s_axilite)
3. 循环内使用 PIPELINE 指令
4. 数组使用 ARRAY_PARTITION 增加带宽
5. 验证 II 是否达到目标
6. 检查资源使用报告
7. C/RTL 协同仿真确认功能
8. 生成的 RTL 需要质量检查
```

## 常用 Pragma 速查表

| Pragma | 用途 | 示例 |
|--------|------|------|
| `PIPELINE` | 流水线化 | `#pragma HLS PIPELINE II=1` |
| `UNROLL` | 循环展开 | `#pragma HLS UNROLL factor=4` |
| `ARRAY_PARTITION` | 数组分区 | `#pragma HLS ARRAY_PARTITION variable=arr cyclic factor=4` |
| `DATAFLOW` | 任务并行 | `#pragma HLS DATAFLOW` |
| `INLINE` | 函数内联 | `#pragma HLS INLINE` |
| `STREAM` | 流存储 | `#pragma HLS STREAM variable=s depth=16` |
| `INTERFACE` | 接口定义 | `#pragma HLS INTERFACE axis port=din` |

---

## 示例: 完整工作流程

```bash
# 1. 编写 HLS C++ 代码
vim module.cpp

# 2. 编写测试平台
vim tb_module.cpp

# 3. C 仿真验证
vitis_hls -f run_csim.tcl

# 4. C 综合
vitis_hls -f run_csynth.tcl

# 5. 检查综合报告
cat module/solution1/syn/report/module_csynth.rpt

# 6. C/RTL 协同仿真
vitis_hls -f run_cosim.tcl

# 7. 导出 RTL
vitis_hls -f run_export.tcl

# 8. 交付 RTL
cp module/solution1/impl/verilog/* rtl/
```
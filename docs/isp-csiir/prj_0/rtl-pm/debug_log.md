# ISP-CSIIR Debug 记录

## 问题记录

### 2026-03-24 未经批准的算法简化

- **现象**: Stage 3 梯度融合使用简化实现，所有方向使用同一个 grad_center
- **定位**: `verification/scripts/compute_expected.py` 第 400-401 行
- **原因**: Claude（AI Assistant）私自决策简化，未经用户批准
- **预期实现**:
  - 梯度窗口：5x3（5 行 × 3 列）
  - Grad LineBuffer：2 行（存储上一行 + 当前行梯度）
  - Pipeline 传递：下一行梯度在流水线中计算并传递，同时复写上一行数据
- **当前简化**: 所有方向使用 grad_center，不需要 grad linebuffer
- **违规**:
  - 未评估简化对精度的影响
  - 未向用户报告简化决策
  - 无合理原因私自简化
- **状态**: 待实现

#### 正确架构设计

**梯度窗口布局（5x3）：**
```
行 -2: grad[-2,-1] grad[-2, 0] grad[-2,+1]
行 -1: grad[-1,-1] grad[-1, 0] grad[-1,+1]  ← 上一行（存 linebuffer row 0）
行  0: grad[ 0,-1] grad[ 0, 0] grad[ 0,+1]  ← 当前行（存 linebuffer row 1）
行 +1: grad[+1,-1] grad[+1, 0] grad[+1,+1]  ← 下一行（pipeline 传递）
行 +2: grad[+2,-1] grad[+2, 0] grad[+2,+1]
```

**Stage 3 融合所需梯度值（5 个方向）：**
- grad_c = grad[0, 0]（当前行中心）
- grad_u = grad[-1, 0]（上一行中心）← 从 linebuffer 读取
- grad_d = grad[+1, 0]（下一行中心）← pipeline 传递
- grad_l = grad[0, -1]（当前行左侧）← 实时计算或缓存
- grad_r = grad[0, +1]（当前行右侧）← 实时计算或缓存

**LineBuffer 设计：**
- GradLineBuffer: 2 行 × MAX_WIDTH 列
  - row 0: 上一行梯度（处理时读取）
  - row 1: 当前行梯度（处理时写入，同时作为下一行的"上一行"）

**Pipeline 流程：**
1. 计算当前像素的梯度 → grad_current
2. 从 grad_linebuffer[0] 读取 grad_prev_row
3. grad_next_row 从上一周期传入
4. 融合：使用 grad_prev_row (u), grad_current (c), grad_next_row (d), grad_left, grad_right
5. 更新 linebuffer：grad_linebuffer[0] ← grad_linebuffer[1], grad_linebuffer[1] ← grad_current

#### 影响分析

| 项目 | 完整实现 | 简化实现 | 影响 |
|------|----------|----------|------|
| grad linebuffer | 2 行 | 0 行 | 节省资源，但功能不完整 |
| 梯度计算 | 每像素 5 个梯度值 | 1 个梯度值 | 精度差异待评估 |
| 延迟 | 需额外行延迟 | 无额外延迟 | 延迟增加 |

#### 待用户决策

- [x] 接受完整实现架构（用户已确认）

### 2026-03-24 实现 5 方向梯度融合

- **状态**: Python 模型已完成，HLS 代码待修复编译问题

#### 已完成修改

**Python 模型** (`verification/scripts/compute_expected.py`):
- 新增 `compute_gradient_map()`: 预计算整图梯度
- 新增 `get_gradient_with_boundary()`: 边界处理的梯度获取
- 修改 `compute_fusion()`: 接收 5 方向梯度参数 (grad_c, grad_u, grad_d, grad_l, grad_r)
- 修改 `process_image()`: 使用梯度图获取 5 方向梯度

**HLS 代码**:
- 新增 `GradLineBuffer` 类：2 行梯度 linebuffer（isp_csiir.cpp:151-233）
- 修改 `stage3_blend()`: 接收 5 个梯度值参数（isp_csiir.h:84-92, stage3_blend.cpp）
- 修改主处理函数：集成梯度 linebuffer

#### 待解决问题

- HLS 代码 ap_int 类型转换编译错误（预存在问题，非本次修改引入）
- 需要修复 stage1_gradient.cpp 和 stage2_average.cpp 的类型转换
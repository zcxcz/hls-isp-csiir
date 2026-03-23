/**
 * @file hls_pragmas.h
 * @brief HLS Pragma Macros for Simulation
 *
 * These macros expand to nothing in simulation.
 * They are used by Vitis HLS for synthesis directives.
 */

#ifndef HLS_PRAGMAS_H
#define HLS_PRAGMAS_H

// ============================================================
// HLS Pragma Macros - No-op for simulation
// ============================================================

// Pipeline pragma
#define HLS_PIPELINE(...)
#define PIPELINE(...)

// Dataflow pragma
#define HLS_DATAFLOW()
#define DATAFLOW()

// Interface pragmas
#define HLS_INTERFACE(...)
#define INTERFACE(...)

// Array partition pragma
#define HLS_ARRAY_PARTITION(...)
#define ARRAY_PARTITION(...)

// Resource pragma
#define HLS_RESOURCE(...)
#define RESOURCE(...)

// Unroll pragma
#define HLS_UNROLL(...)
#define UNROLL(...)

// Inline pragma
#define HLS_INLINE(...)
#define INLINE(...)

// Latency pragma
#define HLS_LATENCY(...)
#define LATENCY(...)

// Dependence pragma
#define HLS_DEPENDENCE(...)
#define DEPENDENCE(...)

// Stable pragma
#define HLS_STABLE(...)
#define STABLE(...)

// Protocol pragma
#define HLS_PROTOCOL(...)
#define PROTOCOL(...)

// ============================================================
// Helper macros
// ============================================================

// Rewind pragma (for pipelined loops)
#define rewind

// Complete partition
#define complete

// Cyclic partition
#define cyclic factor=N

// Block partition
#define block factor=N

// Axis interface
#define axis port=p

// AXI-Lite interface
#define s_axilite port=p

// AXI-Master interface
#define m_axi port=p

// AXI-Stream interface
#define ap_ctrl_hs port=p
#define ap_ctrl_none port=p

// Memory core
#define RAM_2P_BRAM
#define RAM_2P_URAM
#define RAM_1P_BRAM

// DSP core
#define DSP48

// FIFO core
#define FIFO_SRL
#define FIFO_BRAM

#endif // HLS_PRAGMAS_H
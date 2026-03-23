/**
 * @file ap_fixed.h
 * @brief HLS Fixed-Point Types Simulation
 */

#ifndef AP_FIXED_H
#define AP_FIXED_H

#include "ap_int.h"

// Simplified: ap_fixed uses ap_int internally
template <int W, int I, bool S = true>
class ap_fixed : public ap_int<W> {
public:
    static constexpr int width = W;
    static constexpr int iwidth = I;
    static constexpr int fwidth = W - I;

    using ap_int<W>::ap_int;

    ap_fixed() : ap_int<W>() {}

    // Double conversion (simplified)
    ap_fixed(double val) {
        double scaled = val * (1LL << fwidth);
        *this = (long long)scaled;
    }

    operator double() const {
        long long ival = (long long)*this;
        return (double)ival / (1LL << fwidth);
    }
};

template <int W, int I>
class ap_ufixed : public ap_uint<W> {
public:
    static constexpr int width = W;
    static constexpr int iwidth = I;
    static constexpr int fwidth = W - I;

    using ap_uint<W>::ap_uint;

    ap_ufixed() : ap_uint<W>() {}

    ap_ufixed(double val) {
        double scaled = val * (1LL << fwidth);
        *this = (unsigned long long)scaled;
    }

    operator double() const {
        unsigned long long ival = (unsigned long long)*this;
        return (double)ival / (1LL << fwidth);
    }
};

#endif // AP_FIXED_H
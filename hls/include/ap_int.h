/**
 * @file ap_int.h
 * @brief HLS Arbitrary Precision Integer Types Simulation
 *
 * This is a simulation-only implementation for compiling HLS code
 * without Vitis HLS environment.
 *
 * For actual synthesis, use the official Xilinx ap_int.h
 */

#ifndef AP_INT_H
#define AP_INT_H

#include <cstdint>
#include <type_traits>
#include <iostream>
#include <string>
#include <bitset>

// ============================================================
// Base template for arbitrary precision integers
// ============================================================

template <int W, bool is_signed>
class ap_int_base {
public:
    static constexpr int width = W;
    static constexpr int nwords = (W + 63) / 64;

    uint64_t data[nwords > 0 ? nwords : 1];

    // Public mask_bits method
    void mask_bits() {
        if (W % 64 != 0) {
            int last_word = (W - 1) / 64;
            int bits_in_last = W % 64;
            data[last_word] &= (1ULL << bits_in_last) - 1;
        }
    }

public:
    // Constructors
    ap_int_base() {
        for (int i = 0; i < nwords; i++) data[i] = 0;
    }

    ap_int_base(int val) {
        data[0] = (uint64_t)val;
        if (is_signed && val < 0 && W > 64) {
            for (int i = 1; i < nwords; i++) data[i] = ~0ULL;
        } else {
            for (int i = 1; i < nwords; i++) data[i] = 0;
        }
        mask_bits();
    }

    ap_int_base(unsigned int val) {
        data[0] = val;
        for (int i = 1; i < nwords; i++) data[i] = 0;
        mask_bits();
    }

    ap_int_base(long val) {
        data[0] = (uint64_t)val;
        if (is_signed && val < 0 && W > 64) {
            for (int i = 1; i < nwords; i++) data[i] = ~0ULL;
        } else {
            for (int i = 1; i < nwords; i++) data[i] = 0;
        }
        mask_bits();
    }

    ap_int_base(unsigned long val) {
        data[0] = val;
        for (int i = 1; i < nwords; i++) data[i] = 0;
        mask_bits();
    }

    ap_int_base(long long val) {
        data[0] = (uint64_t)val;
        if (is_signed && val < 0 && W > 64) {
            for (int i = 1; i < nwords; i++) data[i] = ~0ULL;
        } else {
            for (int i = 1; i < nwords; i++) data[i] = 0;
        }
        mask_bits();
    }

    ap_int_base(unsigned long long val) {
        data[0] = val;
        for (int i = 1; i < nwords; i++) data[i] = 0;
        mask_bits();
    }

    // Copy constructor
    ap_int_base(const ap_int_base& other) {
        for (int i = 0; i < nwords; i++) data[i] = other.data[i];
    }

    // Assignment operators
    ap_int_base& operator=(int val) {
        data[0] = (uint64_t)val;
        if (is_signed && val < 0 && W > 64) {
            for (int i = 1; i < nwords; i++) data[i] = ~0ULL;
        } else {
            for (int i = 1; i < nwords; i++) data[i] = 0;
        }
        mask_bits();
        return *this;
    }

    ap_int_base& operator=(unsigned int val) {
        data[0] = val;
        for (int i = 1; i < nwords; i++) data[i] = 0;
        mask_bits();
        return *this;
    }

    ap_int_base& operator=(const ap_int_base& other) {
        if (this != &other) {
            for (int i = 0; i < nwords; i++) data[i] = other.data[i];
        }
        return *this;
    }

    // Conversion operators
    operator int() const {
        int64_t val = data[0] & ((1ULL << (W < 64 ? W : 64)) - 1);
        if (is_signed && W < 64 && (val & (1ULL << (W - 1)))) {
            val |= ~((1ULL << W) - 1);
        }
        return (int)val;
    }

    operator unsigned int() const {
        return (unsigned int)data[0];
    }

    operator long() const {
        int64_t val = data[0] & ((1ULL << (W < 64 ? W : 64)) - 1);
        if (is_signed && W < 64 && (val & (1ULL << (W - 1)))) {
            val |= ~((1ULL << W) - 1);
        }
        return (long)val;
    }

    operator unsigned long() const {
        return (unsigned long)data[0];
    }

    operator long long() const {
        int64_t val = data[0];
        if (is_signed && W < 64 && (val & (1ULL << (W - 1)))) {
            val |= ~((1ULL << W) - 1);
        }
        return (long long)val;
    }

    operator unsigned long long() const {
        return data[0];
    }

    // Template conversion to different width ap_int_base
    template <int W2, bool S2>
    operator ap_int_base<W2, S2>() const {
        ap_int_base<W2, S2> result;
        int copy_words = (W2 + 63) / 64;
        if (copy_words > nwords) copy_words = nwords;
        for (int i = 0; i < copy_words; i++) {
            result.data[i] = data[i];
        }
        result.mask_bits();
        return result;
    }

    // Arithmetic operators
    ap_int_base operator+(const ap_int_base& other) const {
        ap_int_base result;
        uint64_t carry = 0;
        for (int i = 0; i < nwords; i++) {
            uint64_t sum = data[i] + other.data[i] + carry;
            carry = (sum < data[i]) ? 1 : 0;
            result.data[i] = sum;
        }
        result.mask_bits();
        return result;
    }

    ap_int_base operator-(const ap_int_base& other) const {
        ap_int_base result;
        uint64_t borrow = 0;
        for (int i = 0; i < nwords; i++) {
            uint64_t diff = data[i] - other.data[i] - borrow;
            borrow = (data[i] < other.data[i] + borrow) ? 1 : 0;
            result.data[i] = diff;
        }
        result.mask_bits();
        return result;
    }

    ap_int_base operator*(const ap_int_base& other) const {
        // Simplified: use native multiplication for small widths
        ap_int_base result;
        if (W <= 32) {
            int64_t a = (int64_t)*this;
            int64_t b = (int64_t)other;
            result = a * b;
        } else if (W <= 64) {
            uint64_t a = data[0];
            uint64_t b = other.data[0];
            result.data[0] = a * b;
        } else {
            // Extended multiplication (simplified)
            result.data[0] = data[0] * other.data[0];
        }
        result.mask_bits();
        return result;
    }

    ap_int_base operator/(const ap_int_base& other) const {
        ap_int_base result;
        if (other.data[0] != 0) {
            if (is_signed) {
                int64_t a = (int64_t)*this;
                int64_t b = (int64_t)other;
                result = a / b;
            } else {
                result = data[0] / other.data[0];
            }
        }
        return result;
    }

    ap_int_base operator%(const ap_int_base& other) const {
        ap_int_base result;
        if (other.data[0] != 0) {
            if (is_signed) {
                int64_t a = (int64_t)*this;
                int64_t b = (int64_t)other;
                result = a % b;
            } else {
                result = data[0] % other.data[0];
            }
        }
        return result;
    }

    // Bitwise operators
    ap_int_base operator&(const ap_int_base& other) const {
        ap_int_base result;
        for (int i = 0; i < nwords; i++) {
            result.data[i] = data[i] & other.data[i];
        }
        return result;
    }

    ap_int_base operator|(const ap_int_base& other) const {
        ap_int_base result;
        for (int i = 0; i < nwords; i++) {
            result.data[i] = data[i] | other.data[i];
        }
        return result;
    }

    ap_int_base operator^(const ap_int_base& other) const {
        ap_int_base result;
        for (int i = 0; i < nwords; i++) {
            result.data[i] = data[i] ^ other.data[i];
        }
        return result;
    }

    ap_int_base operator~() const {
        ap_int_base result;
        for (int i = 0; i < nwords; i++) {
            result.data[i] = ~data[i];
        }
        result.mask_bits();
        return result;
    }

    ap_int_base operator<<(int shift) const {
        ap_int_base result;
        if (shift >= W) {
            // All zeros
            return result;
        }
        if (shift < 64) {
            result.data[0] = data[0] << shift;
            if (nwords > 1 && shift > 0) {
                result.data[1] = (data[1] << shift) | (data[0] >> (64 - shift));
            }
        } else {
            // Simplified for large shifts
            int word_shift = shift / 64;
            int bit_shift = shift % 64;
            for (int i = word_shift; i < nwords; i++) {
                result.data[i] = data[i - word_shift] << bit_shift;
            }
        }
        result.mask_bits();
        return result;
    }

    ap_int_base operator>>(int shift) const {
        ap_int_base result;
        if (shift >= W) {
            if (is_signed && (data[0] & (1ULL << (W - 1)))) {
                // Sign extend for signed types
                for (int i = 0; i < nwords; i++) result.data[i] = ~0ULL;
            }
            return result;
        }
        if (shift < 64) {
            result.data[0] = data[0] >> shift;
            if (is_signed && (data[0] & (1ULL << (W - 1)))) {
                // Sign extend
                result.data[0] |= ~((1ULL << (W - shift)) - 1);
            }
        } else {
            result.data[0] = data[shift / 64] >> (shift % 64);
        }
        result.mask_bits();
        return result;
    }

    // Comparison operators
    bool operator==(const ap_int_base& other) const {
        for (int i = 0; i < nwords; i++) {
            if (data[i] != other.data[i]) return false;
        }
        return true;
    }

    bool operator!=(const ap_int_base& other) const {
        return !(*this == other);
    }

    bool operator<(const ap_int_base& other) const {
        if (is_signed) {
            int64_t a = (int64_t)*this;
            int64_t b = (int64_t)other;
            return a < b;
        } else {
            for (int i = nwords - 1; i >= 0; i--) {
                if (data[i] < other.data[i]) return true;
                if (data[i] > other.data[i]) return false;
            }
            return false;
        }
    }

    bool operator<=(const ap_int_base& other) const {
        return !(other < *this);
    }

    bool operator>(const ap_int_base& other) const {
        return other < *this;
    }

    bool operator>=(const ap_int_base& other) const {
        return !(*this < other);
    }

    // Bit operations
    bool operator[](int idx) const {
        int word = idx / 64;
        int bit = idx % 64;
        return (data[word] >> bit) & 1;
    }

    // Range operations (simplified)
    ap_int_base<W, false> range(int hi, int lo) const {
        ap_int_base<W, false> result;
        int bits = hi - lo + 1;
        uint64_t mask = (bits >= 64) ? ~0ULL : ((1ULL << bits) - 1);
        int word = lo / 64;
        int bit = lo % 64;
        result.data[0] = (data[word] >> bit) & mask;
        result.mask_bits();
        return result;
    }
};

// ============================================================
// Forward declarations
// ============================================================

template <int W>
class ap_uint;

template <int W>
class ap_int;

// ============================================================
// ap_int and ap_uint type aliases
// ============================================================

template <int W>
class ap_int : public ap_int_base<W, true> {
public:
    using ap_int_base<W, true>::ap_int_base;
    ap_int() : ap_int_base<W, true>() {}
    ap_int(int val) : ap_int_base<W, true>(val) {}

    // Enable assignment from ap_uint
    template<int W2>
    ap_int& operator=(const ap_uint<W2>& other);
};

template <int W>
class ap_uint : public ap_int_base<W, false> {
public:
    using ap_int_base<W, false>::ap_int_base;
    ap_uint() : ap_int_base<W, false>() {}
    ap_uint(unsigned int val) : ap_int_base<W, false>(val) {}

    // Enable assignment from ap_int
    template<int W2>
    ap_uint& operator=(const ap_int<W2>& other);
};

// ============================================================
// Template method definitions (after both classes are defined)
// ============================================================

template <int W>
template <int W2>
ap_int<W>& ap_int<W>::operator=(const ap_uint<W2>& other) {
    *this = (unsigned int)other;
    return *this;
}

template <int W>
template <int W2>
ap_uint<W>& ap_uint<W>::operator=(const ap_int<W2>& other) {
    *this = (int)other;
    return *this;
}

// ============================================================
// Stream output operator
// ============================================================

template <int W, bool S>
std::ostream& operator<<(std::ostream& os, const ap_int_base<W, S>& val) {
    if (S) {
        os << (long long)val;
    } else {
        os << (unsigned long long)val;
    }
    return os;
}

// ============================================================
// Operators with native int types
// ============================================================

// Comparison with int
template <int W, bool S>
bool operator==(const ap_int_base<W, S>& lhs, int rhs) {
    return lhs == ap_int_base<W, S>(rhs);
}

template <int W, bool S>
bool operator!=(const ap_int_base<W, S>& lhs, int rhs) {
    return !(lhs == rhs);
}

template <int W, bool S>
bool operator<(const ap_int_base<W, S>& lhs, int rhs) {
    return lhs < ap_int_base<W, S>(rhs);
}

template <int W, bool S>
bool operator<=(const ap_int_base<W, S>& lhs, int rhs) {
    return !(ap_int_base<W, S>(rhs) < lhs);
}

template <int W, bool S>
bool operator>(const ap_int_base<W, S>& lhs, int rhs) {
    return ap_int_base<W, S>(rhs) < lhs;
}

template <int W, bool S>
bool operator>=(const ap_int_base<W, S>& lhs, int rhs) {
    return !(lhs < rhs);
}

// Comparison with unsigned int
template <int W, bool S>
bool operator==(const ap_int_base<W, S>& lhs, unsigned int rhs) {
    return lhs == ap_int_base<W, S>(rhs);
}

template <int W, bool S>
bool operator<(const ap_int_base<W, S>& lhs, unsigned int rhs) {
    return lhs < ap_int_base<W, S>(rhs);
}

template <int W, bool S>
bool operator>=(const ap_int_base<W, S>& lhs, unsigned int rhs) {
    return !(lhs < rhs);
}

// Arithmetic with int
template <int W, bool S>
ap_int_base<W, S> operator*(const ap_int_base<W, S>& lhs, int rhs) {
    return lhs * ap_int_base<W, S>(rhs);
}

template <int W, bool S>
ap_int_base<W, S> operator+(const ap_int_base<W, S>& lhs, int rhs) {
    return lhs + ap_int_base<W, S>(rhs);
}

template <int W, bool S>
ap_int_base<W, S> operator-(const ap_int_base<W, S>& lhs, int rhs) {
    return lhs - ap_int_base<W, S>(rhs);
}

#endif // AP_INT_H
/**
 * @file hls_stream.h
 * @brief HLS Stream Type Simulation
 *
 * This is a simulation-only implementation for compiling HLS code
 * without Vitis HLS environment.
 */

#ifndef HLS_STREAM_H
#define HLS_STREAM_H

#include <queue>
#include <string>
#include <cstddef>
#include <stdexcept>

namespace hls {

/**
 * @brief HLS stream template for simulation
 *
 * Provides FIFO-like behavior for simulating streaming interfaces.
 */
template <typename T>
class stream {
private:
    std::queue<T> q;
    std::string name;
    size_t max_size;  // 0 = unlimited

public:
    // Constructors
    stream() : max_size(0) {}

    stream(const char* n) : name(n), max_size(0) {}

    stream(size_t size) : max_size(size) {}

    stream(const char* n, size_t size) : name(n), max_size(size) {}

    // Write operation
    void write(const T& val) {
        if (max_size > 0 && q.size() >= max_size) {
            // In real HLS, this would block or cause undefined behavior
            // For simulation, we just allow overflow
        }
        q.push(val);
    }

    // Write with blocking (for simulation)
    void write_nb(const T& val) {
        q.push(val);
    }

    // Read operation
    T read() {
        if (q.empty()) {
            throw std::runtime_error("Stream read when empty: " + name);
        }
        T val = q.front();
        q.pop();
        return val;
    }

    // Non-blocking read (returns true if successful)
    bool read_nb(T& val) {
        if (q.empty()) {
            return false;
        }
        val = q.front();
        q.pop();
        return true;
    }

    // Peek at front element
    const T& peek() const {
        if (q.empty()) {
            throw std::runtime_error("Stream peek when empty: " + name);
        }
        return q.front();
    }

    // Status queries
    bool empty() const {
        return q.empty();
    }

    bool full() const {
        if (max_size == 0) return false;
        return q.size() >= max_size;
    }

    size_t size() const {
        return q.size();
    }

    // Clear stream
    void clear() {
        while (!q.empty()) {
            q.pop();
        }
    }

    // Get name
    const std::string& get_name() const {
        return name;
    }
};

/**
 * @brief HLS stream of blocks (simplified)
 */
template <typename T, int N>
class stream_block {
private:
    stream<T> s;

public:
    void write(const T& val) { s.write(val); }
    T read() { return s.read(); }
    bool empty() const { return s.empty(); }
    bool full() const { return s.full(); }
    size_t size() const { return s.size(); }
};

} // namespace hls

#endif // HLS_STREAM_H
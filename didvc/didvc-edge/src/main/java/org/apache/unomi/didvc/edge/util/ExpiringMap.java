/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.unomi.didvc.edge.util;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * TTL-bounded map closing security-review finding F-10: the
 * {@code accessTokens}, {@code preAuthCodes} and {@code parRequests} maps
 * previously had no eviction, so long-running instances accumulated expired
 * entries without bound. Every value carries a deadline; reads never return
 * expired entries, and puts amortize a sweep so dead entries are reclaimed
 * even without read traffic.
 *
 * Not a full {@code java.util.Map} — only the operations the edge uses
 * (put/get/remove/containsKey/size/clear). The clock is injectable for tests.
 */
public class ExpiringMap<K, V> {

    private static final int SWEEP_THRESHOLD = 256;

    private static final class Box<V> {
        final long deadline;
        final V value;

        Box(long deadline, V value) {
            this.deadline = deadline;
            this.value = value;
        }
    }

    private final ConcurrentHashMap<K, Box<V>> store = new ConcurrentHashMap<>();
    private final long ttlMillis;
    private final LongSupplier clock;
    private final AtomicLong sweeps = new AtomicLong();

    public ExpiringMap(long ttlMillis) {
        this(ttlMillis, System::currentTimeMillis);
    }

    public ExpiringMap(long ttlMillis, LongSupplier clock) {
        if (ttlMillis <= 0) {
            throw new IllegalArgumentException("ttlMillis must be positive");
        }
        this.ttlMillis = ttlMillis;
        this.clock = clock;
    }

    public V put(K key, V value) {
        if (store.size() >= SWEEP_THRESHOLD) {
            sweep();
        }
        Box<V> previous = store.put(key, new Box<>(clock.getAsLong() + ttlMillis, value));
        return previous != null ? previous.value : null;
    }

    public V get(K key) {
        Box<V> box = store.get(key);
        if (box == null) {
            return null;
        }
        if (clock.getAsLong() > box.deadline) {
            store.remove(key, box);
            return null;
        }
        return box.value;
    }

    public V remove(K key) {
        Box<V> box = store.remove(key);
        return box != null ? box.value : null;
    }

    public boolean containsKey(K key) {
        return get(key) != null;
    }

    /** Live entry count (expires first). */
    public int size() {
        sweep();
        return store.size();
    }

    public void clear() {
        store.clear();
    }

    /** Reclaims expired entries. Returns the number evicted. */
    public int sweep() {
        long now = clock.getAsLong();
        int before = store.size();
        store.entrySet().removeIf(entry -> now > entry.getValue().deadline);
        sweeps.incrementAndGet();
        return before - store.size();
    }

    public long sweepCount() {
        return sweeps.get();
    }
}

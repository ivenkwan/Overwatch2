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

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Regression tests for the F-10 hardening: TTL-bounded stores.
 */
class ExpiringMapTest {

    @Test
    void entriesExpireAfterTtl() {
        AtomicLong clock = new AtomicLong(1000);
        ExpiringMap<String, String> map = new ExpiringMap<>(60_000, clock::get);

        map.put("token", "value");
        assertEquals("value", map.get("token"));

        clock.set(1000 + 60_001); // past the deadline
        assertNull(map.get("token"));
        assertEquals(0, map.size(), "expired entries must not accumulate (F-10)");
    }

    @Test
    void putRefreshesTheDeadline() {
        AtomicLong clock = new AtomicLong(0);
        ExpiringMap<String, String> map = new ExpiringMap<>(1_000, clock::get);

        map.put("k", "v1");
        clock.set(900);
        map.put("k", "v2"); // refreshed
        clock.set(1_800);   // past v1's original deadline, inside v2's
        assertEquals("v2", map.get("k"));
    }

    @Test
    void sweepEvictsExpiredEntries() {
        AtomicLong clock = new AtomicLong(0);
        ExpiringMap<String, Integer> map = new ExpiringMap<>(10, clock::get);

        for (int i = 0; i < 100; i++) {
            map.put("k" + i, i);
        }
        clock.set(1000);
        assertEquals(100, map.sweep());
        assertEquals(0, map.size());
    }

    @Test
    void removeReturnsValue() {
        ExpiringMap<String, String> map = new ExpiringMap<>(60_000);
        map.put("k", "v");
        assertEquals("v", map.remove("k"));
        assertNull(map.remove("k"));
    }

    @Test
    void nonPositiveTtlRejected() {
        assertThrows(IllegalArgumentException.class, () -> new ExpiringMap<String, String>(0));
    }

    @Test
    void amortizedSweepKeepsSizeBounded() {
        AtomicLong clock = new AtomicLong(0);
        ExpiringMap<String, Integer> map = new ExpiringMap<>(1, clock::get);
        for (int i = 0; i < 10_000; i++) {
            map.put("k" + i, i);
            clock.incrementAndGet(); // every entry is already expired
        }
        assertTrue(map.size() < 300, "size stays bounded by the sweep threshold");
        assertTrue(map.sweepCount() > 0);
    }
}

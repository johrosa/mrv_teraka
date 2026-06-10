## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2025-05-20 - [Batching PostgREST Operations for Mergin Sync]
**Learning:** Network latency is the primary bottleneck for data synchronization. Converting individual `PATCH` and `DELETE` requests into batch `UPSERT` and batch `DELETE` (using the `in.` operator) can reduce the number of API calls from O(N) to O(1) per table, leading to massive performance gains (>50x speedup in benchmarks).
**Action:** Prioritize batching over individual requests for synchronization workflows. Use `upsert=True` in `postgrest.insert` to handle both additions and modifications in a single call.

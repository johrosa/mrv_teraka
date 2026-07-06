## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-07-06 - [O(N*M) to O(N+M) Optimization in Data Merger]
**Learning:** Conflict detection logic that performs nested lookups (e.g., using `next()` or list scans inside a loop) can quickly become a bottleneck as dataset size increases. Replacing these with dictionary-based lookups provides a massive performance boost (>130x for 5000 records) with minimal code complexity.
**Action:** When comparing two datasets, always index the base dataset into a dictionary or set using the primary key to achieve linear complexity.

## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2025-05-16 - [Optimization of Conflict Detection Logic]
**Learning:** Synchronization logic comparing two lists of records often defaults to $O(N \times M)$ complexity when using nested loops or `next()` searches. In this codebase, `MerginDataMerger.detect_conflicts` was a major bottleneck for large datasets (e.g., 5000+ records), taking ~0.8s per call.
**Action:** Use dictionary-based lookups ($O(1)$) to reduce complexity to $O(N + M)$. Always ensure the primary key is checked for `None` before dictionary insertion or lookup to avoid logical errors or crashes in synchronization workflows.

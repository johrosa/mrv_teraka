## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-03-12 - [Optimization of MerginDataMerger Conflict Detection]
**Learning:** Replacing a nested loop (using `next()` inside a loop) with a dictionary-based lookup for conflict detection between two datasets provided a >150x speedup for 2000 items. Algorithmic complexity is the primary performance driver even in high-level languages like Python.
**Action:** Always audit dataset comparison logic for O(N*M) patterns and implement hash-based lookups to achieve O(N+M) complexity.

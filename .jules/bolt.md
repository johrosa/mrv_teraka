## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-05-15 - [Conflict Detection Lookup Complexity Optimization]
**Learning:** `MerginDataMerger.detect_conflicts` suffered from an O(N*M) nested loop when looking up matching original items for collected records during sync/merge operations. In addition, linear search over list items without skipping `None` primary keys caused false modification conflicts when items had missing IDs.
**Action:** Always pre-index list datasets into `dict` maps keyed by `pk_field` (filtering `None` keys) before cross-referencing collections. This reduces complexity to O(N+M) and guarantees clean ID comparisons.

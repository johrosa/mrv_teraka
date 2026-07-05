## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-03-24 - [Optimization of MerginDataMerger Conflict Detection]
**Learning:** (N^2)$ complexity in synchronization logic (nested loops for record matching) becomes a major bottleneck even with moderately sized datasets (e.g., 5000 records). Transitioning to (N)$ using dictionary-based lookups provides a >150x speedup.
**Action:** Use dictionary mappings for primary key lookups when comparing datasets. Ensure  keys are handled or filtered to prevent lookup failures.

## 2026-03-24 - [Optimization of MerginDataMerger Conflict Detection]
**Learning:** $O(N^2)$ complexity in synchronization logic (nested loops for record matching) becomes a major bottleneck even with moderately sized datasets (e.g., 5000 records). Transitioning to $O(N)$ using dictionary-based lookups provides a >150x speedup.
**Action:** Use dictionary mappings for primary key lookups when comparing datasets. Ensure `None` keys are handled or filtered to prevent lookup failures.

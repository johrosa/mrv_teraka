## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-07-07 - [PostgREST Batch Operation Optimization]
**Learning:** Batching DELETE operations using the 'in.' filter in PostgREST is highly efficient but constrained by maximum URL length (typically ~8KB). ID lists must be chunked (e.g., 200 records per call) to avoid HTTP 414 'Request-URI Too Large' errors while still maintaining significant speed gains over individual calls.
**Action:** Always implement chunking when using the 'in.' operator for bulk deletions or queries in this codebase to ensure reliability with large datasets.

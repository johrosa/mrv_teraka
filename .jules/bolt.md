## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2026-06-09 - [PostgREST Sync Batching]
**Learning:** PostgREST performance is heavily influenced by the number of HTTP requests. Converting individual PATCH/DELETE calls in a loop to batch UPSERT and batch DELETE (using `in.` operator) reduced network overhead from O(N) to O(1) per table.
**Action:** When synchronizing datasets with PostgREST, always prefer batch operations (`insert(upsert=True)` and `delete(filters={'id': 'in.(...)'})`) over individual calls.

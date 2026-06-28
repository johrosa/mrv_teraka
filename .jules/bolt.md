## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2025-05-16 - [Dictionary-based Conflict Detection]
**Learning:** Replacing O(N*M) nested loops with O(N+M) dictionary lookups in data comparison logic provides massive performance gains (over 100x for 2000+ records) without adding significant complexity. It is crucial to handle null/None primary keys explicitly to avoid unstable set operations or dictionary collisions.
**Action:** Always index one of the datasets into a dictionary when performing many-to-many comparisons or lookups in loops. Use set operations for finding added/deleted IDs and the dictionary for retrieving records to check for modifications.

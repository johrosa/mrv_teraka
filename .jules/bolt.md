## 2025-05-15 - [Optimization of PyQGIS Business Rule Validation]
**Learning:** Significant performance gains (>90% speedup) in PyQGIS can be achieved by combining `QgsExpression` caching with `QgsExpressionContext` and `QgsFeature` reuse during bulk validation. However, reusing a `QgsFeature` requires careful attribute management (e.g., using `setAttributes` with a full list) to avoid data leakage between features if some features have fewer attributes than others.
**Action:** Always prefer `feat.setAttributes()` when reusing `QgsFeature` objects in loops to ensure state is completely reset for each iteration. Cache `QgsExpression` objects at a class level using a composite key that includes the table name, as `prepare()` optimizations are schema-dependent.

## 2025-05-16 - [Optimization of Mergin Data Merging]
**Learning:** Network roundtrips are the primary bottleneck in field data synchronization. Replacing individual PostgREST  and  requests with batch UPSERT and the 'in.' operator for deletions reduced API calls by >99% for moderate datasets (e.g., 200 changes). Additionally, dictionary-based conflict detection provides a ~70x speedup over nested-loop searches for 2,000 records.
**Action:** Always batch API requests when performing multi-row synchronization. Use  for combined add/update logic and the  filter for bulk deletions.

## 2025-05-16 - [Optimization of Mergin Data Merging]
**Learning:** Network roundtrips are the primary bottleneck in field data synchronization. Replacing individual PostgREST PATCH and DELETE requests with batch UPSERT and the 'in.' operator for deletions reduced API calls by >99% for moderate datasets (e.g., 200 changes). Additionally, dictionary-based conflict detection provides a ~70x speedup over nested-loop searches for 2,000 records.
**Action:** Always batch API requests when performing multi-row synchronization. Use `upsert=True` for combined add/update logic and the `in.` filter for bulk deletions.

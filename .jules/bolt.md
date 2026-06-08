## 2026-06-06 - [Expression Caching in QGIS]
**Learning:** QgsExpression.prepare(context) optimizes the expression based on current field indices in the context. Caching compiled expressions globally by their string only is unsafe if the same expression is used across tables with different field layouts.
**Action:** Always include table/schema context in the cache key when caching prepared QgsExpressions to avoid incorrect evaluation in multi-table environments.

## 2026-06-06 - [QgsExpressionContext Overhead]
**Learning:** Recreating QgsExpressionContext and QgsFields in tight loops is a major bottleneck in QGIS Python plugins. Reusing these objects across a feature set can provide a >90% speedup for attribute-only validation.
**Action:** Initialize QgsFields and QgsExpressionContext once outside feature loops and update them inside (e.g., context.setFeature(feat)).

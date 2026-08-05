# -*- coding: utf-8 -*-
"""
Test pour vérifier que la logique d'inférence de clé primaire UUID fonctionne correctement.
"""

import sys
import os
import io

# Configurer UTF-8 pour Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ajouter le chemin du plugin
plugin_dir = os.path.dirname(__file__)
sys.path.insert(0, plugin_dir)

from config_postgrest import _infer_pk_from_columns, normalize_layer_mapping


def test_infer_pk_from_columns():
    """Test la détection automatique de clé primaire UUID"""
    
    test_cases = [
        # (endpoint, columns, expected_pk, description)
        (
            'bosquet_baseline',
            ['id', 'uuid_bosquet_baseline', 'nom', 'c_com'],
            'uuid_bosquet_baseline',
            'UUID endpoint exact found'
        ),
        (
            'lutte_nuisibles',
            ['id', 'nom', 'uuid_lutte_nuisible', 'nom_malagasy'],
            'uuid_lutte_nuisible',
            'UUID endpoint singular found (plural endpoint)'
        ),
        (
            'answer_nuisible_bosquet_baseline',
            ['id', 'operateur_id', 'uuid_bosquet_baseline', 'uuid_nuisible'],
            'id',
            'No matching uuid_answer_nuisible_bosquet_baseline (other UUIDs are FKs, not PK)'
        ),
        (
            'communes',
            ['id', 'c_com', 'nom'],
            'id',
            'No uuid column, use default id'
        ),
        (
            'species',
            ['uuid_species', 'scientific_name', 'common_name'],
            'uuid_species',
            'UUID as only PK'
        ),
    ]
    
    print("\n=== Test: Inference de Cle Primaire UUID ===\n")
    
    passed = 0
    failed = 0
    
    for endpoint, columns, expected, desc in test_cases:
        result = _infer_pk_from_columns(endpoint, columns)
        status = "PASS" if result == expected else "FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"[{status}] {desc}")
        print(f"      Endpoint: {endpoint}")
        print(f"      Columns: {columns}")
        print(f"      Expected: {expected}")
        print(f"      Got: {result}")
        print()
    
    return passed, failed


def test_normalize_layer_mapping():
    """Test la normalisation complète des mappings"""
    
    print("\n=== Test: Normalisation des Mappings ===\n")
    
    # Test 1: Mapping avec UUID endpoint
    mapping1 = {
        'endpoint': 'bosquet_baseline',
        'columns': ['id', 'uuid_bosquet_baseline', 'nom', 'c_com']
    }
    result1 = normalize_layer_mapping('bosquet_baseline', mapping1)
    
    print("[CHECK] Mapping avec UUID endpoint:")
    print(f"  Endpoint: {result1['endpoint']}")
    print(f"  PK Field: {result1['pk_field']}")
    print(f"  Expected PK: uuid_bosquet_baseline")
    print(f"  [OK] PASS" if result1['pk_field'] == 'uuid_bosquet_baseline' else "  [FAIL]")
    print()
    
    # Test 2: Mapping avec FKs uniquement (pas d'UUID pour cette table)
    mapping2 = {
        'endpoint': 'answer_nuisible_bosquet_baseline',
        'columns': ['id', 'operateur_id', 'uuid_bosquet_baseline', 'uuid_nuisible']
    }
    result2 = normalize_layer_mapping('answer_nuisible_bosquet_baseline', mapping2)
    
    print("[CHECK] Mapping avec FKs uniquement:")
    print(f"  Endpoint: {result2['endpoint']}")
    print(f"  PK Field: {result2['pk_field']}")
    print(f"  Expected PK: id (pas uuid_answer_nuisible_bosquet_baseline)")
    print(f"  [OK] PASS" if result2['pk_field'] == 'id' else "  [FAIL]")
    print()
    
    # Test 3: Mapping avec PK explicite MAIS UUID disponible (UUID doit être prioritaire)
    mapping3 = {
        'endpoint': 'bosquet_baseline',
        'pk_field': 'custom_id',
        'columns': ['custom_id', 'uuid_bosquet_baseline', 'nom']
    }
    result3 = normalize_layer_mapping('bosquet_baseline', mapping3)
    
    print("[CHECK] Mapping avec UUID disponible (UUID prioritaire):")
    print(f"  Endpoint: {result3['endpoint']}")
    print(f"  PK Field: {result3['pk_field']}")
    print(f"  Expected PK: uuid_bosquet_baseline (UUID prioritaire meme si custom_id explicite)")
    print(f"  [OK] PASS" if result3['pk_field'] == 'uuid_bosquet_baseline' else "  [FAIL]")
    print()
    
    # Test 4: Mapping avec PK explicite SANS UUID disponible (utiliser explicit)
    mapping4 = {
        'endpoint': 'other_table',
        'pk_field': 'custom_id',
        'columns': ['custom_id', 'nom', 'description']
    }
    result4 = normalize_layer_mapping('other_table', mapping4)
    
    print("[CHECK] Mapping avec PK explicite (sans UUID):")
    print(f"  Endpoint: {result4['endpoint']}")
    print(f"  PK Field: {result4['pk_field']}")
    print(f"  Expected PK: custom_id (explicit, pas de UUID)")
    print(f"  [OK] PASS" if result4['pk_field'] == 'custom_id' else "  [FAIL]")
    print()


if __name__ == "__main__":
    passed, failed = test_infer_pk_from_columns()
    test_normalize_layer_mapping()
    
    print(f"\n=== Resume ===")
    print(f"Inference PK: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\nSucces: Tous les tests sont passes!")
        exit(0)
    else:
        print(f"\nEchec: {failed} test(s) echoue(s)")
        exit(1)

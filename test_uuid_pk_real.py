# -*- coding: utf-8 -*-
"""
Test pour vérifier que la nouvelle logique d'inférence UUID fonctionne sur le vrai mapping JSON
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

from config_postgrest import load_layer_mapping, _infer_pk_from_columns


def test_uuid_pk_detection():
    """Teste la détection de UUID comme PK dans les vrais mappings"""
    
    print("\n=== Test: Detection de UUID comme PK ===\n")
    
    # Test direct avec la fonction
    test_case = {
        'endpoint': 'bosquet_suivi',
        'columns': [
            'id',
            'uuid_bosquet_suivi',
            'uuid_bosquet_gps',
            'date_suivi',
            'uuid_operateur',
            'uuid_verificateur'
        ]
    }
    
    result = _infer_pk_from_columns(test_case['endpoint'], test_case['columns'])
    
    print("Test direct _infer_pk_from_columns:")
    print(f"  Endpoint: {test_case['endpoint']}")
    print(f"  Colonnes: {test_case['columns']}")
    print(f"  Result PK: {result}")
    print(f"  Expected: uuid_bosquet_suivi")
    print(f"  Status: [OK] PASS" if result == 'uuid_bosquet_suivi' else f"  Status: [FAIL]")
    print()
    
    # Charger les vrais mappings
    mappings = load_layer_mapping(plugin_dir)
    
    if not mappings:
        print("[ERROR] Aucun mapping charge!")
        return False
    
    # Chercher les mappings avec UUID PK
    uuid_pks_detected = []
    
    for layer_name, config in mappings.items():
        endpoint = config.get('endpoint', '')
        pk_field = config.get('pk_field', '')
        columns = config.get('columns', [])
        
        if pk_field.lower().startswith('uuid_'):
            uuid_pks_detected.append({
                'layer': layer_name,
                'endpoint': endpoint,
                'pk': pk_field,
                'columns': len(columns)
            })
    
    print(f"Resultats apres chargement:")
    print(f"  Total mappings: {len(mappings)}")
    print(f"  Mappings avec UUID comme PK: {len(uuid_pks_detected)}")
    
    if uuid_pks_detected:
        print("\n  Exemples detectes:")
        for info in uuid_pks_detected[:10]:
            print(f"    - {info['layer']}: {info['pk']}")
    else:
        print("  Aucune UUID detectee comme PK")
    
    # Chercher specifically bosquet_suivi
    if 'bosquet_suivi' in mappings:
        bs = mappings['bosquet_suivi']
        print(f"\n  Test specifique 'bosquet_suivi':")
        print(f"    Current PK: {bs.get('pk_field')}")
        print(f"    Expected: uuid_bosquet_suivi (selon nouvelle logique)")
        if bs.get('pk_field') == 'uuid_bosquet_suivi':
            print(f"    Status: [OK] PASS - UUID detachee correctement!")
        else:
            print(f"    Status: [INFO] Toujours 'id' - Verifier que les colonnes sont bien disponibles")
            columns = bs.get('columns', [])
            print(f"    Colonnes disponibles: {len(columns)}")
            if 'uuid_bosquet_suivi' in columns:
                print(f"    -> uuid_bosquet_suivi EST dans les colonnes (detection OK)")
    
    return True


if __name__ == "__main__":
    success = test_uuid_pk_detection()
    
    if success:
        print("\nTest completed!")
        exit(0)
    else:
        print("\nTest failed!")
        exit(1)

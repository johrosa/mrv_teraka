# -*- coding: utf-8 -*-
"""
Test final: Vérifier que la logique UUID PK est correctement appliquée
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

from config_postgrest import load_layer_mapping


def test_uuid_pk_integrated():
    """Test que la logique UUID est appliquée au chargement réel"""
    
    print("\n" + "="*80)
    print("TEST FINAL: Logique UUID PK Intégrée")
    print("="*80 + "\n")
    
    mappings = load_layer_mapping(plugin_dir)
    
    test_cases = [
        {
            'name': 'UUID matching trouvée',
            'endpoint': 'bosquet_suivi',
            'expected_pk': 'uuid_bosquet_suivi',
            'should_have_fks': ['uuid_bosquet_gps', 'uuid_operateur', 'uuid_verificateur'],
        },
        {
            'name': 'Endpoint pluriel -> UUID singulier',
            'endpoint': 'lutte_nuisibles',
            'expected_pk': 'uuid_lutte_nuisible',
            'should_have_fks': [],
        },
        {
            'name': 'FKs uniquement (pas UUID pour cette table)',
            'endpoint': 'answer_nuisible_bosquet_baseline',
            'expected_pk': 'id',
            'should_have_fks': ['uuid_bosquet_baseline', 'uuid_nuisible'],
        },
        {
            'name': 'UUID + autres FKs présentes',
            'endpoint': 'answer_sourcing_graine_arbre_baseline',
            'expected_pk': 'uuid_answer_sourcing_graine_arbre_baseline',
            'should_have_fks': ['uuid_arbre_baseline', 'uuid_sourcing_graine'],
        },
    ]
    
    all_passed = True
    
    for test in test_cases:
        endpoint = test['endpoint']
        expected_pk = test['expected_pk']
        should_have_fks = test['should_have_fks']
        
        if endpoint not in mappings:
            print(f"[SKIP] {endpoint} - Not in mappings")
            continue
        
        config = mappings[endpoint]
        actual_pk = config.get('pk_field')
        columns = config.get('columns', [])
        
        # Vérifier la PK
        pk_ok = actual_pk == expected_pk
        
        # Vérifier les FKs
        fks_ok = all(fk in columns for fk in should_have_fks)
        
        status = "PASS" if (pk_ok and fks_ok) else "FAIL"
        
        print(f"[{status}] {test['name']}")
        print(f"      Endpoint: {endpoint}")
        print(f"      Expected PK: {expected_pk}")
        print(f"      Actual PK:   {actual_pk}")
        
        if not pk_ok:
            print(f"      ❌ PK mismatch!")
            all_passed = False
        
        if should_have_fks:
            fks_str = ", ".join(should_have_fks)
            print(f"      Expected FKs: {fks_str}")
            if not fks_ok:
                print(f"      ❌ FKs missing!")
                all_passed = False
        
        print()
    
    # Résumé
    print("-"*80)
    print("\nStatistiques Globales:\n")
    
    uuid_count = sum(1 for c in mappings.values() 
                     if c.get('pk_field', '').startswith('uuid_'))
    id_count = sum(1 for c in mappings.values() 
                   if c.get('pk_field') == 'id')
    
    print(f"  Mappings avec UUID PK:  {uuid_count}")
    print(f"  Mappings avec 'id' PK:  {id_count}")
    print(f"  Total:                  {len(mappings)}")
    print(f"\n  UUID adoption rate:     {uuid_count/len(mappings)*100:.1f}%")
    
    print("\n" + "="*80)
    
    if all_passed and uuid_count >= 40:
        print("\n✅ TEST COMPLET: Logique UUID PK fonctionnelle et intégrée!")
        print(f"\n   {uuid_count} tables utilisent maintenant une UUID comme PK\n")
        return 0
    else:
        print("\n❌ TEST ÉCHOUÉ: Problèmes détectés\n")
        return 1


if __name__ == "__main__":
    exit_code = test_uuid_pk_integrated()
    exit(exit_code)

# -*- coding: utf-8 -*-
"""
Comparaison: Avant/Après l'implémentation UUID PK
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


def main():
    """Affiche un aperçu avant/après"""
    
    mappings = load_layer_mapping(plugin_dir)
    
    print("\n" + "="*80)
    print("COMPARAISON: Avant/Après Implémentation UUID comme Clé Primaire")
    print("="*80 + "\n")
    
    # Exemples clés
    examples = [
        ('bosquet_baseline', 'uuid_bosquet_baseline'),
        ('bosquet_suivi', 'uuid_bosquet_suivi'),
        ('lutte_nuisibles', 'uuid_lutte_nuisible'),
        ('formations', 'uuid_formation'),
        ('answer_sourcing_graine_arbre_baseline', 'uuid_answer_sourcing_graine_arbre_baseline'),
        ('answer_nuisible_bosquet_baseline', None),  # Pas d'UUID, doit rester 'id'
    ]
    
    print("EXEMPLES TRANSFORMES:\n")
    
    for layer_name, expected_uuid in examples:
        if layer_name in mappings:
            config = mappings[layer_name]
            endpoint = config['endpoint']
            pk = config['pk_field']
            has_uuid = expected_uuid in config.get('columns', []) if expected_uuid else False
            
            if expected_uuid:
                print(f"[+] {layer_name}")
                print(f"    Endpoint: {endpoint}")
                print(f"    Avant: PK = 'id'")
                print(f"    Apres: PK = '{pk}'")
                status = "PASS" if pk == expected_uuid else f"FAIL (got '{pk}')"
                print(f"    Status: {status}\n")
            else:
                print(f"[-] {layer_name}")
                print(f"    Endpoint: {endpoint}")
                print(f"    Note: Pas d'UUID_{endpoint}, reste avec 'id'")
                status = "OK" if pk == 'id' else f"UNEXPECTED (got '{pk}')"
                print(f"    Status: {status}\n")
    
    # Statistiques
    print("\n" + "-"*80)
    print("STATISTIQUES:")
    print("-"*80 + "\n")
    
    uuid_pks = [config for config in mappings.values() 
                if config.get('pk_field', '').lower().startswith('uuid_')]
    id_pks = [config for config in mappings.values() 
              if config.get('pk_field') == 'id']
    other_pks = [config for config in mappings.values() 
                 if not config.get('pk_field', '').lower().startswith('uuid_') 
                 and config.get('pk_field') != 'id']
    
    print(f"Mappings avec UUID comme PK:        {len(uuid_pks):>3} ✓ (nouveau)")
    print(f"Mappings avec 'id' comme PK:        {len(id_pks):>3} (pas d'UUID disponible)")
    print(f"Mappings avec autre PK:             {len(other_pks):>3}")
    print(f"{'─'*45}")
    print(f"TOTAL:                              {len(mappings):>3}")
    
    print(f"\nBénéfice: {len(uuid_pks)} tables utilisent maintenant leur UUID natif comme clé primaire!")
    print("\nCela améliore:")
    print("  • L'identité unique des enregistrements")
    print("  • La synchronisation avec les mobiles (Mergin Maps)")
    print("  • Les upserts et la fusion de données")
    print("  • La traçabilité des enregistrements collectés")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

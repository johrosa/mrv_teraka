# 🚀 Démarrage Rapide - Authentification MrvTeraka

## Installation

1. **Fichiers créés/modifiés**:
   ```
   mrv_teraka/
   ├── auth_dialog.py              ✨ Nouveau
   ├── token_manager.py            ✨ Nouveau
   ├── AUTHENTICATION_GUIDE.md     ✨ Nouveau
   ├── AUTHENTICATION_SUMMARY.md   ✨ Nouveau
   ├── mrv_teraka.py              ✏️ Modifié
   └── mrv_teraka_dockwidget.py   ✏️ Modifié
   ```

2. **Aucune dépendance supplémentaire** - Utilise uniquement Qt et les APIs QGIS

## Utilisation Basique

### 1️⃣ Première Connexion

```
┌─────────────────────────────────────────────────┐
│ QGIS                                            │
├─────────────────────────────────────────────────┤
│ Barre d'outils:                                 │
│ [iTeraka]  [🔐 Connexion]                       │
└─────────────────────────────────────────────────┘
                        ↓
              Utilisateur clique → [🔐 Connexion]
                        ↓
        ┌───────────────────────────────────────┐
        │  Dialog: Authentification API         │
        ├───────────────────────────────────────┤
        │ Mode API: [Django          ▼]         │
        │ URL API: [http://localhot:8000]       │
        │ Email/Utilisateur: [user@example.com]│
        │ Mot de passe: [••••••]  [✓ Afficher] │
        │ [✓] Mémoriser les identifiants       │
        │                                       │
        │        [Se connecter]  [Annuler]     │
        └───────────────────────────────────────┘
                        ↓
              Utilisateur se connecte
                        ↓
┌─────────────────────────────────────────────────┐
│ Barre d'outils:                                 │
│ [iTeraka]  [🔓 Déconnecter]                     │
├─────────────────────────────────────────────────┤
│ Dock Widget:                                    │
│ ● Connecté                                      │
│ user@example.com @ http://localhost:8000       │
│                    [Déconnecter]                │
├─────────────────────────────────────────────────┤
│ [Comparer couches / base] [Charger données DB] │
│ ✅ Boutons d'action activés!                    │
└─────────────────────────────────────────────────┘
```

### 2️⃣ Reconnexion Automatique

```
Fermer et relancer QGIS
        ↓
Plugin chargé automatiquement
        ↓
Barre d'outils affiche: [🔓 Déconnecter]
Dock affiche: ● Connecté - user@example.com
        ↓
✅ Aucune saisie d'identifiant requise!
```

### 3️⃣ Charger des données

Une fois connecté:

```
1. Entrez l'endpoint: communes

2. Cliquez "Charger données DB"

3. Les données sont téléchargées et ajoutées en tant que couches QGIS:
   ✅ Les géométries sont chargées
   ✅ Les attributs sont conservés
   ✅ Le CRS correct est appliqué
```

## Fonctionnalités

### ✅ Authentification

- **Dialog professionnel** avec formulaire complet
- **Modes supportés**: Django et PostgREST Standalone
- **URL personnalisable**: Entrez votre propre URL
- **Mémorisation**: Les paramètres sont sauvegardés

### ✅ Persistance du Jeton

- **Sauvegarde automatique** dans QSettings
- **Chargement automatique** au démarrage
- **Validation d'expiration**: Jeton expiré après 24h
- **Suppression sécurisée**: À la déconnexion

### ✅ Interface Utilisateur

- **Indicateur de statut**: `● Connecté` (vert) ou `● Déconnecté` (rouge)
- **Affichage utilisateur**: Email et URL de l'API
- **Bouton dynamique**: Change "Connexion" ↔ "Déconnecter"
- **Boutons d'action**: Activés/désactivés selon l'authentification

### ✅ Sécurité

- **Suppression complète** du jeton à la déconnexion
- **Validation avant action**: Vérifiable avant chaque requête API
- **Expiration gérée**: Jeton renouvelable si expiré
- **Stockage sécurisé**: QSettings avec permissions système

## Configuration Avancée

### Changer le Mode API

Dans le dialog d'authentification:

```
Mode API: [Django ▼]
          ├─ Django
          └─ PostgREST (Standalone)
```

Sélectionnez selon votre configuration serveur.

### Mémoriser les Identifiants

```
[✓] Mémoriser les identifiants
```

Si coché:
- L'email/username est sauvegardé
- Prérempli au prochain dialog
- Le jeton est toujours sauvegardé

### Personnaliser l'URL

```
URL API: [http://localhost:8000]
```

Modifiez l'URL pour pointer vers votre serveur:
- Développement: `http://localhost:8000`
- Production: `https://api.example.com`
- Tests: `http://staging.example.com:8000`

## Dépannage Rapide

### ❌ "Authentification échouée"

**Cause**: Identifiants incorrects ou serveur non accessible

**Solution**:
1. Vérifiez le serveur est actif
2. Vérifiez les identifiants
3. Vérifiez l'URL API

### ❌ "Erreur 401 Unauthorized"

**Cause**: Jeton expiré ou invalide

**Solution**:
1. Cliquez "Déconnecter"
2. Cliquez "Connexion"
3. Saisissez les identifiants de nouveau

### ❌ "Jeton non trouvé"

**Cause**: Le dialog d'authentification retourne une réponse invalide

**Solution**:
1. Vérifiez le format de réponse de votre API (JSON)
2. Assurez-vous que le champ `access_token` ou `token` existe

### ❌ "Les boutons d'action restent désactivés"

**Cause**: Pas de jeton valide

**Solution**:
1. Vérifiez via le statut "● Connecté"
2. Cliquez "Connexion" et authentifiez-vous

## Flux Typique de Utilisation

```
┌─ Jour 1 ─────────────────────────────────┐
│ 1. Lancer QGIS                          │
│ 2. Voir "● Déconnecté" → Cliquer Conn. │
│ 3. Remplir le formulaire                │
│ 4. Cliquer "Se connecter"               │
│ 5. Voir "● Connecté"                    │
│ 6. Charger des données, comparer, etc.  │
│ 7. Fermer QGIS                          │
└─────────────────────────────────────────┘
              ↓
┌─ Jour 2 ─────────────────────────────────┐
│ 1. Lancer QGIS                          │
│ 2. Voir "● Connecté" immédiatement ✨   │
│ 3. Commencer à utiliser le plugin       │
│ 4. Aucune saisie requise!               │
│ 5. Fermer QGIS                          │
└─────────────────────────────────────────┘
```

## Aide Inline

Pour comprendre chaque élément:

```
Dialog d'authentification:
┌─────────────────────────────────────────┐
│ Mode API: Choisir entre Django ou       │
│           PostgREST Standalone          │
│                                         │
│ URL API: Laisser http://localhost:8000  │
│          pour un serveur local          │
│                                         │
│ Email/Utilisateur: Votre login          │
│                                         │
│ Mot de passe: Votre password sécurisé   │
│                                         │
│ [✓] Afficher: Voir le mot de passe      │
│                                         │
│ [✓] Mémoriser: Sauvegarder les infos    │
│                (email ET jeton)         │
└─────────────────────────────────────────┘
```

## FAQ

### Q: Où sont sauvegardés les identifiants ?
**R**: Dans QSettings (Registry Windows, ~/.config Linux, Preferences macOS)

### Q: Mon mot de passe est-il sauvegardé ?
**R**: Non, seul le jeton JWT est sauvegardé. Le mot de passe est oublié après connexion.

### Q: Combien de temps le jeton reste-t-il valide ?
**R**: 24h par défaut. Vous pouvez le modifier dans le code si nécessaire.

### Q: Que se passe-t-il si le jeton expire ?
**R**: Un dialog d'authentification s'affiche automatiquement à la prochaine action.

### Q: Comment me déconnecter complètement ?
**R**: Cliquez "Déconnecter" → Confirmer → Le jeton est supprimé.

### Q: Puis-je utiliser plusieurs comptes ?
**R**: Oui, en cliquant "Déconnecter" puis "Connexion" avec d'autres identifiants.

### Q: L'authentification fonctionne sur quel mode API ?
**R**: Django ET PostgREST (à sélectionner dans le dialog)

### Q: Quelle est la sécurité ?
**R**: Le jeton est stocké localement de manière sécurisée avec les permissions du système.

## Résumé des Commandes Utilisateur

| Action | Interface |
|--------|-----------|
| Se connecter | Cliquez [🔐 Connexion] dans la barre d'outils |
| Se déconnecter | Cliquez [🔓 Déconnecter] dans la barre d'outils |
| Se déconnecter (dock) | Cliquez [Déconnecter] dans la dock widget |
| Charger des données | Entrez endpoint + cliquez [Charger données DB] |
| Comparer | Entrez endpoint + cliquez [Comparer couches / base] |
| Préparer Mergin | Entrez endpoint + cliquez [Préparer données Mergin] |
| Voir le statut | Regardez `● Connecté/Déconnecté` dans la dock |
| Voir l'utilisateur | Regardez "user@email.com @ url" dans la dock |

## Conclusion

Vous avez maintenant:

✅ **Authentification fluide** et sécurisée
✅ **Persistance du jeton** (pas de saisie à chaque démarrage)
✅ **Interface professionnelle** et intuitive
✅ **Indicateurs visuels** clairs
✅ **Support du multi-mode API** (Django + PostgREST)
✅ **Gestion d'expiration** automatique
✅ **Déconnexion sécurisée**

Bon travail! 🎉


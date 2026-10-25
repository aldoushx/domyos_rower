# Historique des versions

Retour au [README](README.md).

## v0.11.0
Écran de la console remis (interrupteur, activé par défaut) avec les champs décodés : Time,
Time/500M, Count = coups, Km. Octet 12 = allure et non pouls. Spm / Kcal : inconnus.
Les services de test, les options de protocole / initialisation et le mode Passive restent retirés.

## v0.11.1
L'écran de la console n'est écrit qu'après les premiers paquets d'état du rameur (+3 s) : écrit
dès la connexion, juste après la mise sous tension, la console cessait d'envoyer ses données à HA.

## v0.11.2
Après une mise sous tension du rameur (plus d'annonce Bluetooth pendant 30 s, puis retour),
l'intégration attend 10 s avant de se connecter : connectée pile pendant le démarrage de la
console, celle-ci restait complètement éteinte. Une coupure de lien en pleine séance se reconnecte
sans cette attente.

## v0.12.0 – envoi vers Garmin Connect (facultatif, sur bouton)
Options de l'intégration → « Relier mon compte Garmin Connect » : e-mail + mot de passe (+ code de
vérification si ton compte a la double authentification). Le mot de passe n'est jamais conservé :
seuls l'e-mail et le jeton de session de la bibliothèque `garminconnect==0.3.17` le sont.
Le bouton « Envoyer la dernière séance à Garmin Connect » envoie le fichier FIT de la dernière
séance (il le génère s'il n'existe pas). La bibliothèque est installée par Home Assistant au premier
usage.
**Limites** : connexion non officielle, qui peut cesser de marcher si Garmin la modifie ; non
testée contre un vrai compte (tests avec une fausse bibliothèque + vérification des noms de la vraie) ;
la bibliothèque demande `requests>=2.33` : si ta version de HA fige une version plus ancienne,
l'installation échoue (message dans l'assistant). Session expirée → relier de nouveau le compte.

## v0.13.0
Strava retiré (étape d'installation, options, bouton, code). Les installations existantes gardent
simplement une clé `strava` inutilisée dans leur configuration.

### v0.13.1 - 0.13.2
- Icône et logo de l intégration (dossier `brand/`), affichés dans Paramètres > Appareils et services (Home Assistant 2026.3 ou plus récent) et dans HACS.

### v0.13.3
- Les coordonnées GPX laissées vides dans les options ne font plus échouer la génération des fichiers (retour aux coordonnées de Home Assistant).
- Encodeur FIT : valeurs de distance ou de vitesse absentes traitées comme 0.
- Test d'écriture du dossier d'export : fichier temporaire unique.
- `garminconnect` : version `>=0.3.17,<0.4` pour recevoir les correctifs de la bibliothèque.
- Ajout de `hacs.json`.

### v0.14.0 - Carte Lovelace intégrée
L'intégration fournit maintenant sa propre carte, sans aucune dépendance (ni HACS, ni autre carte). Elle est chargée automatiquement : redémarre Home Assistant après la mise à jour, puis vide le cache du navigateur (Ctrl + F5).

Ajout dans un tableau de bord : Modifier > Ajouter une carte > Manuel :

```yaml
type: custom:domyos-rower-card
plug_entity: switch.prise_rameur            # facultatif : prise connectée du rameur (bouton masqué sans cette ligne)
title: Rameur Domyos                        # facultatif
```

Les entités du rameur sont trouvées automatiquement. Si plusieurs rameurs sont installés, ajoute `device_id:`. La carte affiche le bouton de séance, le temps, l'allure, la distance, la cadence, les coups, la puissance, les calories, un graphe de toute la séance (puissance et résistance), la résistance (− / +), la prise du rameur (facultatif), le Bluetooth (avec son état), l'entraînement choisi, la dernière séance et les boutons Fichiers / Garmin. La carte n'a besoin d'aucune autre carte HACS et ne demande aucune ligne pour l'entraînement : il se choisit dans l'éditeur.

### v0.15.0 - Entraînements (programmes de résistance)
Remplace l'automatisation « Entraînement pyramides » (et son `input_boolean`) par des programmes gérés par l'intégration.

- Un entraînement est une liste de paliers (durée + niveau de résistance), regroupés en blocs répétables (« × 9 »). Quatre modèles sont fournis : Pyramides (4 min niveau 8, 2 min niveau 10, 1 min niveau 15, 2 min niveau 10, × 9), Intervalles 30/30, Endurance, Montée progressive. Ils sont enregistrés dans Home Assistant et modifiables.
- Le bouton « Entraînement » de la carte ouvre l'éditeur : liste des entraînements avec case de sélection (un seul choisi à la fois, ou aucun), modification, duplication, suppression, création, aperçu du profil et durée totale.
- L'entraînement choisi démarre avec l'enregistrement de la séance (bouton « Démarrer la séance »). Il se met en pause 8 s après le dernier coup de rame et reprend quand tu rames. Il s'arrête avec la séance et remet le niveau choisi pour la fin (1 par défaut). La résistance reste modifiable à la main : le palier suivant la remplace.
- Nouvelles entités : `select` « Entraînement » (choix du programme), capteur « Programme » (état `idle`, `paused`, `running`, `finished` ; attributs : palier, niveau, niveau suivant, temps restant du palier, temps écoulé et total).
- API WebSocket utilisée par la carte : `domyos_rower/workouts` (liste), `/save`, `/delete`, `/select` (enregistrer et supprimer demandent un compte administrateur).
- Le niveau de résistance maximal vient du rameur (15 sur le Rower 500).

### v0.15.1
- La prise connectée du rameur n est plus gérée par la carte (retirée de la carte JS et de la carte YAML).

### v0.15.2
- La prise connectée du rameur redevient disponible, toujours facultative : le bouton n apparaît que si `plug_entity` est renseigné dans la carte JS. Dans la carte YAML, supprime le bloc « Prise rameur » si tu n en as pas.

### v0.15.3
- Le lien « documentation » de l'intégration pointe vers ce dépôt (il pointait vers QZ).
- La carte YAML (`dashboard/`) est supprimée : seule la carte `custom:domyos-rower-card` reste.
- Stockage des entraînements : fichier `.storage/domyos_rower_workouts_<id de l'entrée>` dans le dossier de configuration de Home Assistant (sauvegardé avec HA). Aucune entité ne les contient : seuls le `select` « Entraînement » et le capteur « Programme » exposent le choix et l'avancement.
- Si la carte reste introuvable (« Custom element doesn't exist ») : Paramètres > Tableaux de bord > ⋮ > Ressources > Ajouter `/domyos_rower/domyos-rower-card.js`, type « Module JavaScript ». (Nécessite le mode avancé dans ton profil.)


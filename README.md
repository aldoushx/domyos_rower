<p align="center">
  <img src="https://raw.githubusercontent.com/aldoushx/domyos_rower/main/custom_components/domyos_rower/brand/icon@2x.png" width="160" alt="Domyos Rower">
</p>

<h1 align="center">Domyos Rower pour Home Assistant</h1>

<p align="center">
  Rameur Decathlon / Domyos en Bluetooth, via la pile Bluetooth de Home Assistant et tes proxies ESP32.<br>
  Capteurs, résistance, enregistrement de séance, export FIT / TCX / GPX, entraînements programmables et carte Lovelace intégrée.
</p>

<p align="center">
  <a href="https://github.com/aldoushx/domyos_rower/releases"><img alt="Version" src="https://img.shields.io/github/v/release/aldoushx/domyos_rower"></a>
  <a href="https://hacs.xyz"><img alt="HACS" src="https://img.shields.io/badge/HACS-Custom-orange"></a>
</p>

---

## Ce que ça fait

- **Capteurs en direct** : cadence, coups, allure /500 m, distance, calories, puissance (estimée), résistance, temps.
- **Résistance pilotable** depuis HA (niveaux 1 à 15 sur le Rower 500).
- **Séances** : un bouton démarre / termine l'enregistrement et produit des fichiers **FIT, TCX et GPX**.
- **Garmin Connect** (facultatif) : envoi de la dernière séance sur simple bouton.
- **Entraînements** : programmes de résistance (Pyramides, Intervalles 30/30, Endurance, Montée progressive), modifiables avec un éditeur. Ils se mettent en pause quand tu arrêtes de ramer.
- **Écran de la console** : l'intégration y écrit temps, distance, allure et coups.
- **Carte Lovelace fournie**, sans dépendance.

Testé sur un Rower 500 (`Domyos-ROW-xxxx`).

## Installation

### Avec HACS (recommandé)
1. HACS > ⋮ > **Dépôts personnalisés** > ajoute `https://github.com/aldoushx/domyos_rower`, catégorie **Intégration**.
2. Installe **Domyos Rower (Bluetooth)** puis redémarre Home Assistant.
3. Réveille le rameur (tire la poignée), puis **Paramètres > Appareils et services** : il est découvert tout seul, sinon **Ajouter une intégration**.

### À la main
Copie `custom_components/domyos_rower` dans `/config/custom_components/` et redémarre.

### Proxy Bluetooth
Si tu passes par un ESP32, autorise les connexions actives :

```yaml
bluetooth_proxy:
  active: true
```

## La carte Lovelace

Tableau de bord > Modifier > Ajouter une carte > **Manuel** :

```yaml
type: custom:domyos-rower-card
plug_entity: switch.prise_rameur   # facultatif : bouton de la prise du rameur
title: Rameur Domyos               # facultatif
```

Les entités du rameur sont trouvées automatiquement. Avec plusieurs rameurs, ajoute `device_id:`.

La carte affiche le bouton de séance, les chiffres clés, le graphe de toute la séance (puissance et résistance), la résistance − / +, le Bluetooth, l'entraînement choisi, la dernière séance et les boutons Fichiers / Garmin.

> **« Custom element doesn't exist »** : recharge la page après le redémarrage. Si ça persiste, ajoute la ressource à la main : profil > mode avancé, puis Paramètres > Tableaux de bord > ⋮ > Ressources > `/domyos_rower/domyos-rower-card.js`, type **Module JavaScript**.

## Entraînements

Un entraînement est une suite de paliers (durée + niveau), regroupés en blocs répétables. Le bouton **Entraînement** de la carte ouvre l'éditeur : choix de l'entraînement (une seule case), création, modification, duplication, suppression.

- Il démarre avec **Démarrer la séance** et s'arrête avec **Terminer la séance**.
- Il se met en pause 8 s après le dernier coup de rame et reprend quand tu rames.
- Tu peux forcer la résistance à la main : le palier suivant la remplace.
- Stockage : `.storage/domyos_rower_workouts_<id>` dans la configuration de HA (inclus dans les sauvegardes).

## Séances et Garmin

Les fichiers sont écrits dans `/media/domyos_rower` (ou `<config>/domyos_rower`), dossier modifiable dans les options. **Le FIT est le plus complet** : à préférer pour Garmin. L'envoi vers Garmin Connect se règle dans **Options** de l'intégration (compte Garmin) et ne part que sur bouton. Pour Strava, relie Garmin Connect à Strava dans les réglages de Strava.

## Documentation

- [Référence technique](docs/REFERENCE.md) : entités, protocoles, étalonnage, fichiers exportés, diagnostic.
- [Historique des versions](CHANGELOG.md)

## Limites

- Le rameur n'accepte qu'un client Bluetooth à la fois (HA **ou** téléphone / QZ). L'interrupteur « Connexion Bluetooth » le libère.
- La puissance est une estimation (formule du Concept2 appliquée à l'allure), pas une mesure.
- Pas de fréquence cardiaque sans ceinture reliée à la console.

## Crédits

Protocole décodé à partir de [QZ (qdomyos-zwift)](https://github.com/cagnulein/qdomyos-zwift). Projet indépendant, non affilié à Decathlon ni à Domyos.

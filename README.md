# Domyos Rower — intégration Home Assistant (Bluetooth / proxy ESPHome) v0.10.0

Port en Python de ce que fait QZ (qdomyos-zwift) avec les rameurs Domyos.
Elle passe par la pile Bluetooth de Home Assistant, donc par tes proxies ESP32.

## Installation / mise à jour
1. Remplace le dossier `/config/custom_components/domyos_rower` par celui du zip.
2. Redémarre Home Assistant.
3. Réveille le rameur (tire la poignée / active le Bluetooth dans son menu).

Le proxy ESPHome doit autoriser les connexions actives :

    bluetooth_proxy:
      active: true

## L'écran de la console (protocole Domyos)
Dès qu'un client Bluetooth est connecté (HA, QZ, nRF Connect…), la console cesse d'afficher ses
propres mesures : elle n'affiche que ce que le client lui écrit (logo Bluetooth sinon). L'interrupteur
**« Écran de la console »** (activé par défaut) écrit donc chaque seconde, comme QZ :
- **Time** : temps écoulé ; **Km** : distance (dixièmes de km) ;
- **Time/500M** : allure (octets 11/12, nombre décimal minutes×100+secondes) ;
- **Count** : nombre total de coups (octets 15/16 = coups × 10, la console divise par 10).

**Spm et Kcal restent à 0 sur la console** : aucun octet connu, QZ ne les écrit pas non plus
(ils restent disponibles dans HA). Pour retrouver l'écran natif complet, déconnecte HA
(interrupteur « Connexion Bluetooth ») et, si besoin, coupe le courant du rameur.

## Protocoles (choisis automatiquement à la connexion, comme QZ)
- **FTMS** (cas d'un `DOMYOS-ROW-xxxx` qui annonce le service 0x1826) : l'intégration
  s'abonne à toutes les caractéristiques notify/indicate du service FTMS, puis envoie
  « Start/Resume » (0x07) sur le Control Point, ce qui déclenche l'envoi des données.
  Si le rameur répond « control not permitted », elle envoie « Request Control » puis
  recommence.
- **Domyos propriétaire** (service 49535343-…) : séquence d'initialisation + interrogation
  toutes les ~300 ms. Si la console ne répond jamais et que FTMS est aussi présent,
  bascule automatiquement sur FTMS.

## Entités
- Capteurs : cadence, coups, vitesse, allure (s/500 m), distance, calories, résistance,
  fréquence cardiaque, puissance et temps écoulé (selon ce que le rameur envoie).
  Cadence, vitesse et puissance passent à 0 après 3 s sans nouveau coup (règle de QZ).
- **Puissance et temps écoulé calculés** quand le rameur ne les envoie pas (c'est le cas du
  Rower 500, comme QZ le constate) :
  - puissance = formule du Concept2 appliquée à l'allure : `2,8 × (500 / allure en s)³`
    (ex. 178 s/500 m → ≈ 62 W). C'est une estimation, pas une mesure. L'attribut
    `power_calculated` du capteur « État » indique si elle est calculée ;
  - temps écoulé = chronomètre qui avance tant que des coups arrivent et s'arrête après 3 s
    sans coup ; il repart de zéro si la console recommence une séance (compteur de coups remis à 0).
  Si un rameur envoie lui-même ces valeurs, ce sont les siennes qui sont utilisées.
- **Allure** : deux capteurs. « Allure (mm:ss/500 m) » est un texte lisible (`02:58`) ;
  « Allure (s/500 m) » reste numérique pour les graphiques et automatisations.
- **Étalonnage distance (multiplicateur)** : réglage (1,00 par défaut, de 0,5 à 2,0, conservé
  après redémarrage). Il multiplie la distance et la vitesse, divise l'allure, et la
  puissance calculée à partir de l'allure suit. Il ne touche pas aux coups, à la cadence, aux
  calories, à la résistance, au pouls, au temps, ni à une puissance envoyée par le rameur.
  Pour le régler : multiplicateur = distance de référence ÷ distance affichée par HA, sur une
  séance longue (l'écran du rameur n'affiche que 0,1 km de résolution).
- **Résistance (consigne)** : curseur. En FTMS la commande est « Set Target Resistance »
  (0x04, valeur × 10, comme QZ) et les bornes sont lues sur le rameur (0x2AD6) ; sinon
  1 à 15. En protocole Domyos, 1 à 15.
- **Connexion Bluetooth** (interrupteur) : libère le rameur pour ton téléphone / QZ.
- **État** (diagnostic) : disabled / waiting / connecting / connected / error, avec en
  attributs le protocole, la dernière erreur, les services GATT et la plage de résistance.

## Enregistrer une séance et exporter les fichiers
- **Interrupteur « Enregistrement de la séance »** : activé = la séance démarre (le chronomètre
  repart de zéro) ; désactivé = elle s'arrête et trois fichiers sont **créés automatiquement** :
  `rowing_AAAAMMJJ_HHMMSS.fit`, `.tcx` et `.gpx`. Une mesure par seconde. Rien n'est envoyé
  nulle part automatiquement.
- **Que contient chaque fichier** (à importer sur Garmin Connect) :

  | | FIT | TCX | GPX |
  |---|---|---|---|
  | Sport « aviron d'intérieur » reconnu | oui | non (activité « autre ») | « rowing » dans le nom du type |
  | Distance, vitesse | par point | par point | non |
  | Cadence de coups | par point | par point | par point |
  | Puissance (estimée) | par point + moyenne/max | par point | non |
  | Pouls | par point + moy./max | par point + moy./max | par point |
  | Calories | par point + total | total | non |
  | Nombre de coups | total | dans les notes | non |
  | Temps actif (sans les pauses) et temps écoulé | oui | temps total | non |
  | Niveau de résistance | par point | non | non |

  **Le FIT est le plus complet : c'est celui à préférer pour Garmin.** Le TCX est le plus
  répandu ; le GPX est un format GPS et ne sert que de secours.
- **Dossier des fichiers** : `/media/domyos_rower` si `/media` existe (Home Assistant OS), sinon
  `<config>/domyos_rower`. Modifiable dans les options de l'intégration. `/media` est visible
  dans le navigateur multimédia. Certaines intégrations n'ouvrent que les dossiers déclarés dans
  `allowlist_external_dirs` (`configuration.yaml`) : ajoute-y le dossier si besoin.
- **Pour une autre intégration ou une automatisation** : à chaque export, l'événement
  `domyos_rower_session_saved` contient `fit`, `tcx`, `gpx`, `folder`, `duration_s`,
  `distance_m`, `calories`, `strokes`, `start`. Le capteur « Dernière séance » garde les mêmes
  informations en attributs (conservées après un redémarrage).
- **Bouton « Générer les fichiers (TCX, GPX, FIT) »** : recrée les fichiers de la dernière séance.
- **GPX** : une séance d'intérieur n'a pas de position, tous les points utilisent donc les
  coordonnées des options (par défaut celles de ta maison dans HA).
- **Limites** : la puissance est une estimation (formule du Concept2 appliquée à l'allure) ; il n'y
  a pas de pouls sans ceinture reliée à la console. Le FIT est écrit avec le fabricant
  « development » (il ne se fait pas passer pour un appareil Garmin). Les mesures ne sont
  enregistrées que quand le rameur est connecté ; si un redémarrage de HA interrompt une séance,
  ce qui avait été sauvegardé (toutes les 30 s) reste disponible via le bouton.

## Envoi vers Garmin Connect (facultatif, uniquement sur bouton)
Voir « v0.12.0 » plus bas. Strava n'est plus géré directement (son API est réservée aux abonnés
payants) : relie Garmin Connect à Strava dans les réglages de Strava, et Garmin transmet la séance.

## Reconnexion
- Une coupure en pleine séance est retentée au bout de ~3 s.
- Si les échecs se répètent, les tentatives sont espacées (10 s, 20 s, 40 s, 60 s, puis 2 min)
  pour ne pas empêcher le proxy d'écouter ses autres appareils (chaque tentative coupe son
  scan pendant plusieurs secondes). Un interrupteur coupé puis rallumé relance tout de suite.
- Une seule tentative par cycle côté Home Assistant (au lieu de 3) : c'est la boucle de
  l'intégration qui gère les nouvelles tentatives.

## Si rien n'arrive : diagnostic
1. Regarde l'entité **État** : `error` + l'attribut `last_error` disent pourquoi, et
   `last_failed_step` indique l'étape Bluetooth qui a échoué (connexion, abonnement à une
   caractéristique avec son *handle*, écriture Start/Resume, résistance…).
2. Active les logs détaillés sans redémarrer : Outils de développement → Actions →
   `logger.set_level` avec `custom_components.domyos_rower: debug`. Ou, de façon permanente,
   dans `configuration.yaml` :

       logger:
         default: warning
         logs:
           custom_components.domyos_rower: debug

   Les lignes importantes : `connected, services: [...]`, `FTMS characteristics: {...}`,
   `subscribed to [...]`, `Start/Resume -> ...`, `control point indication ...`.
3. Les erreurs de connexion apparaissent maintenant dans le journal en WARNING.

## Limites connues
- **Non testé sur un vrai rameur ni dans un vrai Home Assistant.** La logique est vérifiée
  contre un faux rameur, et les trames Domyos contre le C++ de QZ compilé.
- Le rameur n'accepte qu'un client Bluetooth à la fois (HA **ou** téléphone/QZ).
- La plage de résistance FTMS (0x2AD6) est lue selon la spec ; si ton rameur la formate
  autrement, elle apparaît dans le log (`resistance range raw=...`) et on retombe sur 1–15.
- Pas de démarrage/arrêt de séance depuis HA.

## Tests
`tests/` contient 22 tests exécutés sur Home Assistant 2025.1.4 avec
`pytest-homeassistant-custom-component` (assistant de configuration, options, enregistrement,
fichiers, envoi Garmin simulé, logique Bluetooth avec un faux rameur). Le fichier FIT est lu par
le décodeur officiel de Garmin (`garmin-fit-sdk`) et les numéros de champs sont comparés à son profil. Ils ne remplacent pas un
essai sur ton rameur.

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
- Ajout de `hacs.json` et d'un exemple de carte Lovelace (`dashboard/carte_rameur.yaml`, nécessite button-card, apexcharts-card et config-template-card).

### v0.14.0 - Carte Lovelace intégrée
L'intégration fournit maintenant sa propre carte, sans aucune dépendance (ni HACS, ni autre carte). Elle est chargée automatiquement : redémarre Home Assistant après la mise à jour, puis vide le cache du navigateur (Ctrl + F5).

Ajout dans un tableau de bord : Modifier > Ajouter une carte > Manuel :

```yaml
type: custom:domyos-rower-card
plug_entity: switch.prise_rameur            # facultatif : prise connectée du rameur (bouton masqué sans cette ligne)
title: Rameur Domyos                        # facultatif
```

Les entités du rameur sont trouvées automatiquement. Si plusieurs rameurs sont installés, ajoute `device_id:`. La carte affiche le bouton de séance, le temps, l'allure, la distance, la cadence, les coups, la puissance, les calories, un graphe de toute la séance (puissance et résistance), la résistance (− / +), la prise du rameur (facultatif), le Bluetooth (avec son état), l'entraînement choisi, la dernière séance et les boutons Fichiers / Garmin. Une version Lovelace YAML équivalente (avec button-card, apexcharts-card et config-template-card) reste disponible dans `dashboard/carte_rameur.yaml`.

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

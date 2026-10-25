# Référence technique

Détails du protocole, des entités, des fichiers exportés et du diagnostic. Retour au [README](../README.md).

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

## Tests
`tests/` contient 22 tests exécutés sur Home Assistant 2025.1.4 avec
`pytest-homeassistant-custom-component` (assistant de configuration, options, enregistrement,
fichiers, envoi Garmin simulé, logique Bluetooth avec un faux rameur). Le fichier FIT est lu par
le décodeur officiel de Garmin (`garmin-fit-sdk`) et les numéros de champs sont comparés à son profil. Ils ne remplacent pas un
essai sur ton rameur.


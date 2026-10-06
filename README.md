# Domyos Rower — intégration Home Assistant (Bluetooth / proxy ESPHome) v0.5.0

Port en Python de ce que fait QZ (qdomyos-zwift) avec les rameurs Domyos.
Elle passe par la pile Bluetooth de Home Assistant, donc par tes proxies ESP32.

## Installation / mise à jour
1. Remplace le dossier `/config/custom_components/domyos_rower` par celui du zip.
2. Redémarre Home Assistant.
3. Réveille le rameur (tire la poignée / active le Bluetooth dans son menu).

Le proxy ESPHome doit autoriser les connexions actives :

    bluetooth_proxy:
      active: true

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
- **Écran de la console** (protocole Domyos uniquement) : comme QZ, l'intégration rafraîchit
  l'afficheur une fois par seconde (temps, vitesse, cadence, calories, distance, pouls). En
  FTMS, QZ n'écrit rien sur l'écran, donc l'intégration non plus.
- **Résistance (consigne)** : curseur. En FTMS la commande est « Set Target Resistance »
  (0x04, valeur × 10, comme QZ) et les bornes sont lues sur le rameur (0x2AD6) ; sinon
  1 à 15. En protocole Domyos, 1 à 15.
- **Connexion Bluetooth** (interrupteur) : libère le rameur pour ton téléphone / QZ.
- **État** (diagnostic) : disabled / waiting / connecting / connected / error, avec en
  attributs le protocole, la dernière erreur, les services GATT et la plage de résistance.

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
- Pas de démarrage/arrêt de séance depuis HA, ni d'écriture sur l'écran de la console.

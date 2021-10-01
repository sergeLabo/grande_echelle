# Grande Echelle

### Installation
Testée avec Debian 11 Bullseye

Les packages python sont installés dans un virtualenv parce que c'est facile, ça marche bien, c'est la bonne façon de procéder.

#### RealSense D 455
``` bash
sudo apt-key adv --keyserver keys.gnupg.net --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE
sudo apt install software-properties-common
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo focal main" -u
sudo apt install librealsense2-dkms
```

#### Coral
``` bash
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
sudo apt install curl
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt update
sudo apt install python3-tflite-runtime edgetpu-compiler gasket-dkms
sudo apt install python3-pycoral libedgetpu1-std
```

#### Python
Installe tous les packages nécessaires dans un dossier /mon_env dans le dossier /grande_echelle
``` bash
# Mise à jour de pip
sudo apt install python3-pip
python3 -m pip install --upgrade pip
# Installation de venv
sudo apt install python3-venv

# Installation de l'environnement
cd /le/dossier/de/grande_echelle/
# Création du dossier environnement si pas encore créé
python3 -m venv --system-site-packages mon_env
# Activation
source mon_env/bin/activate
# Installation des packages
python3 -m pip install -r requirements.txt
```

### Excécution
Copier coller le lanceur grande-echelle.desktop sur le Bureau

Il faut le modifier avec Propriétés: adapter le chemin à votre cas.

Ce lanceur lance un terminal et l'interface graphique. Clic dans la fenêtre de l'interface pour l'activer, puis clic sur

Lancer Grande Echelle

### Reset à la version de GitHub

``` bash
git fetch origin
git reset --hard origin/master
```

### Fichier de configuration

#### Exemple des valeurs par défaut du fichier de config grande_echelle.ini

```
[camera]
width_input = 1280
height_input = 720

[pose]
brightness = 0.05
contrast = 0.13
threshold = 0.8
around = 1

[histopocene]
frame_rate_du_film = 25
film = ge_1920_25_moy.mp4
profondeur_mini = 1000
profondeur_maxi = 3800
x_maxi = 230
d_mode = exponentiel
x_mode = simple
d_lissage = 100
x_coeff = 0.2
etendue = 200
x_lissage = 50
info = 0
```

#### Utilisation
* Bascule full_screen en cours en activant la fenêtre à aggrandir puis:
    * espace
* Options permet de modifier tous les paramètres mais il faut relancer l'application pour les paramètres non modifiables à chaud


#### Explications sur les  paramètres

* brightness et contrast: régler au centre de la plage de bonne détection
* threshold = 80 seuil de confiance de la détection, plus c'est grand moins il y a d'erreur, mais plus la détection est difficile.
* around = 1 nombre de pixels autour de la détection pour calcul moyenné de la profondeur, 1 à 3 mais ne change rien
* frame_rate_du_film = 25 Créer le film avec cette valeur !
* film = 'ge_1920_25_moy.mp4' 1920x1080, 25 fps!
* d_lissage = 30 lissage de la profondeur en mode rapide
* d_mode = 'exponentiel' pour le calcul de la moyenne glissante, réagit plus vite
* profondeur_mini = 1200, cale le 0 de la profondeur
* profondeur_maxi = 4000, limite le maxi
* x_maxi = 1500, limite la plage des x
* x_coeff = 0.2, pourcentage d'influence des x en mode lent
* etendue = 200, plage de variation de la profondeur, au dessus utilisation de la profondeur, en dessous utilisation des x
* x_lissage = 50, lissage des x en mode lent, pour le calcul de la moyenne glissante
* x_mode = 'simple', calcul de la moyenne glissante sans pondération


### LICENSE

#### Apache License, Version 2.0

* pose_engine.py
* posenet_histopocene.py
* pyrealsense2

#### Licence GPL v3

* tous les autres fichiers

#### Creative Commons

[Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License](http://oer2go.org/mods/en-boundless/creativecommons.org/licenses/by-nc-nd/4.0/legalcode.html)

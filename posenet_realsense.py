
# Posenet
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


## pyrealsense2
## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2015-2017 Intel Corporation. All Rights Reserved.


"""
Echap pour finir proprement le script

Capture de 1 squelette, celui au plus près du centre,
avec
camera Intel RealSense D455, Google posenet et Google Coral.

Les distances en 3D sont en mm, comme dans grande echelle!
"""


import os
from time import time, sleep
from threading import Thread

import numpy as np
import cv2

import pyrealsense2 as rs
from my_realsense import MyRealSense

from my_posenet_conversion import MyPoseNetConversion
from my_posenet import MyPosenet
from pose_engine import EDGES

from my_config import MyConfig
from filtre import moving_average



class PosenetRealsenseViewer:
    """Affichage dans une fenêtre OpenCV, et gestion des fenêtres"""

    def __init__(self, conn, config):

        self.conn = conn
        self.config = config
        self.loop = 1
        self.t0 = time()

        self.mode_expo = int(self.config['histopocene']['mode_expo'])
        self.full_screen = int(self.config['histopocene']['full_screen'])
        if self.mode_expo:
            self.info = 0
            self.full_screen = 0

        self.create_window()

    def create_window(self):
        if not self.mode_expo:
            cv2.namedWindow('posecolor', cv2.WND_PROP_FULLSCREEN)

    def set_window(self):
        if not self.mode_expo:
            if self.full_screen:
                cv2.setWindowProperty(  'posecolor',
                                        cv2.WND_PROP_FULLSCREEN,
                                        cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty(  'posecolor',
                                        cv2.WND_PROP_FULLSCREEN,
                                        cv2.WINDOW_NORMAL)

    def draw_line(self):
        # Ligne au centre
        h = self.img.shape[0]
        w = self.img.shape[1]
        cv2.line(self.img, (int(w/2), 0),
                                 (int(w/2), h),
                                 (255, 255, 255), 2)

    def viewer(self):
        # ############### Affichage de l'image
        # La ligne au centre
        self.draw_line()

        if not self.mode_expo:
            cv2.imshow('posecolor', self.img)

        # Calcul du FPS, affichage toutes les 10 s
        if time() - self.t0 > 10:
            print("FPS =", int(self.nbr/10))
            self.t0, self.nbr = time(), 0

        k = cv2.waitKey(1)
        # Pour quitter
        if k == 27:  # Esc
            self.conn.send(['quit', 1])
            self.loop = 0
            # # self.conn_loop = 0
            print("Quit dans Posenet Realsense")

            self.close()

    def close(self):
        cv2.destroyAllWindows()



class PosenetRealsense(MyRealSense, MyPosenet, PosenetRealsenseViewer):
    """ Capture avec  Camera RealSense D455
        Détection de la pose avec Coral USB Stick
        Calcul des coordonnées 3D
            et envoi de la moyenne des profondeurs pour 1 personnage.
        La profondeur est le 3ème dans les coordonnées d'un point 3D,
        x = horizontale, y = verticale
    """

    def __init__(self, conn, current_dir, config):
        """Les paramètres sont à définir dans le fichier posenet.ini
        En principe, rien ne doit être modifié dans les autres paramètres.
        """
        print("Lancement de PosenetRealsense")

        MyRealSense.__init__(self, config)
        PosenetRealsenseViewer.__init__(self, conn, config)

        self.conn = conn
        self.current_dir = current_dir

        self.loop = 1
        self.conn_loop = 1

        if self.conn:
            self.receive_thread()

        self.config = config

        # Taille d'image possible: 1280x720, 640x480 seulement
        # 640x480 est utile pour fps > 30
        # Les modèles posenet imposent une taille d'image
        self.width = int(self.config['camera']['width_input'])
        self.height = int(self.config['camera']['height_input'])
        MyPosenet.__init__(self, self.width, self.height)

        # Luminosité
        self.brightness = float(self.config['pose']['brightness'])
        # Contrast
        self.contrast = float(self.config['pose']['contrast'])
        # Seuil de confiance de reconnaissance du squelette
        self.threshold = float(self.config['pose']['threshold'])
        # Activation de la fonction qui mange un peu de FPS
        self.brightness_contrast_on = int(self.config['pose']['brightness_contrast_on'])

        # Pour éliminer les trops loing ou trop près, en mêtre
        self.profondeur_maxi = int(self.config['histopocene']['profondeur_maxi'])
        self.profondeur_mini = int(self.config['histopocene']['profondeur_mini'])
        self.largeur_maxi = int(self.config['histopocene']['largeur_maxi'])
        self.full_screen = int(self.config['histopocene']['full_screen'])
        self.mode_expo = int(self.config['histopocene']['mode_expo'])

    def receive_thread(self):
        print("Lancement du thread receive dans posenet")
        t = Thread(target=self.receive)
        t.start()

    def receive(self):
        while self.conn_loop:
            data = self.conn.recv()

            if data:
                if data[0] == 'quit':  # il doit être en premier
                    print("Quit reçu dans PosenetRealsense")
                    self.loop = 0
                    self.conn_loop = 0
                    os._exit(0)

                if data[0] == 'threshold':
                    print('threshold reçu dans posenet:', data[1])
                    self.threshold = data[1]

                if data[0] == 'brightness':
                    print('brightness reçu dans posenet:', data[1])
                    self.brightness = data[1]

                if data[0] == 'contrast':
                    print('contrast reçu dans posenet:', data[1])
                    self.contrast = data[1]

                if data[0] == 'brightness_contrast_on':
                    print('brightness_contrast_on reçu dans posenet:', data[1])
                    self.brightness_contrast_on = data[1]

                if data[0] == 'profondeur_mini':
                    print('profondeur_mini reçu dans posenet::', data[1])
                    self.profondeur_mini = data[1]

                if data[0] == 'profondeur_maxi':
                    print('profondeur_maxi reçu dans posenet::', data[1])
                    self.profondeur_maxi = data[1]

                if data[0] == 'largeur_maxi':
                    print('largeur_maxi reçu dans posenet:', data[1])
                    self.largeur_maxi = data[1]

                if data[0] == 'mode_expo':
                    print('mode_expo reçu dans posenet:', data[1])
                    self.mode_expo = data[1]

            sleep(0.001)

    def main(self, outputs):
        """ Appelé depuis la boucle infinie, c'est le main d'une frame."""
        self.skelets_2D, self.skelets_3D, self.centers = None, None, None

        # Récupération de tous les squelettes
        if outputs:
            # liste des squelettes 2D, un squelette = dict de 17 keypoints
            self.skelets_2D = MyPoseNetConversion(outputs, self.threshold).skeletons

            if self.skelets_2D:
                # Ajout de la profondeur pour 3D, et capture des couleurs
                # Liste des squelettes 3D, un squelette = list de 17 keypoints
                # un keypoint = liste de 3 coordonnées
                self.skelets_3D = self.get_skelets_3D()
                # Calcul de tous les centres
                self.centers = get_center_3D(self.skelets_3D)

                # Tri des squelettes dans la zone acceptable et pas tout None
                self.get_only_skelets_in_zone_and_valable()

                # self.skelets_2D est trié ici, ce n'est pas le même que ci-dessus
                if self.skelets_2D:
                    # Détermination du squelette au centre
                    self.get_who()
                    self.draw_text()
                    self.send()
                    # Dessin
                    self.draw_all_poses()

    def get_only_skelets_in_zone_and_valable(self):
        """Elimination des squelettes pas dans la zone
                profondeur mini à maxi et dans largeur_maxi
        et qui ne sont pas [None]*17
        """
        skelets_2D, skelets_3D, centers = [], [], []

        for i in range(len(self.skelets_2D)):
            # Si il n'y a pas de centre, il n'y a pas de personnage
            if self.centers[i]:
                # Entre mini maxi
                if self.profondeur_mini < self.centers[i][2] < self.profondeur_maxi:
                    # Pas trop écarté
                    if abs(self.centers[i][0]) < self.largeur_maxi:
                        # Squelette 3D valide, ne devrait pas arrivé si self.centers[i]
                        if self.skelets_3D[i] != [None]*17:
                            skelets_2D.append(self.skelets_2D[i])
                            skelets_3D.append(self.skelets_3D[i])
                            centers.append(self.centers[i])

        self.skelets_2D = skelets_2D
        self.skelets_2D = skelets_2D
        self.centers = centers

    def get_who(self):
        """Détermination du squelette au centre
        self.centers = [[x, y , z], ...]
        all_x =    [-0.5, 0.8, 0.6]
        abs_all_x = [0.5, 0.8, 0.6]
        """
        if self.centers:
            # Recherche de celui au centre
            all_x = [c[0] for c in self.centers]
            abs_all_x = [abs(c[0]) for c in self.centers]

            if abs_all_x:  # si abs_all_x is not [], alors all_x est aussi
                mini = min(abs_all_x)
                # Index du mini des abs est le même que all_x
                self.who = abs_all_x.index(mini)
                self.depth = self.centers[self.who][2]
                # La position en x pour affichage
                self.x =  self.centers[self.who][0]
        else:
            self.who, self.depth, self.x = None, 0, self.x

    def get_skelets_3D(self):
        """A partir des squelettes 2D détectés dans l'image,
        retourne les squelettes 3D
        """
        skelets_3D = []
        for xys in self.skelets_2D:
            pts = self.get_points_3D(xys)
            # pts peut être [None]*17
            skelets_3D.append(pts)
        return skelets_3D

    def get_points_3D(self, xys):
        """Trouve les points 3D pour un squelette
        Si tous les points sont inférieur à la valeur du threshold,
            points_3D == [None]*17:
        """

        # Les coordonnées des 17 points 3D avec qq None
        points_3D = [None]*17

        # Parcours des squelettes
        for i, xy in enumerate(xys):
            if xy:
                x = xy[0]
                y = xy[1]
                # Calcul de la profondeur du point
                profondeur = self.get_profondeur_du_point(x, y)
                if profondeur:
                    # Calcul les coordonnées 3D avec x et y coordonnées dans
                    # l'image et la profondeur du point
                    # Changement du nom de la fonction trop long
                    point_2D_to_3D = rs.rs2_deproject_pixel_to_point
                    point_with_deph = point_2D_to_3D(self.depth_intrinsic,
                                                     [x, y],
                                                     profondeur)
                    # Conversion des m en mm
                    points_3D[i] = [int(1000*x) for x in point_with_deph]

        return points_3D

    def get_profondeur_du_point(self, x, y):
        """Calcul la moyenne des profondeurs des pixels autour du point considéré
        Filtre les absurdes et les trop loins
        """
        profondeur = None
        distances = []
        # around = nombre de pixel autour du points
        x_min = max(x - 1, 0)
        x_max = min(x + 1, self.depth_frame.width)
        y_min = max(y - 1, 0)
        y_max = min(y + 1, self.depth_frame.height)

        for u in range(x_min, x_max):
            for v in range(y_min, y_max):
                # Profondeur du point de coordonnée (u, v) dans l'image
                distances.append(self.depth_frame.get_distance(u, v))

        # Si valeurs non trouvées, retourne [0.0, 0.0, 0.0, 0.0]
        # Remove the item 0.0 for all its occurrences
        dists = [i for i in distances if i != 0.0]
        dists_sort = sorted(dists)
        if len(dists_sort) > 2:
            # Suppression du plus petit et du plus grand
            goods = dists_sort[1:-1]
            # TODO: rajouter un filtre sur les absurdes ?

            # Calcul de la moyenne des profondeur
            profondeur = get_average_list_with_None(goods)

        return profondeur

    def draw_all_poses(self):
        for i, skelet in enumerate(self.skelets_2D):
            if skelet:
                if i == self.who:
                    color = [0, 255, 0]
                else:
                    color = [0, 0, 255]
                self.draw_pose(skelet, color)

    def draw_pose(self, xys, color):
        """Affiche les points 2D, et les 'os' dans l'image pour un acteur
        xys = [[790, 331], [780, 313], None,  ... ]
        """

        # Dessin des points
        for point in xys:
            if point:
                x = point[0]
                y = point[1]
                cv2.circle(self.img, (x, y), 5, color=(100, 100, 100),
                                                                  thickness=-1)
                cv2.circle(self.img, (x, y), 6, color=color, thickness=1)

        # Dessin des os
        for a, b in EDGES:
            a = a.value  # 0 à 16
            b = b.value  # 0 à 16

            # Os seulement entre keypoints esxistants
            if not xys[a] or not xys[b] :
                continue

            # Les 2 keypoints existent
            ax, ay = xys[a]
            bx, by = xys[b]
            cv2.line(self.img, (ax, ay), (bx, by), color, 2)

    def draw_text(self):
        """Affichage de la moyenne des profondeurs et x du personnage vert"""
        d = {   "Profondeur": self.depth,
                "Largeur": self.x,
                "Threshold": self.threshold,
                "Brightness": self.brightness,
                "Contrast": self.contrast,
                "Profondeur mini": self.profondeur_mini,
                "Profondeur maxi": self.profondeur_maxi,
                "Largeur maxi": self.largeur_maxi}

        i = 0
        for key, val in d.items():
            text = key + " : " + str(val)
            cv2.putText(self.img,  # image
                        text,
                        (30, 80*i+150),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        2,  # taille police
                        (0, 255, 0),  # couleur
                        2)  # épaisseur
            i += 1

    def send(self):
        if self.conn and self.depth:
            self.conn.send(['from_realsense', int(self.depth)])

    def run(self):
        """Boucle infinie, quitter avec Echap dans la fenêtre OpenCV"""

        t0 = time()
        self.nbr = 0

        while self.loop:
            self.nbr += 1

            # ############### RealSense
            frames = self.pipeline.wait_for_frames(timeout_ms=80)

            # Align the depth frame to color frame
            aligned_frames = self.align.process(frames)

            color = aligned_frames.get_color_frame()
            self.depth_frame = aligned_frames.get_depth_frame()

            if not self.depth_frame and not color:
                continue

            color_data = color.as_frame().get_data()
            self.img = np.asanyarray(color_data)
            if self.brightness_contrast_on:
                self.img = apply_brightness_contrast(   self.img,
                                                        self.brightness,
                                                        self.contrast)

            # ############### Posenet
            outputs = self.get_outputs(self.img)

            # Recherche des squelettes
            self.main(outputs)

            # Affichage
            self.viewer()



def apply_brightness_contrast(img, brightness=0, contrast=0):
    """Correction des Luminosité et Contraste
    Retourne l'image corrigée

    Brightness range -255 to 255
    Contrast range -127 to 127
    """

    brightness = (255*brightness + 255)
    contrast = (127*contrast + 127)

    brightness = int((brightness - 0) * (255 - (-255)) / (510 - 0) + (-255))

    contrast = int((contrast - 0) * (127 - (-127)) / (254 - 0) + (-127))

    if brightness != 0:
        if brightness > 0:
            shadow = brightness
            max = 255
        else:
            shadow = 0
            max = 255 + brightness

        al_pha = (max - shadow) / 255
        ga_mma = shadow

        # addWeighted calculates the weighted sum of two arrays
        cal = cv2.addWeighted(img, al_pha, img, 0, ga_mma)

    else:
        cal = img

    if contrast != 0:
        Alpha = float(131 * (contrast + 127)) / (127 * (131 - contrast))
        Gamma = 127 * (1 - Alpha)

        # addWeighted calculates the weighted sum of two arrays
        cal = cv2.addWeighted(cal, Alpha, cal, 0, Gamma)

    return cal


def get_center_2D(skelet):
    center = []
    for i in range(2):
        center.append(get_moyenne(skelet, i))
    return center


def get_center_3D(skelets_3D):
    """Retourne la liste des centres des squelettes 3D"""
    centers = []
    for skelet in skelets_3D:
        if skelet != [None]*17:
            center = []
            for i in range(3):
                center.append(get_moyenne(skelet, i))
            centers.append(center)
        else:
            centers.append(None)

    return centers


def get_moyenne(points, indice):
    """Calcul la moyenne d'une coordonnée des points,
    la profondeur est le 3 ème = z, le y est la verticale
    indice = 0 pour x, 1 pour y, 2 pour z
    """

    somme = 0
    n = 0
    for i in range(17):
        if points[i]:
            p = points[i][indice]
            if p:
                n += 1
                somme += p
    if n != 0:
        moyenne = int(somme/n)
    else:
        moyenne = None

    return moyenne


def get_average_list_with_None(liste):
    """Calcul de la moyenne des valeurs de la liste, sans tenir compte des None.
    liste = list de int ou float
    liste = [1, 2, None, ..., 10.0, None]

    Retourne un float
    Si la liste ne contient que des None, retourne None
    """
    # dtype permet d'accepter les None
    liste_array = np.array(liste, dtype=np.float64)

    return np.nanmean(liste_array)


def posenet_realsense_run(conn, current_dir, config):

    pnrs = PosenetRealsense(conn, current_dir, config)
    pnrs.run()

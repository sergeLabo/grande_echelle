
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
import enum
from threading import Thread

import numpy as np
import cv2
import pyrealsense2 as rs

from pose_engine import PoseEngine
from pose_engine import EDGES

from my_config import MyConfig
from filtre import moving_average


class PoseNetConversion:
    """Conversion de posenet vers ma norme
    1 ou 2 squelettes capturés:

    [Pose(keypoints={
    <KeypointType.NOSE: 0>: Keypoint(point=Point(x=652.6, y=176.6), score=0.8),
    <KeypointType.LEFT_EYE: 1>: Keypoint(point=Point(x=655.9, y=164.3), score=0.9)},
    score=0.53292614),

    Pose(keypoints={
    <KeypointType.NOSE: 0>: Keypoint(point=Point(x=329.2562, y=18.127075), score=0.91656697),
    <KeypointType.LEFT_EYE: 1>: Keypoint(point=Point(x=337.1971, y=4.7381477), score=0.14472471)},
    score=0.35073516)]

    Conversion en:
    skeleton1 = {0: (x=652.6, y=176.6),
    et
    skeleton2 = {0: (x=329.2, y=18.1), ... etc ... jusque 16
    soit
    skeleton2 = {0: (329.2, 18.1),

    skeletons = list de skeleton = [skeleton1, skeleton2]
    """

    def __init__(self, outputs, threshold):

        self.outputs = outputs
        self.threshold = threshold
        self.skeletons = []
        self.conversion()

    def conversion(self):
        """Convertit les keypoints posenet dans ma norme"""

        self.skeletons = []
        for pose in self.outputs:
            xys = self.get_points_2D(pose)
            self.skeletons.append(xys)

    def get_points_2D(self, pose):
        """ ma norme = dict{index du keypoint: (x, y), }
        xys = {0: (698, 320), 1: (698, 297), 2: (675, 295), .... } """

        xys = {}
        # # print("dans PoseNetConversion:", self.threshold)
        for label, keypoint in pose.keypoints.items():
            if keypoint.score > self.threshold:
                xys[label.value] = [int(keypoint.point[0]),
                                    int(keypoint.point[1])]
        return xys


class Personnage:
    """Permet de stocker facilement les attributs d'un personnage,
    et de les reset-er.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.who = None
        self.xys = None
        self.points_3D = None,
        self.depth = None
        self.x = None


class PosenetRealsense:
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

        self.conn = conn
        self.current_dir = current_dir

        self.loop = 1
        self.conn_loop = 1

        if self.conn:
            self.receive_thread()

        self.config = config

        self.posenet_shared_lib = (f'{self.current_dir}/posenet_lib/'
                                    f'{os.uname().machine}/posenet_decoder.so')
        print("posenet_shared_lib =", self.posenet_shared_lib)

        # Luminosité
        self.brightness = float(self.config['pose']['brightness'])
        # Contrast
        self.contrast = float(self.config['pose']['contrast'])
        # Seuil de confiance de reconnaissance du squelette
        self.threshold = float(self.config['pose']['threshold'])

        # Nombre de pixels autour du point pour moyenne du calcul de profondeur
        self.around = int(self.config['pose']['around'])

        # Taille d'image possible: 1280x720, 640x480 seulement
        # 640x480 est utile pour fps > 30
        # Les modèles posenet imposent une taille d'image
        self.width = int(self.config['camera']['width_input'])
        self.height = int(self.config['camera']['height_input'])

        # Pour éliminer les trops loing ou trop près, en mêtre
        self.profondeur_maxi = int(self.config['histopocene']['profondeur_maxi'])
        self.profondeur_mini = int(self.config['histopocene']['profondeur_mini'])
        self.x_maxi = int(self.config['histopocene']['x_maxi'])

        self.set_pipeline()
        self.get_engine()

        # Toutes les datas du personnage vert
        self.perso = Personnage()

        self.create_window()

    def create_window(self):
        # fullscreen property (can be WINDOW_NORMAL or WINDOW_FULLSCREEN)
        cv2.namedWindow('posecolor', cv2.WND_PROP_FULLSCREEN)
        # Plein écran de la fenêtre OpenCV
        self.full_screen = 0

    def get_engine(self):
        """Crée le moteur de calcul avec le stick Coral"""

        res = str(self.width) + 'x' + str(self.height)
        print("width:", self.width, ", height:", self.height)
        print("Résolution =", res)

        if res == "1280x720":
            self.src_size = (1280, 720)
            self.appsink_size = (1280, 720)
            model_size = (721, 1281)
        elif res == "640x480":
            self.src_size = (640, 480)
            self.appsink_size = (640, 480)
            model_size = (481, 641)
        else:
            print(f"La résolution {res} n'est pas possible.")
            self.conn.send(['quit', 1])
            sleep(0.1)
            os._exit(0)

        # TODO
        model = (f'{self.current_dir}'
                 f'/models/mobilenet/posenet_mobilenet_v1_075_'
                 f'{model_size[0]}_{model_size[1]}'
                 f'_quant_decoder_edgetpu.tflite'   )
        print('Loading model: ', model)

        try:
            self.engine = PoseEngine(   model,
                                        self.posenet_shared_lib,
                                        mirror=False)
        except:
            print(f"Pas de Stick Coral connecté.")
            self.conn.send(['quit', 1])
            sleep(0.1)
            os._exit(0)

    def set_pipeline(self):
        """Crée le flux d'image avec la caméra D455"""

        self.pipeline = rs.pipeline()
        config = rs.config()
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        try:
            pipeline_profile = config.resolve(pipeline_wrapper)
        except:
            print(f"Pas de Capteur Realsense connecté")
            if self.conn:
                self.conn.send(['quit', 1])
            sleep(0.1)
            os._exit(0)

        device = pipeline_profile.get_device()
        config.enable_stream(rs.stream.color, self.width, self.height,
                                                            rs.format.bgr8, 30)
        config.enable_stream(rs.stream.depth, self.width, self.height,
                                                            rs.format.z16, 30)
        self.pipeline.start(config)
        self.align = rs.align(rs.stream.color)
        unaligned_frames = self.pipeline.wait_for_frames()
        frames = self.align.process(unaligned_frames)
        depth = frames.get_depth_frame()
        self.depth_intrinsic = depth.profile.as_video_stream_profile().intrinsics

        # Affichage de la taille des images
        color_frame = frames.get_color_frame()
        img = np.asanyarray(color_frame.get_data())
        print(f"Taille des images:"
              f"     {img.shape[1]}x{img.shape[0]}")

    def receive_thread(self):
        print("Lancement du thread receive dans posenet")
        t = Thread(target=self.receive)
        t.start()

    def receive(self):
        while self.conn_loop:
            data = self.conn.recv()
            if data:
                if data[0] == 'quit':
                    print("Quit reçu")
                    self.loop = 0
                    self.conn_loop = 0
                    os._exit(0)

                elif data[0] == 'threshold':
                    print('threshold reçu dans posenet:', data[1])
                    self.threshold = data[1]

                elif data[0] == 'brightness':
                    print('brightness reçu dans posenet:', data[1])
                    self.brightness = data[1]

                elif data[0] == 'contrast':
                    print('contrast reçu dans posenet:', data[1])
                    self.contrast = data[1]

                elif data[0] == 'profondeur_mini':
                    print('profondeur_mini reçu dans posenet::', data[1])
                    self.profondeur_mini = data[1]

                elif data[0] == 'profondeur_maxi':
                    print('profondeur_maxi reçu dans posenet::', data[1])
                    self.profondeur_maxi = data[1]

                elif data[0] == 'x_maxi':
                    print('x_maxi reçu dans posenet:', data[1])
                    self.x_maxi = data[1]


            sleep(0.001)

    def get_personnages(self, outputs):
        """ Appelé depuis la boucle infinie, c'est le main d'une frame.
                Récupération de tous les squelettes
                Definition de who
        """

        # Récupération de tous les squelettes
        persos_2D = PoseNetConversion(outputs, self.threshold).skeletons  # les xys

        # Ajout de la profondeur pour 3D
        persos_3D = self.get_persos_3D(persos_2D)

        # Récup de who, apply to self.perso
        who = self.get_who(persos_3D)

        # Apply who, pour le personnage vert et les rouges
        self.apply_who(who, persos_2D, persos_3D)

    def apply_who(self, who, persos_2D, persos_3D):
        """Apply who pour le personnage vert et les rouges
        Le vert est self.perso, les autres sont dans self.perso_bad
        """

        # Application à perso pour définir le vert
        if who is not None:
            self.perso.who = who
            self.perso.xys = persos_2D[who]
            self.perso.points_3D = persos_3D[who]
            # 2 est la profondeur en z
            self.perso.depth = get_moyenne(persos_3D[who], 2)
            # 0 est le x, 1 le y
            self.perso.x = get_moyenne(persos_3D[who], 0)

        # Affichage du personnage vert
        if self.perso.who is not None:
            self.draw_pose(self.color_arr, self.perso.xys, color=[0, 255, 0])

        # Affichage de la profondeur et de x du perso vert
        self.draw_depth_values()

        # Affichage des autres personnages, persos_2D=liste de dict
        for p, xys in enumerate(persos_2D):
            if p != who:
                self.draw_pose(self.color_arr, xys, color=[0, 0, 255])

    def get_who(self, persos_3D):
        """who est l'indice du personnage vert, dans la liste des perso 3D"""

        who = None
        all_x_z = []

        if persos_3D:
            for perso in persos_3D:
                # Le x est la 1ère valeur
                if perso:
                    x = get_moyenne(perso, 0)
                    z = get_moyenne(perso, 2)
                    if x and z:
                        all_x_z.append([x, z])
                    else:
                        all_x_z.append([100000, 100000])

        # [[200, 5000], [500, 3000]]
        # Je ne garde que ceux devant profondeur_maxi, derrière le mini,
        # et dans la plage des x
        all_x = []  # tous les x valides
        for item in all_x_z:
            if self.profondeur_mini < item[1] < self.profondeur_maxi\
                    and -self.x_maxi < item[0] < self.x_maxi:
                all_x.append(item[0])

        if all_x:
            all_x_sorted = sorted(all_x)
            who = all_x.index(all_x_sorted[0])

        return who

    def get_persos_3D(self, persos_2D):
        """Coordonnées 3D avec les 2D de toutes les détections"""
        persos_3D = []
        for xys in persos_2D:
            pts = self.get_points_3D(xys)
            persos_3D.append(pts)
        return persos_3D

    def get_points_3D(self, xys):
        """Calcul des coordonnées 3D dans un repère centré sur la caméra,
        avec le z = profondeur
        La profondeur est une moyenne de la profondeur des points autour,
        sauf les extrêmes, le plus petit et le plus gand.
        TODO: rajouter un filtre sur les absurdes ?
        """

        points_3D = [None]*17
        for key, val in xys.items():
            if val:
                #
                distances = []
                x, y = val[0], val[1]
                # around = nombre de pixel autour du points
                x_min = max(x - self.around, 0)
                x_max = min(x + self.around, self.depth_frame.width)
                y_min = max(y - self.around, 0)
                y_max = min(y + self.around, self.depth_frame.height)

                for u in range(x_min, x_max):
                    for v in range(y_min, y_max):
                        distances.append(self.depth_frame.get_distance(u, v))

                # Si valeurs non trouvées = [0.0, 0.0, 0.0, 0.0]
                # remove the item 0.0 for all its occurrences
                dists = [i for i in distances if i != 0.0]
                dists_sort = sorted(dists)
                if len(dists_sort) > 2:
                    goods = dists_sort[1:-1]

                    somme = 0
                    for item in goods:
                        somme += item
                    profondeur = somme/len(goods)
                    # Calcul les coordonnées 3D avec x et y coordonnées dans
                    # l'image et la profondeur du point
                    # Changement du nom de la fonction trop long
                    point_2D_to_3D = rs.rs2_deproject_pixel_to_point
                    point_with_deph_en_m = point_2D_to_3D(self.depth_intrinsic,
                                                     [x, y],
                                                     profondeur)
                    point_with_deph_en_mm = [int(1000*x) for x in point_with_deph_en_m]
                    points_3D[key] = point_with_deph_en_mm

        return points_3D

    def draw_pose(self, img, xys, color):
        """Affiche les points 2D, et les 'os' dans l'image pour un personnage
        xys = {0: [790, 331], 2: [780, 313],  ... }
        """
        points = []
        for xy in xys.values():
            points.append(xy)

        # Dessin des points
        for point in points:
            x = point[0]
            y = point[1]
            cv2.circle(img, (x, y), 5, color=(100, 100, 100), thickness=-1)
            cv2.circle(img, (x, y), 6, color=color, thickness=1)

        # Dessin des os
        for a, b in EDGES:
            if a not in xys or b not in xys: continue
            ax, ay = xys[a]
            bx, by = xys[b]
            cv2.line(img, (ax, ay), (bx, by), color, 2)

    def draw_depth_values(self):
        """Affichage de la moyenne des profondeurs et x en gros
        du personnage vert
        """

        if self.perso.depth is not None:
            depth = self.perso.depth
            cv2.putText(self.color_arr,  # image
                        str(int(depth)),  # text
                        (30, 80),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        3,  # taille police
                        (0, 255, 0),  # couleur
                        12)  # épaisseur

        if self.perso.x is not None:
            x = self.perso.x
            cv2.putText(self.color_arr,  # image
                        str(int(x)),  # text
                        (30, 180),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        3,  # taille police
                        (0, 255, 0),  # couleur
                        12)  # épaisseur

    def draw_text(self):
        d = {   "Threshold": self.threshold,
                "Brightness": self.brightness,
                "Contrast": self.contrast,
                "Profondeur mini": self.profondeur_mini,
                "Profondeur maxi": self.profondeur_maxi,
                "X maxi": self.x_maxi}

        i = 0
        for key, val in d.items():
            text = key + " : " + str(val)
            cv2.putText(self.color_arr,  # image
                        text,
                        (30, 80*i+250),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        1,  # taille police
                        (0, 255, 0),  # couleur
                        2)  # épaisseur
            i += 1

    def draw_line(self):
        # Ligne au centre
        h = self.color_arr.shape[0]
        w = self.color_arr.shape[1]
        cv2.line(self.color_arr, (int(w/2), 0),
                                 (int(w/2), h),
                                 (255, 255, 255), 2)


    def set_window(self):
        if self.full_screen:
            cv2.setWindowProperty(  'posecolor',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(  'posecolor',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_NORMAL)

    def send(self):
        if self.conn and self.perso.x and self.perso.depth:
            self.conn.send(['from_realsense', int(self.perso.x),
                                              int(self.perso.depth)])

    def run(self):
        """Boucle infinie, quitter avec Echap dans la fenêtre OpenCV"""

        t0 = time()
        nbr = 0

        while self.loop:
            nbr += 1
            frames = self.pipeline.wait_for_frames()
            # Align the depth frame to color frame
            aligned_frames = self.align.process(frames)

            color = aligned_frames.get_color_frame()
            self.depth_frame = aligned_frames.get_depth_frame()
            if not self.depth_frame:
                continue

            # L'image captée
            color_data = color.as_frame().get_data()

            # Correction
            self.color_arr = np.asanyarray(color_data)
            self.color_arr = apply_brightness_contrast( self.color_arr,
                                                        self.brightness,
                                                        self.contrast)

            detection = self.engine.DetectPosesInImage
            outputs, inference_time = detection(self.color_arr)
            # Recherche des personnages captés
            self.get_personnages(outputs)

            self.send()

            # Affichage de l'image
            self.draw_text()
            self.draw_line()
            cv2.imshow('posecolor', self.color_arr)

            # Calcul du FPS, affichage toutes les 10 s
            if time() - t0 > 10:
                print("FPS =", int(nbr/10))
                t0, nbr = time(), 0

            k = cv2.waitKey(1)
            # Space pour full screen or not
            if k == 32:  # space
                if self.full_screen == 1:
                    self.full_screen = 0
                elif self.full_screen == 0:
                    self.full_screen = 1
                self.set_window()
            # Esc to  exit
            if k == 27:
                self.conn.send(['quit', 1])
                self.loop = 0

        # Du OpenCV propre
        cv2.destroyAllWindows()



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


def get_moyenne(points_3D, indice):
    """Calcul la moyenne d'une coordonnée des points,
    la profondeur est le 3 ème = z
    indice = 0 pour x, 1 pour y, 2 pour z
    """

    somme = 0
    n = 0
    for i in range(17):
        if points_3D[i]:
            n += 1
            somme += points_3D[i][indice]
    if n != 0:
        moyenne = somme/n
    else:
        moyenne = None

    return moyenne


def posenet_realsense_run(conn, current_dir, config):

    pnrs = PosenetRealsense(conn, current_dir, config)
    pnrs.run()




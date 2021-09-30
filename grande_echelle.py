

# Echap pour finir proprement le script
# Espace pour bascule, plein écran / normal


import os
from time import time, sleep
from threading import Thread

import cv2
import numpy as np

from filtre import moving_average
from my_config import MyConfig


class GrandeEchelle:
    """Affichage d'une frame spécique du film,
    en fonction de la réception de la profondeur
    avec conn de multiprocess.
    """

    def __init__(self, conn, current_dir, config):

        self.conn = conn
        self.config = config

        self.conn_loop = 1
        self.loop = 1
        self.frame = 0

        if self.conn:
            self.receive_thread()

        film = str(current_dir) + "/" + self.config['histopocene']['film']
        print("Le film est:", film)
        self.video = cv2.VideoCapture(film)
        self.lenght = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        print("Longueur du film :", self.lenght)  # 38400

        freq = int(self.config['histopocene']['frame_rate_du_film'])
        if freq != 0:
            self.tempo = int(1000/freq)
        else:
            print("Le frame rate du film est à 0 !")
            os._exit(0)

        self.profondeur_mini = int(self.config['histopocene']['profondeur_mini'])
        self.profondeur_maxi = int(self.config['histopocene']['profondeur_maxi'])
        self.x_maxi = int(self.config['histopocene']['x_maxi'])
        self.x_coeff = float(self.config['histopocene']['x_coeff'])
        self.etendue = int(self.config['histopocene']['etendue'])
        self.d_lissage = int(self.config['histopocene']['d_lissage'])
        self.d_mode = self.config['histopocene']['d_mode']
        self.x_lissage = int(self.config['histopocene']['x_lissage'])
        self.x_mode = self.config['histopocene']['x_mode']

        self.info = 0
        self.block = 0
        self.depth_fixe = 0
        # Image fixe si pas de capture à - 2 millions
        self.frame = 1
        self.histo_d = [0]*self.d_lissage
        self.histo_x = [0]*self.x_lissage

        self.create_window()

    def create_window(self):
        self.full_screen = 0
        cv2.namedWindow('histopocene', cv2.WND_PROP_FULLSCREEN)

    def receive_thread(self):
        t = Thread(target=self.receive)
        t.start()

    def receive(self):
        while self.conn_loop:
            data = self.conn.recv()
            self.conn.send(['bidon', 0])
            if data[0] == 'depth_x':
                if data[1] and data[2]:
                    # En mm, et dans la plage
                    depth = data[2]
                    depth -= self.profondeur_mini
                    # si 1800 avec 1200:5000, depth=1800-1200=600
                    # si 5200, depth=4000, 5000-1200=3800, depth=3800
                    if depth <= 0:
                        depth = 0
                    if depth > self.profondeur_maxi - self.profondeur_mini:
                        depth = self.profondeur_maxi - self.profondeur_mini

                    # En mm, entre -2000 et 2000
                    x = data[1]
                    # Utilisation de la surface de beaucoup de cm2
                    self.get_frame_slow(depth, x)

            elif data[0] == 'info':
                self.info = data[1]
                print("info reçu dans grande echelle:", self.info)

            elif data[0] == 'profondeur_mini':
                self.profondeur_mini = data[1]
                print("profondeur_mini reçu dans grande echelle:", self.profondeur_mini)

            elif data[0] == 'profondeur_maxi':
                self.profondeur_maxi = data[1]
                print("profondeur_maxi reçu dans grande echelle:", self.profondeur_maxi)

            elif data[0] == 'x_maxi':
                self.x_maxi = data[1]
                print("x_maxi reçu dans grande echelle:", self.x_maxi)

            elif data[0] == 'd_mode':
                self.d_mode = data[1]
                print("d_mode reçu dans grande echelle:", self.d_mode)

            elif data[0] == 'x_mode':
                self.x_mode = data[1]
                print("x_mode reçu dans grande echelle:", self.x_mode)

            elif data[0] == 'd_lissage':
                self.d_lissage = data[1]
                # # self.histo_d = [0]*self.d_lissage
                print("d_lissage reçu dans grande echelle:", self.d_lissage)

            elif data[0] == 'x_coeff':
                self.x_coeff = data[1]
                print("x_coeff reçu dans grande echelle:", self.x_coeff)

            elif data[0] == 'etendue':
                self.etendue = data[1]
                print("etendue reçu dans grande echelle:", self.etendue)

            elif data[0] == 'x_lissage':
                self.x_lissage = data[1]
                # # self.histo_x = [0]*self.x_lissage
                print("x_lissage reçu dans grande echelle:", self.x_lissage)

            elif data[0] == 'quit':
                self.loop = 0
                self.conn_loop = 0
                os._exit(0)

            sleep(0.001)

    def get_frame_slow(self, depth, x):
        """ Appelé à chaque frame"""

        # Mise à jour des piles
        self.histo_d.append(depth)
        del self.histo_d[0]

        self.histo_x.append(x)
        del self.histo_x[0]

        # Etendue des 20 derniers de l'histo des depth
        histo_depth_array = np.asarray(self.histo_d[-20:])
        etendue = np.max(histo_depth_array) - np.min(histo_depth_array)

        # Etendue = plage qui détermine si je bouge ou ne bouge pas en mode rapide
        if etendue > self.etendue:
            # Pas de blockage
            # self.depth_fixe sert pour le mode slow
            self.depth_fixe = self.get_frame_fast(depth)
            if self.block == 1:
                # Changement de phase
                self.block = 0
                # reset de la pile à la valeur actuelle
                self.histo_d = [depth]*self.d_lissage
        else:
            if self.block == 0:
                self.block = 1

        # Fonctionnement en mode slow
        if self.block == 1:
            x_liss = int(moving_average(np.array(self.histo_x),
                                        self.x_lissage-2,
                                        type_=self.x_mode))

            # Influence de x
            x_cor = int(x_liss  * self.x_coeff)

            # Combinaison depth et x et sens
            depth_and_x = self.depth_fixe + x_cor

            # Conversion en frame
            plage = self.profondeur_maxi - self.profondeur_mini
            frame = int(depth_and_x * self.lenght/plage)
            self.frame = frame

        # Fonctionnement en mode fast self.block = 0
        else:
            depth = int(moving_average(np.array(self.histo_d),
                                        self.d_lissage-2,
                                        type_=self.d_mode))
            plage = self.profondeur_maxi - self.profondeur_mini
            frame = int(depth * self.lenght/plage)
            self.frame = frame

    def get_frame_fast(self, depth):
        """Calcule la frame avec la profondeur pour le mode rapide,
        définir self.frame suffit pour être appliqué,
        le retour sert en mode slow
        """

        # Pour le mode slow
        depth_liss = int(moving_average(np.array(self.histo_d),
                                        self.d_lissage-2,
                                        type_=self.d_mode))

        # Conversion de la profondeur en frame
        plage = self.profondeur_maxi - self.profondeur_mini
        frame = int(depth_liss * self.lenght / plage)
        self.frame = frame

        # retour pour mode avec x
        return depth_liss

    def set_window(self):
        if self.full_screen:
            cv2.setWindowProperty(  'histopocene',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(  'histopocene',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_NORMAL)

    def draw_text(self, img, frame):
        if self.info:

            d = {   "Frame": frame,
                    "Profondeur mini": self.profondeur_mini,
                    "Profondeur maxi": self.profondeur_maxi,
                    "X maxi": self.x_maxi,
                    "D mode": self.d_mode,
                    "D lissage": self.d_lissage,
                    "X coeff": self.x_coeff,
                    "Etendue": self.etendue,
                    "X mode": self.x_mode,
                    "X lissage": self.x_lissage}
            i = 0
            for key, val in d.items():
                text = key + " : " + str(val)
                cv2.putText(img,  # image
                            text,
                            (30, 100*i+100),  # position
                            cv2.FONT_HERSHEY_SIMPLEX,  # police
                            2,  # taille police
                            (0, 255, 0),  # couleur
                            6)  # épaisseur
                i += 1

        return img

    def run(self):
        """Boucle infinie du script"""

        while self.loop:
            # Inversion de la video
            frame = self.lenght - self.frame
            # Pour ne jamais planté
            if frame < 1:
                frame = 1
            if frame > self.lenght:
                frame = self.lenght

            self.video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ret, img = self.video.read()

            if ret:
                img = self.draw_text(img, frame)
                cv2.imshow('histopocene', img)

            k = cv2.waitKey(self.tempo)
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

        self.video.release()
        cv2.destroyAllWindows()



def get_a_b(x_min, x_max, y_min, y_max):
    a = (y_min - y_max) / (x_min - x_max)
    b = y_min - (a * x_min)
    return a, b


def grande_echelle_run(conn, current_dir, config):

    ge = GrandeEchelle(conn, current_dir, config)
    ge.run()



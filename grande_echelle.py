

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

        # 0 = simple, 1 = 'exponentiel'
        if self.config['histopocene']['d_mode'] == 'simple': self.d_mode = 0
        else: self.d_mode = 1
        if self.config['histopocene']['x_mode'] == 'simple': self.x_mode = 0
        else: self.x_mode = 1

        self.d_lissage = int(self.config['histopocene']['d_lissage'])
        self.profondeur_mini = int(self.config['histopocene']['profondeur_mini'])
        self.profondeur_maxi = int(self.config['histopocene']['profondeur_maxi'])
        self.x_coeff = float(self.config['histopocene']['x_coeff'])
        self.etendue = int(self.config['histopocene']['etendue'])
        self.with_x = int(self.config['histopocene']['with_x'])
        self.x_lissage = int(self.config['histopocene']['x_lissage'])

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
                    if depth <= 0:
                        depth = 0
                    if depth > self.profondeur_maxi - self.profondeur_mini:
                        depth = self.profondeur_maxi

                    # En mm, entre -2000 et 2000
                    x = data[1]
                    if not self.with_x:
                        # Méthode moyenne glissante sur 800 cm
                        self.get_frame_fast(depth)
                    else:
                        # Utilisation de la surface de beaucoup de cm2
                        self.get_frame_slow(depth, x)

            elif data[0] == 'info':
                self.info = data[1]
                print("info reçu:", self.info)

            elif data[0] == 'with_x':
                self.with_x = data[1]
                print("with_x reçu:", self.with_x)

            elif data[0] == 'profondeur_mini':
                self.profondeur_mini = data[1]
                print("profondeur_mini reçu:", self.profondeur_mini)

            elif data[0] == 'profondeur_maxi':
                self.profondeur_maxi = data[1]
                print("profondeur_maxi reçu:", self.profondeur_maxi)

            elif data[0] == 'x_maxi':
                self.x_maxi = data[1]
                print("x_maxi reçu:", self.x_maxi)

            elif data[0] == 'd_mode':
                self.d_mode = data[1]
                print("d_mode reçu:", self.d_mode)

            elif data[0] == 'x_mode':
                self.x_mode = data[1]
                print(" reçu:", self.x_mode)

            elif data[0] == 'd_lissage':
                self.d_lissage = data[1]
                self.histo_d = [0]*self.d_lissage
                print("d_lissage reçu:", self.d_lissage)

            elif data[0] == 'x_coeff':
                self.x_coeff = data[1]
                print("x_coeff reçu:", self.x_coeff)

            elif data[0] == 'etendue':
                self.etendue = data[1]
                print("etendue reçu:", self.etendue)

            elif data[0] == 'x_lissage':
                self.x_lissage = data[1]
                self.histo_x = [0]*self.x_lissage
                print("x_lissage reçu:", self.x_lissage)

            elif data[0] == 'quit':
                self.loop = 0
                self.conn_loop = 0
                os._exit(0)

            sleep(0.001)

    def get_frame_slow(self, depth, x):
        """
                            if x < -2000:
                        x = -2000
                    if x > 2000:
                        x = 2000
        """
        # Mise à jour des piles
        self.histo_d.append(depth)
        del self.histo_d[0]

        self.histo_x.append(x)
        del self.histo_x[0]

        # Etendue des 20 derniers de l'histo des depth
        histo_depth_array = np.asarray(self.histo_d)  # [-60:])
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
        # Maj de la pile des profondeurs
        self.histo_d.append(depth)
        del self.histo_d[0]

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
            l = [frame, self.with_x, self.profondeur_mini,
                self.profondeur_maxi, self.d_mode, self.x_mode,
                self.d_lissage, self.x_coeff, self.etendue, self.x_lissage]
            text = ""
            for t in l:
                text += str(t) + " "
            cv2.putText(img,  # image
                        text,
                        (30, 1000),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        2,  # taille police
                        (0, 255, 0),  # couleur
                        6)  # épaisseur
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


if __name__ == '__main__':
    conn = None
    current_dir = '/media/data/3D/projets/grande_echelle'

    ini_file = current_dir + '/grande_echelle.ini'
    config = MyConfig(ini_file).conf

    ge = grande_echelle_run(conn, current_dir, config)

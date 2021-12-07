
# Echap pour finir proprement le script
# Espace pour bascule, plein écran / normal


import os
from time import time, sleep
from threading import Thread

import cv2
import numpy as np

from pynput.mouse import Button, Controller

from filtre import moving_average
from my_config import MyConfig


global GE_LOOP
GE_LOOP = 1



class GrandeEchelleViewer:
    """Affichage dans une fenêtre OpenCV, et gestion des fenêtres"""
    global GE_LOOP

    def __init__(self, conn, config):

        self.conn = conn
        self.config = config

        freq = int(self.config['histopocene']['frame_rate_du_film'])
        if freq != 0:
            self.tempo = int(1000/freq)
        else:
            print("Le frame rate du film est à 0 !")
            os._exit(0)

        self.info = int(self.config['histopocene']['info'])
        self.mode_expo = int(self.config['histopocene']['mode_expo'])
        self.full_screen = int(self.config['histopocene']['full_screen'])
        if self.mode_expo:
            self.info = 0
            self.full_screen = 1
        self.create_window()
        self.mouse = Controller()

    def create_window(self):
        cv2.namedWindow('histopocene', cv2.WND_PROP_FULLSCREEN)

    def set_window(self):
        """ from pynput.mouse import Button, Controller
            mouse = Controller()
            mouse.position = (50,60)
        """
        if self.full_screen:
            cv2.setWindowProperty(  'histopocene',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_FULLSCREEN)
            x, y, w, h = cv2.getWindowImageRect('histopocene')
            self.mouse.position = (w, h)
        else:
            cv2.setWindowProperty(  'histopocene',
                                    cv2.WND_PROP_FULLSCREEN,
                                    cv2.WINDOW_NORMAL)

    def run(self):
        """Boucle infinie du script"""
        global GE_LOOP

        while GE_LOOP:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.frame)
            ret, img = self.video.read()

            if self.mode_expo:
                self.info = 0
                self.full_screen = 1
                self.set_window()

            if ret:
                if self.info:
                    img = self.draw_text(img, self.frame)
                cv2.imshow('histopocene', img)

            k = cv2.waitKey(self.tempo)
            # Space pour full screen or not
            if k == 32:  # space
                if not self.mode_expo:
                    if self.full_screen == 1:
                        self.full_screen = 0
                    elif self.full_screen == 0:
                        self.full_screen = 1
                    self.set_window()
            # Esc to  exit
            if k == 27:
                self.conn.send(['quit', 1])
                print("Quit envoyé de Grande Echelle")
                GE_LOOP = 0

        self.video.release()
        cv2.destroyAllWindows()



class GrandeEchelle(GrandeEchelleViewer):
    """Affichage d'une frame spécique du film,
    en fonction de la réception de la profondeur
    avec conn de multiprocess.
    """
    global GE_LOOP

    def __init__(self, conn, current_dir, config):

        self.conn = conn
        self.config = config

        # Fenêtres OpenCV
        GrandeEchelleViewer.__init__(self, conn, config)

        self.ge_conn_loop = 1
        self.frame = 0

        if self.conn:
            self.receive_thread()

        film = str(current_dir) + "/" + self.config['histopocene']['film']
        print("Le film est:", film)
        self.video = cv2.VideoCapture(film)
        self.lenght = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        print("Longueur du film :", self.lenght)  # 38400

        self.profondeur_mini = int(self.config['histopocene']['profondeur_mini'])
        self.profondeur_maxi = int(self.config['histopocene']['profondeur_maxi'])
        self.largeur_maxi = int(self.config['histopocene']['largeur_maxi'])
        self.pile_size = int(self.config['histopocene']['pile_size'])
        self.lissage = int(self.config['histopocene']['lissage'])

        # Image fixe si pas de capture a la fin du film
        self.frame = 0
        self.depth = 1
        self.histo = [self.profondeur_mini + 1000]*self.pile_size
        # Stockage des 8 dernières valeurs de frame
        self.slow_size = int(self.config['histopocene']['slow_size'])
        self.histo_slow = [0]*self.slow_size

    def receive_thread(self):
        t = Thread(target=self.receive)
        t.start()

    def receive(self):
        global GE_LOOP

        while self.ge_conn_loop:
            if self.conn.poll():
                data = self.conn.recv()
                if data[0] == 'depth':
                    if data[1]:
                        self.get_frame(data[1])

                elif data[0] == 'info':
                    self.info = data[1]
                    print("info reçu dans grande echelle:", self.info)

                elif data[0] == 'profondeur_mini':
                    self.profondeur_mini = data[1]
                    print("profondeur_mini reçu dans grande echelle:", self.profondeur_mini)

                elif data[0] == 'profondeur_maxi':
                    self.profondeur_maxi = data[1]
                    print("profondeur_maxi reçu dans grande echelle:", self.profondeur_maxi)

                elif data[0] == 'largeur_maxi':
                    self.largeur_maxi = data[1]
                    print("largeur_maxi reçu dans grande echelle:", self.largeur_maxi)

                elif data[0] == 'mode_expo':
                    self.mode_expo = data[1]
                    print("info reçu dans grande echelle:", self.mode_expo)
                    if self.mode_expo:
                        self.info = 0

                elif data[0] == 'pile_size':
                    self.pile_size = data[1]
                    print("pile_size reçu dans grande echelle:", self.pile_size)

                elif data[0] == 'lissage':
                    self.lissage = data[1]
                    print("lissage reçu dans grande echelle:", self.lissage)

                elif data[0] == 'quit':
                    print("Alerte: Quit reçu dans Grande Echelle")
                    GE_LOOP = 0
                    self.ge_conn_loop = 0
                    os._exit(0)

            sleep(0.001)

    def get_frame(self, depth):
        """ Appelé à chaque réception de depth dans receive 'depth',
        longueur en mm
        160 frame pour 12 000 ans
        39750 frame pour 300 cm
        1 cm pour 132 frames
        """
        # Mise à jour de la pile
        self.histo.append(depth)
        del self.histo[0]

        try:
            depth = int(moving_average( np.array(self.histo),
                                        self.lissage,
                                        type_='simple')[0])
        except:
            print("Erreur moving_average depth")

        # Pour bien comprendre
        mini = self.profondeur_mini + 100  # frame 0 si mini
        maxi = self.profondeur_maxi - 300  # frame lenght si maxi
        lenght = self.lenght

        # Voir le dessin
        # (x1, y1, x2, y2) = (mini, 0, maxi, lenght)
        a, b = get_a_b(mini, lenght, maxi, 0)
        frame = int(a*depth + b)

        # Pour ne jamais planté
        if frame < 0:
            frame = 0
        if frame >= lenght:
            frame = lenght - 1

        # Pile des 8 dernières valeurs lissées
        self.histo_slow.append(frame)
        del self.histo_slow[0]
        try:
            frame = int(moving_average( np.array(self.histo_slow),
                                        self.slow_size - 1,
                                        type_='simple')[0])
        except:
            print("Erreur moving_average depth")

        self.frame = frame

    def draw_text(self, img, frame):
        d = {   "Frame du Film": frame,
                "Profondeur mini": self.profondeur_mini,
                "Profondeur maxi": self.profondeur_maxi,
                "X maxi": self.largeur_maxi,
                "Taille pile": self.pile_size,
                "Lissage": self.lissage}
        i = 0
        for key, val in d.items():
            text = key + " : " + str(val)
            cv2.putText(img,  # image
                        text,
                        (30, 150*i+200),  # position
                        cv2.FONT_HERSHEY_SIMPLEX,  # police
                        2,  # taille police
                        (0, 255, 0),  # couleur
                        6)  # épaisseur
            i += 1

        return img



def get_a_b(x1, y1, x2, y2):
    a = (y1 - y2)/(x1 - x2)
    b = y1 - a*x1
    return a, b


def grande_echelle_run(conn, current_dir, config):

    ge = GrandeEchelle(conn, current_dir, config)
    # run est dans Viewer
    ge.run()

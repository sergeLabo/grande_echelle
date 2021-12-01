
#  160 frame pour 12 000 ans

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


class GrandeEchelleViewer:
    """Affichage dans une fenêtre OpenCV, et gestion des fenêtres"""

    def __init__(self, conn, config):

        self.conn = conn
        self.config = config
        self.loop = 1

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

        while self.loop:
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
                print("Quit dans Grande Echelle")
                self.loop = 0
                # # self.conn_loop = 0

        self.video.release()
        cv2.destroyAllWindows()



class GrandeEchelle(GrandeEchelleViewer):
    """Affichage d'une frame spécique du film,
    en fonction de la réception de la profondeur
    avec conn de multiprocess.
    """

    def __init__(self, conn, current_dir, config):

        self.conn = conn
        self.config = config

        # Fenêtres OpenCV
        GrandeEchelleViewer.__init__(self, conn, config)

        self.conn_loop = 1
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
        while self.conn_loop:
            if self.conn.poll():
                data = self.conn.recv()

                if data[0] == 'quit':  # il doit être en premier
                    self.loop = 0
                    self.conn_loop = 0
                    os._exit(0)

                if data[0] == 'depth':
                    # # print("depth reçu dans grande échelle", data[1])
                    if data[1]:
                        self.get_frame(data[1])

                if data[0] == 'info':
                    self.info = data[1]
                    print("info reçu dans grande echelle:", self.info)

                if data[0] == 'profondeur_mini':
                    self.profondeur_mini = data[1]
                    print("profondeur_mini reçu dans grande echelle:", self.profondeur_mini)

                if data[0] == 'profondeur_maxi':
                    self.profondeur_maxi = data[1]
                    print("profondeur_maxi reçu dans grande echelle:", self.profondeur_maxi)

                if data[0] == 'largeur_maxi':
                    self.largeur_maxi = data[1]
                    print("largeur_maxi reçu dans grande echelle:", self.largeur_maxi)

                if data[0] == 'mode_expo':
                    self.mode_expo = data[1]
                    print("info reçu dans grande echelle:", self.mode_expo)
                    if self.mode_expo:
                        self.info = 0

                if data[0] == 'pile_size':
                    self.pile_size = data[1]
                    print("pile_size reçu dans grande echelle:", self.pile_size)

                if data[0] == 'lissage':
                    self.lissage = data[1]
                    print("lissage reçu dans grande echelle:", self.lissage)

                if data[0] == 'slow_size':
                    self.slow_size = data[1]
                    print("slow_size reçu dans grande echelle:", self.slow_size)

            sleep(0.001)

    def get_frame(self, depth):
        """ Appelé à chaque réception de depth dans receive 'depth',
        longueur en mm
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
        mini = self.profondeur_mini + 100
        maxi = self.profondeur_maxi - 300
        lenght = self.lenght

        # Voir le dessin
        a, b = get_a_b(mini, 0, maxi, lenght)
        frame = int(a*depth + b)

        # Inversion de la video
        frame = self.lenght - frame
        # Pour ne jamais planté
        if frame < 0:
            frame = 0
        if frame >= self.lenght:
            frame = self.lenght - 1


        print(frame)
        # Pile des 8 dernières valeurs lissées
        self.histo_slow.append(frame)
        del self.histo_slow[0]
        try:
            frame = int(moving_average( np.array(self.histo_slow),
                                        self.slow_size - 1,
                                        type_='simple')[0])
        except:
            print("Erreur moving_average depth")
        print(frame, self.histo_slow)
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


        # # # Ma boucle PID
        # # delta = int(frame - self.frame)
        # # a, b = get_a_b(10, 10, 100, 20)
        # # delta_new = int(a*(delta) + b)
        # # frame_new = frame + delta_new
        # # print(delta, delta_new, frame, frame_new)
        # Pour ne jamais planté
        # # if frame_new < 0:
            # # frame_new = 0
        # # if frame_new >= self.lenght:
            # # frame_new = self.lenght - 1
        # # self.frame = frame_new

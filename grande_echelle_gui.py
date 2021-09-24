
"""
Interface graphique pour Grande Echelle
"""

import os
from time import sleep
from pathlib import Path
from multiprocessing import Process, Pipe
from threading import Thread

import kivy
kivy.require('2.0.0')

from kivy.core.window import Window
k = 1.4
WS = (int(640*k), int(640*k))
Window.size = WS


from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, BooleanProperty

from posenet_realsense import posenet_realsense_run
from grande_echelle import grande_echelle_run



class MainScreen(Screen):
    """Ecran principal, l'appli s'ouvre sur cet écran
    root est le parent de cette classe dans la section <MainScreen> du kv
    """

    # Attribut de class, obligatoire pour appeler root.titre dans kv
    titre = StringProperty("toto")
    enable = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trop fort
        self.app = App.get_running_app()

        # Pour envoyer les valeurs au child_conn
        # [pose]
        self.threshold = 0.5
        self.around = 1

        # [histopocene]
        self.with_x = 1
        self.profondeur_mini = 1500
        self.profondeur_maxi = 4000
        self.d_mode = 0
        self.x_mode = 0
        self.d_lissage = 44
        self.x_coeff = 0.19
        self.etendue = 200
        self.x_lissage = 27

        # Pour le Pipe
        self.p1_conn = None
        self.p2_conn = None
        self.receive_loop = 1

        # Pour ne lancer qu'une fois les processus
        self.enable = False

        self.titre = "Grande Echelle"

        print("Initialisation du Screen MainScreen ok")

    def receive_thread(self):
        t = Thread(target=self.receive)
        t.start()

    def receive(self):
        while self.receive_loop:
            sleep(0.001)
            # De posenet realsense
            data1 = self.p1_conn.recv()

            # Relais des depth et x
            if data1[0] == 'from_realsense':
                self.p2_conn.send(['depth_x', data1[1], data1[2]])
            if data1[0] == 'quit':
                try:
                    self.app.do_quit()
                except:
                    pass

            # De grande echelle
            data2 = self.p2_conn.recv()
            if data2[0] == 'quit':
                try:
                    self.app.do_quit()
                except:
                    pass

    def run_grande_echelle(self):
        if not self.enable:
            print("Lancement de 2 processus:")

            current_dir = str(Path(__file__).parent.absolute())
            print("Dossier courrant:", current_dir)

            # Posenet et Realsense
            self.p1_conn, child_conn1 = Pipe()
            p1 = Process(target=posenet_realsense_run, args=(child_conn1,
                                                             current_dir,
                                                             self.app.config,  ))
            p1.start()
            print("Posenet Realsense lancé ...")

            # Grande Echelle
            self.p2_conn, child_conn2 = Pipe()
            p2 = Process(target=grande_echelle_run, args=(child_conn2,
                                                          current_dir,
                                                          self.app.config, ))
            p2.start()
            print("Histopocene lancé ...")

            self.enable = True
            self.receive_thread()
            print("Ca tourne ...")



class Reglage(Screen):
    """
    Sliders:
            threshold = 53.0
            around = 1
            d_lissage = 44
            x_coeff = 0.19
            etendue = 200
            x_lissage = 27

    Switch:
            d_mode = 0 = 'simple'
            x_mode = 0 = 'simple'
            with_x = 1
            info = 0
    Options:
            frame_rate_du_film = 14
            film = 'ge_1920_14_moy.mp4'
    """

    brightness = NumericProperty(0)
    contrast = NumericProperty(0)
    threshold = NumericProperty(0.8)
    profondeur_mini = NumericProperty(1500)
    profondeur_maxi = NumericProperty(4000)
    x_maxi = NumericProperty(1500)
    d_lissage = NumericProperty(50)
    x_coeff = NumericProperty(0.20)
    etendue = NumericProperty(200)
    x_lissage = NumericProperty(25)
    d_mode = NumericProperty(0)
    x_mode = NumericProperty(0)
    with_x = NumericProperty(1)
    info = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("Initialisation du Screen Settings")

        self.app = App.get_running_app()
        self.brightness = float(self.app.config.get('pose', 'brightness'))
        self.contrast = float(self.app.config.get('pose', 'contrast'))
        self.threshold = float(self.app.config.get('pose', 'threshold'))
        self.around = int(self.app.config.get('pose', 'around'))

        if self.app.config.get('histopocene', 'd_mode') == 'simple':
            self.d_mode = 0
        else:
            self.d_mode = 1
        if self.app.config.get('histopocene', 'x_mode') == 'simple':
            self.x_mode = 0
        else:
            self.x_mode = 1

        self.with_x = int(self.app.config.get('histopocene', 'with_x'))
        self.profondeur_mini = int(self.app.config.get('histopocene', 'profondeur_mini'))
        self.profondeur_maxi = int(self.app.config.get('histopocene', 'profondeur_maxi'))
        self.x_maxi = int(self.app.config.get('histopocene', 'x_maxi'))
        self.d_lissage = int(self.app.config.get('histopocene', 'd_lissage'))
        self.x_coeff = float(self.app.config.get('histopocene', 'x_coeff'))
        self.etendue = int(self.app.config.get('histopocene', 'etendue'))
        self.x_lissage = int(self.app.config.get('histopocene', 'x_lissage'))
        self.info = int(self.app.config.get('histopocene', 'info'))

    def do_slider(self, iD, instance, value):

        scr = self.app.screen_manager.get_screen('Main')

        if iD == 'brightness':
            self.brightness = round(value, 2)

            self.app.config.set('pose', 'brightness', self.brightness)
            self.app.config.write()

            if scr.p1_conn:
                scr.p1_conn.send(['brightness', self.brightness])

        if iD == 'contrast':
            self.contrast = round(value, 2)

            self.app.config.set('pose', 'contrast', self.contrast)
            self.app.config.write()

            if scr.p1_conn:
                scr.p1_conn.send(['contrast', self.contrast])

        if iD == 'threshold':
            # Maj de l'attribut
            self.threshold = round(value, 2)
            # Maj de la config
            self.app.config.set('pose', 'threshold', self.threshold)
            # Sauvegarde dans le *.ini
            self.app.config.write()

            # Envoi de la valeur au process enfant
            if scr.p1_conn:
                scr.p1_conn.send(['threshold', self.threshold])

        if iD == 'profondeur_mini':
            self.profondeur_mini = int(value)

            self.app.config.set('histopocene', 'profondeur_mini', self.profondeur_mini)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['profondeur_mini', self.profondeur_mini])

        if iD == 'profondeur_maxi':
            self.profondeur_maxi = int(value)

            self.app.config.set('histopocene', 'profondeur_maxi', self.profondeur_maxi)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['profondeur_maxi', self.profondeur_maxi])

        if iD == 'x_maxi':
            self.x_maxi = int(value)

            self.app.config.set('histopocene', 'x_maxi', self.x_maxi)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['x_maxi', self.x_maxi])

        if iD == 'd_lissage':
            self.d_lissage = int(value)

            self.app.config.set('histopocene', 'd_lissage', self.d_lissage)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['d_lissage', self.d_lissage])

        if iD == 'x_coeff':
            self.x_coeff = round(value, 2)

            self.app.config.set('histopocene', 'x_coeff', self.x_coeff)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['x_coeff', self.x_coeff])

        if iD == 'etendue':
            self.etendue = int(value)

            self.app.config.set('histopocene', 'etendue', self.etendue)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['etendue', self.etendue])

        if iD == 'x_lissage':
            self.x_lissage = int(value)

            self.app.config.set('histopocene', 'x_lissage', self.x_lissage)
            self.app.config.write()

            if scr.p2_conn:
                scr.p2_conn.send(['x_lissage', self.x_lissage])

    def on_switch_d_mode(self, instance, value):

        scr = self.app.screen_manager.get_screen('Main')

        if value:
            value = 1
            d_mode = 'exponentiel'
        else:
            value = 0
            d_mode = 'simple'
        self.d_mode = value
        if scr.p2_conn:
            scr.p2_conn.send(['d_mode', self.d_mode])
        self.app.config.set('histopocene', 'd_mode', d_mode)
        self.app.config.write()
        print("d_mode =", self.d_mode, d_mode)

    def on_switch_x_mode(self, instance, value):
        scr = self.app.screen_manager.get_screen('Main')
        if value:
            value = 1
            x_mode = 'exponentiel'
        else:
            value = 0
            x_mode = 'simple'
        self.x_mode = value
        if scr.p2_conn:
            scr.p2_conn.send(['x_mode', self.x_mode])
        self.app.config.set('histopocene', 'x_mode', x_mode)
        self.app.config.write()
        print("x_mode =", self.x_mode, x_mode)

    def on_switch_with_x(self, instance, value):
        scr = self.app.screen_manager.get_screen('Main')
        if value:
            value = 1
        else:
            value = 0
        self.with_x = value
        if scr.p2_conn:
            scr.p2_conn.send(['with_x', self.with_x])
        self.app.config.set('histopocene', 'with_x', self.with_x)
        self.app.config.write()
        print("with_x =", self.with_x)

    def on_switch_info(self, instance, value):
        scr = self.app.screen_manager.get_screen('Main')
        if value:
            value = 1
        else:
            value = 0
        self.info = value
        if scr.p2_conn:
            scr.p2_conn.send(['info', self.info])
        self.app.config.set('histopocene', 'info', self.info)
        self.app.config.write()
        print("info =", self.info)



# Variable globale qui définit les écrans
# L'écran de configuration est toujours créé par défaut
# Il suffit de créer un bouton d'accès
# Les class appelées (MainScreen, ...) sont placées avant
SCREENS = { 0: (MainScreen, 'Main'),
            1: (Reglage, 'Reglage')}


class Grande_EchelleApp(App):
    """Construction de l'application. Exécuté par if __name__ == '__main__':,
    app est le parent de cette classe dans kv
    """

    def build(self):
        """Exécuté après build_config, construit les écrans"""

        # Création des écrans
        self.screen_manager = ScreenManager()
        for i in range(len(SCREENS)):
            # Pour chaque écran, équivaut à
            # self.screen_manager.add_widget(MainScreen(name="Main"))
            self.screen_manager.add_widget(SCREENS[i][0](name=SCREENS[i][1]))

        return self.screen_manager

    def build_config(self, config):
        """Excécuté en premier (ou après __init__()).
        Si le fichier *.ini n'existe pas,
                il est créé avec ces valeurs par défaut.
        Il s'appelle comme le kv mais en ini
        Si il manque seulement des lignes, il ne fait rien !
        """

        print("Création du fichier *.ini si il n'existe pas")

        config.setdefaults( 'camera',
                                        {   'width_input': 1280,
                                            'height_input': 720})

        config.setdefaults( 'pose',
                                        {   'brightness': 0,
                                            'contrast': 0,
                                            'threshold': 0.80,
                                            'around': 1 })

        config.setdefaults( 'histopocene',
                                        {   'with_x': 1,
                                            'frame_rate_du_film': 14,
                                            'film': 'ge_1920_14_moy.mp4',
                                            'profondeur_mini': 1500,
                                            'profondeur_maxi': 4000,
                                            'x_maxi': 1500,
                                            'd_mode': 'simple',
                                            'x_mode': 'simple',
                                            'd_lissage': 50,
                                            'x_coeff': 0.20,
                                            'etendue': 200,
                                            'x_lissage': 25,
                                            'info': 0})

        print("self.config peut maintenant être appelé")

    def build_settings(self, settings):
        """Construit l'interface de l'écran Options, pour Grande_Echelle seul,
        Les réglages Kivy sont par défaut.
        Cette méthode est appelée par app.open_settings() dans .kv,
        donc si Options est cliqué !
        """

        print("Construction de l'écran Options")

        data = """[
                    {"type": "title", "title": "Camera RealSense"},

                        {   "type": "numeric",
                            "title": "Largeur de l'image caméra",
                            "desc": "1280 ou 640",
                            "section": "camera", "key": "width_input"},

                        {   "type": "numeric",
                            "title": "Hauteur de l'image caméra",
                            "desc": "720 ouy 480",
                            "section": "camera", "key": "height_input"},

                    {"type": "title", "title": "Détection des squelettes"},
                        {   "type": "numeric",
                            "title": "Seuil de confiance pour la detection d'un keypoint",
                            "desc": "0.01 à 0.99",
                            "section": "pose", "key": "threshold"},
                        {   "type": "numeric",
                            "title": "Nombre de pixels autour du point pour le calcul de la profondeur",
                            "desc": "Entier de 1 à 5",
                            "section": "pose", "key": "around"},

                    {"type": "title", "title": "Histopocene"},

                        {   "type": "numeric",
                            "title": "Détection avec les x",
                            "desc": "0 ou 1",
                            "section": "histopocene", "key": "with_x"},

                        {   "type": "string",
                            "title": "Nom du film",
                            "desc": "Nom du fichier du fiml avecextension, sans chemin",
                            "section": "histopocene", "key": "film"},

                        {   "type": "numeric",
                            "title": "Frame Rate du film",
                            "desc": "1 à 30",
                            "section": "histopocene", "key": "frame_rate_du_film"},

                        {   "type": "numeric",
                            "title": "Profondeur de détection mini",
                            "desc": "De 500 à 2000",
                            "section": "histopocene", "key": "profondeur_mini"},

                        {   "type": "numeric",
                            "title": "Profondeur de détection maxi",
                            "desc": "De 3000 à 8000",
                            "section": "histopocene", "key": "profondeur_maxi"},

                        {   "type": "numeric",
                            "title": "X maxi par rapport à l'axe",
                            "desc": "De 100 à 2000",
                            "section": "histopocene", "key": "x_maxi"},

                        {   "type": "string",
                            "title": "Mode de Lissage de la profondeur",
                            "desc": "Simple ou exponentiel",
                            "section": "histopocene", "key": "d_mode"},

                        {   "type": "string",
                            "title": "Mode de Lissage des x",
                            "desc": "Simple ou exponentiel",
                            "section": "histopocene", "key": "x_mode"},

                        {   "type": "numeric",
                            "title": "Coefficient de lissage de la profondeur",
                            "desc": "De 10 à 120",
                            "section": "histopocene", "key": "d_lissage"},

                        {   "type": "numeric",
                            "title": "Etendue de la variation de la profondeur en mode rapide",
                            "desc": "De 100 à 500",
                            "section": "histopocene", "key": "etendue"},

                        {   "type": "numeric",
                            "title": "Influence de la valeur des x",
                            "desc": "De 0.1 à 1",
                            "section": "histopocene", "key": "x_coeff"},

                        {   "type": "numeric",
                            "title": "Coefficient de lissage des x ",
                            "desc": "De 10 à 120",
                            "section": "histopocene", "key": "x_lissage"}

                        {   "type": "numeric",
                            "title": "Affichage du numéro de frame dans histopocene",
                            "desc": "0 ou 1",
                            "section": "histopocene", "key": "info"}
                   ]"""

        # self.config est le config de build_config
        settings.add_json_panel('Grande_Echelle', self.config, data=data)

    def on_config_change(self, config, section, key, value):
        """Si modification des options, fonction appelée automatiquement
        menu = self.screen_manager.get_screen("Main")
        Seul les rébglages à chaud sont définis ici !
        """

        if config is self.config:
            token = (section, key)

            if token == ('pose', 'threshold'):
                if value < 0: value = 0
                if value > 0.99: value = 0.99
                self.threshold = value
                self.config.set('pose', 'threshold', self.threshold)

            if token == ('pose', 'around'):
                if value < 1: value = 1
                if value > 5: value = 5
                self.around = value
                self.config.set('pose', 'around', self.around)

            if token == ('histopocene', 'with_x'):
                if value in [0, 1]:
                    self.with_x = value
                    self.config.set('histopocene', 'with_x', self.with_x)

            if token == ('histopocene', 'profondeur_mini'):
                if value < 500: value = 500
                if value > 2000: value = 2000
                self.profondeur_mini = value
                self.config.set('histopocene', 'profondeur_mini', self.profondeur_mini)

            if token == ('histopocene', 'profondeur_maxi'):
                if value < 3000: value = 3000
                if value > 8000: value = 8000
                self.profondeur_maxi = value
                self.config.set('histopocene', 'profondeur_maxi', self.profondeur_maxi)

            if token == ('histopocene', 'x_maxi'):
                if value < 3000: value = 3000
                if value > 8000: value = 8000
                self.x_maxi = value
                self.config.set('histopocene', 'x_maxi', self.x_maxi)

            if token == ('histopocene', 'd_mode'):
                # value = simple ou exponentiel
                if value != 'simple':
                    self.d_mode = 0
                else:
                    self.d_mode = 1
                self.config.set('histopocene', 'd_mode', value)

            if token == ('histopocene', 'x_mode'):
                # value = simple ou exponentiel
                if value != 'simple':
                    self.x_mode = 0
                else:
                    self.x_mode = 1
                self.config.set('histopocene', 'x_mode', value)

            if token == ('histopocene', 'd_lissage'):
                if value < 10: value = 10
                if value > 120: value = 120
                self.d_lissage = int(value)
                self.config.set('histopocene', 'd_lissage', self.d_lissage)

            if token == ('histopocene', 'x_lissage'):
                if value < 10: value = 10
                if value > 120: value = 120
                self.x_lissage = int(value)
                self.config.set('histopocene', 'x_lissage', self.x_lissage)

            if token == ('histopocene', 'x_coeff'):
                if value < 0.1: value = 0.1
                if value > 1: value = 1
                self.x_coeff = value
                self.config.set('histopocene', 'x_coeff', self.x_coeff)

            if token == ('histopocene', 'etendue'):
                if value < 100: value = 100
                if value > 500: value = 500
                self.etendue = int(value)
                self.config.set('histopocene', 'etendue', self.etendue)

            if token == ('histopocene', 'info'):
                if value in [0, 1]:
                    self.info = value
                    self.config.set('histopocene', 'info', self.info)

    def go_mainscreen(self):
        """Retour au menu principal depuis les autres écrans."""
        self.screen_manager.current = ("Main")

    def do_quit(self):
        print("Je quitte proprement")

        # Fin du processus fils
        scr = self.screen_manager.get_screen('Main')
        if scr.p1_conn:
            scr.p1_conn.send(['quit'])
        if scr.p2_conn:
            scr.p2_conn.send(['quit'])

        # Fin du thread
        scr.receive_loop = 0

        # Kivy
        Grande_EchelleApp.get_running_app().stop()

        # Extinction forcée de tout, si besoin
        os._exit(0)



if __name__ == '__main__':
    """L'application s'appelle Grande_Echelle
    d'où
    la class
        Grande_EchelleApp()
    les fichiers:
        grande_echelle.kv
        grande_echelle.ini
    """

    Grande_EchelleApp().run()

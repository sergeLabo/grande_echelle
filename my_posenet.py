
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


import os
import pathlib

from pose_engine import PoseEngine


class MyPosenet:
    """Initialisation du Coral et du model posenet"""

    def __init__(self, width, height):

        self.width = width
        self.height = height
        self.get_engine()

    def get_engine(self):
        """Crée le moteur de calcul avec le stick Coral"""

        res = str(self.width) + 'x' + str(self.height)
        print("width:", self.width, ", height:", self.height)
        print("Résolution =", res)

        if res == "1280x720":
            # #src_size = (1280, 720)
            # #appsink_size = (1280, 720)
            model_size = (721, 1281)
        elif res == "640x480":
            # #src_size = (640, 480)
            # #appsink_size = (640, 480)
            model_size = (481, 641)
        else:
            print(f"La résolution {res} n'est pas possible.")
            os._exit(0)

        current_dir = pathlib.Path(__file__).parent
        model = (f'{current_dir}'
                 f'/posenet/models/mobilenet/posenet_mobilenet_v1_075_'
                 f'{model_size[0]}_{model_size[1]}'
                 f'_quant_decoder_edgetpu.tflite'   )
        print('Loading model: ', model)
        self.engine = PoseEngine(model, mirror=False)
        # # try:
            # # self.engine = PoseEngine(model, mirror=False)
        # # except:
            # # print(f"Pas de Stick Coral connecté")
            # # os._exit(0)

    def get_outputs(self, color_arr):
        outputs, inference_time = self.engine.DetectPosesInImage(color_arr)
        return outputs


if __name__ == '__main__':

    MyPosenet(1280, 720)

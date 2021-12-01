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


"""
Un squelette 2D = xys:
    - liste de 17 items avec les coordonnées de chaque keypoints
    - xys_list = [(698, 320), (698, 297), None, ... ]
    - il y a toujours 17 items, si le point n'est pas détecté, la value est None
"""


import enum

class KeypointType(enum.IntEnum):
    """Pose kepoints."""
    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16


class MyPoseNetConversion:
    """Convertit les sorties Posenet dans un format (une liste)
    utilisable facilement
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
            if xys:
                self.skeletons.append(xys)

    def get_points_2D(self, pose):
        """ xys_dict = dict{index du keypoint: (x, y), }
        xys = {0: (698, 320), 1: (698, 297), 3: None, .... }
        puis convertit en liste
        xys_list = [(698, 320), (698, 297), None, ... ]
        avec toujours 17 items
        """
        xys = {}
        for label, keypoint in pose.keypoints.items():
            if keypoint.score > self.threshold:
                xys[label.value] = [int(keypoint.point[0]),
                                    int(keypoint.point[1])]

        return self.xys_dict_to_xys_list(xys)

    def xys_dict_to_xys_list(self, xys):
        """
        xys_dict = {0: (698, 320), 1: (698, 297), 2: (675, 295), .... }
        vers
        xys_list = [item0, ....] avec
        item0 = value de la key 0
        """
        xys_list = [None]*17

        for key_num, value in xys.items():
            xys_list[key_num] = value

        # Suppression des squelettes sans aucune articulation, possible lorsque
        # toutes les articulations sont en dessous du seuil de confiance
        if xys_list == [None]*17:
            xys_list = None

        return xys_list

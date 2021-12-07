## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2017 Intel Corporation. All Rights Reserved.

import os
import numpy as np

import pyrealsense2 as rs


class MyRealSense:
    """Initialise la caméra et permet d'accéder aux images"""

    def __init__(self, kwargs):

        self.config = kwargs
        self.width = int(self.config['camera']['width_input'])
        self.height = int(self.config['camera']['height_input'])
        self.set_pipeline()

    def set_pipeline(self):

        self.pipeline = rs.pipeline()
        config = rs.config()
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        try:
            pipeline_profile = config.resolve(pipeline_wrapper)
        except:
            print('\n\nPas de Capteur Realsense connecté\n\n')
            os._exit(0)

        device = pipeline_profile.get_device()
        config.enable_stream(   rs.stream.color,
                                width=self.width,
                                height=self.height,
                                format=rs.format.bgr8,
                                framerate=30)
        config.enable_stream(   rs.stream.depth,
                                width=self.width,
                                height=self.height,
                                format=rs.format.z16,
                                framerate=30)
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

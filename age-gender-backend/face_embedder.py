# face_embedder.py

import os
import cv2
import numpy as np
import onnxruntime as ort


class FaceEmbedder:

    def __init__(self):

        model_path = os.path.expanduser(
            "~/.insightface/models/buffalo_l/w600k_r50.onnx"
        )

        if not os.path.exists(model_path):
            raise RuntimeError(f"Embedding model not found: {model_path}")

        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )

        self.input_name = self.session.get_inputs()[0].name

    def preprocess(self, face_rgb):

        face = cv2.resize(face_rgb, (112, 112))
        face = face.astype(np.float32)

        face = (face - 127.5) / 127.5
        face = np.transpose(face, (2, 0, 1))
        face = np.expand_dims(face, axis=0)

        return face

    def align_face(self, face_rgb, landmarks):

        left_eye = landmarks["left_eye"]
        right_eye = landmarks["right_eye"]

        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]

        angle = np.degrees(np.arctan2(dy, dx))

        center = (
            float((left_eye[0] + right_eye[0]) / 2),
            float((left_eye[1] + right_eye[1]) / 2)
        )

        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        aligned = cv2.warpAffine(
            face_rgb,
            rot_matrix,
            (face_rgb.shape[1], face_rgb.shape[0]),
            flags=cv2.INTER_LINEAR
        )

        return aligned
    
    def get_embedding(self, face_rgb):

        input_blob = self.preprocess(face_rgb)

        embedding = self.session.run(
            None,
            {self.input_name: input_blob}
        )[0][0]

        embedding = embedding.astype(np.float32)
        embedding /= np.linalg.norm(embedding)

        return embedding

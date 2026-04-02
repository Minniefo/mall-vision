import tensorflow as tf
from tensorflow.keras.layers import (
    Input, Conv2D, BatchNormalization, ReLU, Add, GlobalAveragePooling2D,
    Dense, Dropout, Reshape, Multiply, MaxPooling2D, Lambda, Concatenate
)
from tensorflow.keras.models import Model
import tensorflow as tf


# ---------- RESIDUAL BLOCK ----------
def residual_block(x, filters):
    shortcut = x

    x = Conv2D(filters, 3, padding="same", use_bias=False)(x)
    x = BatchNormalization()(x)
    x = ReLU()(x)

    x = Conv2D(filters, 3, padding="same", use_bias=False)(x)
    x = BatchNormalization()(x)

    # Match dimensions
    if shortcut.shape[-1] != filters:
        shortcut = Conv2D(filters, 1, padding="same", use_bias=False)(shortcut)
        shortcut = BatchNormalization()(shortcut)

    x = Add()([shortcut, x])
    x = ReLU()(x)
    return x


# ---------- SE BLOCK ----------
def se_block(x, reduction=16):
    filters = x.shape[-1]

    se = GlobalAveragePooling2D()(x)
    se = Dense(filters // reduction, activation="relu")(se)
    se = Dense(filters, activation="sigmoid")(se)
    se = Reshape((1, 1, filters))(se)

    return Multiply()([x, se])


# ---------- SPATIAL ATTENTION ----------
def spatial_attention(x):
    avg_pool = Lambda(lambda t: tf.reduce_mean(t, axis=-1, keepdims=True))(x)
    max_pool = Lambda(lambda t: tf.reduce_max(t, axis=-1, keepdims=True))(x)

    concat = Concatenate()([avg_pool, max_pool])
    attn = Conv2D(1, 7, padding="same", activation="sigmoid")(concat)

    return Multiply()([x, attn])


# ---------- FEATURE BRANCH ----------
def build_rgb_branch(inputs):

    x = Conv2D(32, 3, padding="same", activation="relu")(inputs)
    x = MaxPooling2D()(x)

    # Block 1
    x = residual_block(x, 64)
    x = se_block(x)
    x = MaxPooling2D()(x)

    # Block 2
    x = residual_block(x, 128)
    x = spatial_attention(x)
    x = MaxPooling2D()(x)

    # Block 3
    x = residual_block(x, 256)
    x = se_block(x)

    x = GlobalAveragePooling2D()(x)
    return x


# ---------- EMOTION MODEL ----------
def build_emotion_model():
    inp = Input(shape=(160,160,3))
    x = build_rgb_branch(inp)

    x = Dense(256, activation="relu")(x)
    x = Dropout(0.4)(x)

    x = Dense(128, activation="relu")(x)
    x = Dropout(0.3)(x)

    out = Dense(6, activation="softmax")(x)

    model = Model(inputs=inp, outputs=out)
    return model

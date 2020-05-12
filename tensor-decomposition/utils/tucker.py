import tensorly as tl
from tensorly.decomposition import partial_tucker
import numpy as np
from keras.layers import Conv2D


def tucker_decomposition(layer, tucker_rank):
    """
    :param: layer is a weight tensor of dimensions (k,k,c,f)
    :param: tucker_rank is a list [r1,r2]

    :returns: list of Conv2D layers [input_layer,core_layer,ouptut_layer]
            where
            - input layer is a Conv2D layer of dimensions (1,1,c,r1)
            - core layer is a Conv2D layer of dimensions (k,k,r1,r2)
            - output layer is a Conv2D layer of dimensions (1,1,f,r1)

    """
    strides = layer.get_config()['strides']
    padding = layer.get_config()['padding']

    weights = layer.get_weights()[0]
    bias = None
    if len(layer.get_weights()) > 1:
        bias = layer.get_weights()[1]

    # core - (k,k,r1,r2)
    # I - (c,r1)
    # O - (f,r2)
    core, [I, O] = partial_tucker(weights, modes=[2, 3], ranks=tucker_rank, init='svd')

    input_layer = Conv2D(filters=I.shape[1], kernel_size=1, strides=(1, 1), padding='valid',
                         input_shape=[None, None, I.shape[0]], use_bias=False)
    core_layer = Conv2D(filters=core.shape[-1], kernel_size=core.shape[0], strides=strides, padding=padding,
                        input_shape=[None, None, core.shape[-2]], use_bias=False)
    output_layer = Conv2D(filters=O.shape[0], kernel_size=1, strides=(1, 1), padding='valid',
                          input_shape=[None, None, core.shape[-1]], use_bias=True)

    input_layer.set_weights([I[np.newaxis, np.newaxis]])
    core_layer.set_weights([core])
    output_layer.set_weights([np.transpose(O)[np.newaxis, np.newaxis], bias])

    return [input_layer, core_layer, output_layer]


def tucker_reconstruction_loss(layer, rank):
    """
    :param: layer is a weight tensor of dimensions (k,k,c,f)
    :param: tucker_rank is a list [r1,r2]

    :returns: L2 reconstruction loss for the weight matrix after tucker decomposition and reonstructing
    """
    weights = layer.get_weights()[0]
    modes = [2, 3]
    core, factors = partial_tucker(weights, modes=modes, ranks=rank, init='svd')

    reconstructed = core
    for i in range(len(factors)):
        reconstructed = tl.tenalg.mode_dot(reconstructed, factors[i], modes[i])

    return np.mean((weights - reconstructed) ** 2)

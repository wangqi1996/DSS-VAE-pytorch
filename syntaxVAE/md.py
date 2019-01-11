# MIT License

# Copyright (c) 2018 the FastGEN-pytorch authors.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import torch
import torch.nn as nn


def find_val(inputs, val, axis=1):
    """
    Args:
        inputs: batch,max_len
        val: eos id
    Return:
        is_find: byteTensor [batch,1]
        indices: longTensor [batch,1]
    """
    val_match = (inputs == val)
    return ((val_match.cumsum(axis) == 1) & val_match).max(axis)


class MatrixMapper(nn.Module):
    """
    Input:
        z: batch_size,hidden
    Modules:
        mapper_k: z->hidden->k
        mapper_v: z->hidden->v
        k * v
    """

    def __init__(self, input_dim, hidden_dim, k_dim, v_dim, dropout=0.1):
        super(MatrixMapper, self).__init__()
        self.k_mapper = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(input_dim, hidden_dim, bias=True),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, k_dim, bias=True)
        )
        self.v_mapper = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(input_dim, hidden_dim, bias=True),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, v_dim, bias=True),
        )

    def forward(self, inputs):
        """
        Mapper the inputs to a matrix
        Args:
            inputs:(Tensor: batch_size, hidden) encoder output or latent variable.
        """
        k_vec = self.k_mapper.forward(inputs)
        v_vec = self.v_mapper.forward(inputs)
        batch_size = inputs.size(0)
        post_k = k_vec.contiguous().view(batch_size, -1, 1)
        post_v = v_vec.contiguous().view(batch_size, 1, -1)

        return torch.bmm(post_k, post_v)


class MatrixDecoder(nn.Module):
    """
    Input:
        z: batch_size, hidden
    Constructing:
        Inv(R): max_len X max_len
        S:  max_len X hidden_dim
    Modules:
        Matrix Mapper: z -> Inv(R)
        Matrix Mapper: z -> S
        Predictor: Inv(R)*S -> Tgt_V
    """

    def __init__(self, input_dim, hidden_dim, max_len, vocab_size, dropm=0.1, dropo=0.1):
        super(MatrixDecoder, self).__init__()
        self.max_len = max_len

        self.control_matrix_mapper = MatrixMapper(input_dim, hidden_dim, self.max_len, self.max_len, dropm)
        self.semantic_matrix_mapper = MatrixMapper(input_dim, hidden_dim, self.max_len, hidden_dim, dropm)

        self.word_predictor = nn.Sequential(
            nn.Dropout(dropo),
            nn.Linear(hidden_dim, hidden_dim, bias=True),
            nn.Dropout(dropo),
            nn.Linear(hidden_dim, vocab_size, bias=True)
        )

    def generate(self, con_inputs, sem_inputs):
        con_mat = self.control_matrix_mapper.forward(con_inputs)
        sem_mat = self.semantic_matrix_mapper.forward(sem_inputs)
        dec_init = torch.bmm(con_mat, sem_mat)
        return self.word_predictor.forward(dec_init)

    def forward(self, inputs, ):
        return self.generate(inputs, inputs)


class VarMD(MatrixDecoder):
    def __init__(self, input_dim, latent_dim, hidden_dim, max_len, vocab_size, dropm=0.1, dropo=0.1):
        super(VarMD, self).__init__(input_dim, hidden_dim, max_len, vocab_size, dropm, dropo)
        pass

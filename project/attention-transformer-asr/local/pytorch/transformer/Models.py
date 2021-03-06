''' Define the Transformer model '''
import torch
import torch.nn as nn
import numpy as np
import transformer.Constants as Constants
from transformer.Modules import BottleLinear as Linear
from transformer.Layers import EncoderLayer, DecoderLayer
import torch.nn.functional as F
__author__ = "Yu-Hsiang Huang"

# further edited by liu.baiji
# adapted for speech recognition

def position_encoding_init(n_position, d_pos_vec):
    ''' Init the sinusoid position encoding table '''
    # keep dim 0 for padding token position encoding zero vector
    position_enc = np.array([
        [pos / np.power(10000, 2 * (j // 2) / d_pos_vec) for j in range(d_pos_vec)]
        if pos != 0 else np.zeros(d_pos_vec) for pos in range(n_position)])

    position_enc[1:, 0::2] = np.sin(position_enc[1:, 0::2]) # dim 2i
    position_enc[1:, 1::2] = np.cos(position_enc[1:, 1::2]) # dim 2i+1
    return torch.from_numpy(position_enc).type(torch.FloatTensor)

def get_attn_padding_mask(seq_q, seq_k):
    ''' Indicate the padding-related part to mask '''
    assert seq_q.dim() == 2 and seq_k.dim() == 2
    mb_size, len_q = seq_q.size()
    mb_size, len_k = seq_k.size()

    pad_attn_mask = seq_k.data.eq(Constants.PAD).unsqueeze(1)   # bx1xsk
    pad_attn_mask = pad_attn_mask.expand(mb_size, len_q, len_k) # bxsqxsk

    return pad_attn_mask

def get_attn_subsequent_mask(seq):
    ''' Get an attention mask to avoid using the subsequent info.'''
    assert seq.dim() == 2
    attn_shape = (seq.size(0), seq.size(1), seq.size(1))
    subsequent_mask = np.triu(np.ones(attn_shape), k=1).astype('uint8')
    subsequent_mask = torch.from_numpy(subsequent_mask)
    if seq.is_cuda:
        subsequent_mask = subsequent_mask.cuda()
    return subsequent_mask

class Encoder(nn.Module):
    ''' A encoder model with self attention mechanism. '''
    def __init__(
            self, n_max_seq, n_layers=6, n_head=8, d_k=64, d_v=64,
            d_model=512, d_inner_hid=1024, dropout=0.1):

        super(Encoder, self).__init__()

        n_position = n_max_seq + 1
        self.n_max_seq = n_max_seq
        self.d_model = d_model

        self.layer_stack = nn.ModuleList([
            EncoderLayer(d_model, d_inner_hid, n_head, d_k, d_v, dropout=dropout)
            for _ in range(n_layers)])

    def forward(self, src_seq, src_pad_mask, return_attns=False):
        if return_attns:
            enc_slf_attns = []

        enc_output = src_seq
        enc_slf_attn_mask = get_attn_padding_mask(src_pad_mask, src_pad_mask)

        for enc_layer in self.layer_stack:
            enc_output, enc_slf_attn = enc_layer(
                enc_output, slf_attn_mask=enc_slf_attn_mask)
            if return_attns:
                enc_slf_attns += [enc_slf_attn]

        if return_attns:
            return enc_output, enc_slf_attns
        else:
            return enc_output,

class Decoder(nn.Module):
    ''' A decoder model with self attention mechanism. '''
    def __init__(
            self, n_max_seq, n_layers=6, n_head=8, d_k=64, d_v=64,
            d_model=512, d_inner_hid=1024, dropout=0.1):

        super(Decoder, self).__init__()
        n_position = n_max_seq + 1
        self.n_max_seq = n_max_seq
        self.d_model = d_model

        self.dropout = nn.Dropout(dropout)

        self.layer_stack = nn.ModuleList([
            DecoderLayer(d_model, d_inner_hid, n_head, d_k, d_v, dropout=dropout)
            for _ in range(n_layers)])

    def forward(self, tgt_seq, tgt_pad_mask, src_pad_mask, enc_output, return_attns=False):
        # Decode
        dec_slf_attn_pad_mask = get_attn_padding_mask(tgt_pad_mask, tgt_pad_mask)
        dec_slf_attn_sub_mask = get_attn_subsequent_mask(tgt_pad_mask)
        dec_slf_attn_mask = torch.gt(dec_slf_attn_pad_mask + dec_slf_attn_sub_mask, 0)

        dec_enc_attn_pad_mask = get_attn_padding_mask(tgt_pad_mask, src_pad_mask)

        if return_attns:
            dec_slf_attns, dec_enc_attns = [], []

        dec_output = tgt_seq
        for dec_layer in self.layer_stack:
            dec_output, dec_slf_attn, dec_enc_attn = dec_layer(
                dec_output, enc_output,
                slf_attn_mask=dec_slf_attn_mask,
                dec_enc_attn_mask=dec_enc_attn_pad_mask)

            if return_attns:
                dec_slf_attns += [dec_slf_attn]
                dec_enc_attns += [dec_enc_attn]

        if return_attns:
            return dec_output, dec_slf_attns, dec_enc_attns
        else:
            return dec_output,

class Transformer(nn.Module):
    ''' A sequence to sequence model with attention mechanism. '''
    def __init__(
            self, n_src_dim, n_tgt_vocab, n_max_seq, n_layers=6, n_head=8,
            d_model=512, d_inner_hid=1024, d_k=64, d_v=64, dropout=0.1,
            proj_share_weight=True, embs_share_weight=True):

        super(Transformer, self).__init__()
        self.encoder = Encoder(
            n_max_seq, n_layers=n_layers, n_head=n_head,
            d_model=d_model, d_inner_hid=d_inner_hid, dropout=dropout)
        self.decoder = Decoder(
            n_max_seq, n_layers=n_layers, n_head=n_head,
            d_model=d_model, d_inner_hid=d_inner_hid, dropout=dropout)

        #project the source to dim of model
        self.src_projection = Linear(n_src_dim, d_model, bias=False)
        self.tgt_word_emb = nn.Embedding(n_tgt_vocab, d_model, padding_idx=Constants.PAD)
        self.tgt_word_proj = Linear(d_model, n_tgt_vocab, bias=False)

        self.dropout = nn.Dropout(dropout)

    def get_trainable_parameters(self):
        ''' Avoid updating the position encoding '''
        #enc_freezed_param_ids = set(map(id, self.encoder.position_enc.parameters()))
        #dec_freezed_param_ids = set(map(id, self.decoder.position_enc.parameters()))
        #freezed_param_ids = enc_freezed_param_ids | dec_freezed_param_ids
        #return (p for p in self.parameters() if id(p) not in freezed_param_ids)
        return (p for p in self.parameters())

    def forward(self, src_seq, src_pad_mask, tgt_seq, tgt_pad_mask):
        #src_seq batch*len*featdim -> batch*len*modeldim
        src_seq = self.src_projection(src_seq)
        enc_output, *_ = self.encoder(src_seq, src_pad_mask)

        #word -> dim model
        tgt_seq = self.tgt_word_emb(tgt_seq)
        dec_output, *_ = self.decoder(tgt_seq, tgt_pad_mask, src_pad_mask, enc_output)
        seq_logit = self.tgt_word_proj(dec_output)

        #return batch*seq len*word dim
        return seq_logit
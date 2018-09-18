# a test file script, leaved by the developer
# maybe helpful when building your own project.
import sys

import argparse
from utils import instances_handler
import kaldi_io
import torch
from transformer.Models import Transformer

def test_vocab():
    parser = argparse.ArgumentParser()
    parser.add_argument('-read_instances_file', required=True)
    parser.add_argument('-save_vocab_file', required=True)
    parser.add_argument('-min_word_count', type=int, default=0)
    opt = parser.parse_args()

    print('--------------------[PROCEDURE]--------------------')
    print('[PROCEDURE] preparing vocabulary for output label')
    instances = instances_handler.read_instances(opt.read_instances_file)
    vocab = instances_handler.build_vocab(instances)
    instances_handler.save_vocab(vocab, opt.save_vocab_file)

    print(instances['sw02053-B_020556-020891'])
    instances_index = instances_handler.apply_vocab(instances, opt.save_vocab_file, 'word2idx')
    print(instances_index['sw02053-B_020556-020891'])
    instances = instances_handler.apply_vocab(instances_index, opt.save_vocab_file, 'idx2word')
    print(instances['sw02053-B_020556-020891'])


# a separate model initialization can split the parameter of model and trainning process,
# and help to improve the flexibility
# [to be done] should be able to convert kaldi nnet3 model into pytorch format?
def test_init_model():
    parser = argparse.ArgumentParser()
    parser.add_argument('-read_feats_scp_file', required=True)
    parser.add_argument('-read_vocab_file', required=True)
    parser.add_argument('-max_token_seq_len', type=int, required=True)

    parser.add_argument('-n_layers', type=int, default=6)
    parser.add_argument('-n_head', type=int, default=8)
    parser.add_argument('-d_word_vec', type=int, default=512)
    parser.add_argument('-d_model', type=int, default=512)
    parser.add_argument('-d_inner_hid', type=int, default=1024)
    parser.add_argument('-d_k', type=int, default=64)
    parser.add_argument('-d_v', type=int, default=64)
    parser.add_argument('-dropout', type=float, default=0.1)
    parser.add_argument('-proj_share_weight', action='store_true')
    parser.add_argument('-embs_share_weight', action='store_true')

    parser.add_argument('-save_model_file', required=True)
    opt = parser.parse_args()

    print('--------------------[PROCEDURE]--------------------')
    print('[PROCEDURE] reading dimension from data file and initialize the model')

    for key,matrix in kaldi_io.read_mat_scp(opt.read_feats_scp_file):
        opt.src_dim = matrix.shape[1]
        break
    print('[INFO] get feature of dimension {} from {}.'.format(opt.src_dim, opt.read_feats_scp_file))

    word2idx = torch.load(opt.read_vocab_file)
    opt.tgt_dim = len(word2idx)
    print('[INFO] get label of dimension {} from {}.'.format(opt.tgt_dim, opt.read_vocab_file))

    print('[INFO] model will initialized with add_argument:\n{}.'.format(opt))

    model = Transformer(
        opt.src_dim,
        opt.tgt_dim,
        opt.max_token_seq_len,
        n_layers=opt.n_layers,
        n_head=opt.n_head,
        d_word_vec=opt.d_word_vec,
        d_model=opt.d_model,
        d_inner_hid=opt.d_inner_hid,
        d_k=opt.d_k,
        d_v=opt.d_v,
        dropout=opt.dropout,
        proj_share_weight=opt.proj_share_weight,
        embs_share_weight=opt.embs_share_weight)

    checkpoint = {
        'model': model,
        'options': opt,
        'epoch': 0}

    torch.save(checkpoint, opt.save_model_file)
    #can be readed by:
    #checkpoint = torch.load(opt.save_model_file)
    #model = checkpoint['model']
    print('[INFO] initialized model is saved to {}.'.format(opt.save_model_file))

#simulating the parameter passing
def set_arg(command):
    arg_list = command.split()
    sys.argv = [sys.argv[0]]
    for arg in arg_list:
        sys.argv.append(arg)


if __name__ == '__main__':
#-----------------------------------------------------------------------------
    #set_arg("-read_instances_file data/text -save_vocab_file exp/vocab.torch")
    #test_vocab()
#-----------------------------------------------------------------------------
    #exit(0)
    command = "\
        -read_feats_scp_file data/feats.scp \
        -read_vocab_file exp/vocab.torch \
        -max_token_seq_len 50 \
        \
        -n_layers 6 \
        -n_head 8 \
        -d_word_vec 512 \
        -d_model 512 \
        -d_inner_hid 1024 \
        -d_k 64 \
        -d_v 64 \
        -dropout 0.1 \
        \
        -save_model_file exp/model.init"

    set_arg(command)
    test_init_model()
#-----------------------------------------------------------------------------
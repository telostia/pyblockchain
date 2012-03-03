#!/usr/bin/env python

# pyblockchain.py 1.0
# public domain

import struct
import os
import sys
import platform
import json
import hashlib
import optparse

def determine_db_dir():
    if platform.system() == 'Darwin':
        return os.path.expanduser('~/Library/Application Support/Bitcoin/')
    elif platform.system() == 'Windows':
        return os.path.join(os.environ['APPDATA'], 'Bitcoin')
    return os.path.expanduser('~/.bitcoin')

def dhash(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def  u8(f): return struct.unpack('B', f.read(1))[0]
def u16(f): return struct.unpack('H', f.read(2))[0]
def u32(f): return struct.unpack('I', f.read(4))[0]
def u64(f): return struct.unpack('Q', f.read(8))[0]
    
def var_int(f):
    t = u8(f)
    if   t == 0xfd: return u16(f)
    elif t == 0xfe: return u32(f)
    elif t == 0xff: return u64(f)
    else: return t

def opcode(t):
    if   t == 0xac: return 'OP_CHECKSIG'
    elif t == 0x76: return 'OP_DUP'
    elif t == 0xa9: return 'OP_HASH160'
    elif t == 0x88: return 'OP_EQUALVERIFY'
    else: return 'OP_UNSUPPORTED:%02X' % t

def parse_script(s):
    r = []
    i = 0
    while i < len(s):
        c = ord(s[i])
        i += 1
        if c > 0 and c < 0x4b:
            r.append(s[i:i+c].encode('hex'))
            i += c
        else:
            r.append(opcode(c))
    return ' '.join(r)

def read_string(f):
    len = var_int(f)
    return f.read(len)

def read_tx(f):
    tx_in = []
    tx_out = []
    startpos = f.tell()
    tx_ver = u32(f)

    vin_sz = var_int(f)

    for i in xrange(vin_sz):
        outpoint = f.read(32)
        n = u32(f)
        sig = read_string(f)
        seq = u32(f)
        type = int(n != 4294967295)
        name = ['coinbase','scriptSig'][type]
        prev_out = {'hash':outpoint.encode('hex'), 'n':n}
        tx_in.append({name:sig[type:].encode('hex'), "prev_out":prev_out})

    vout_sz = var_int(f)

    for i in xrange(vout_sz):
        value = u64(f)
        spk = parse_script(read_string(f))
        tx_out.append({'value': '%.8f' % (value * 1e-8), 'scriptPubKey': spk})

    lock_time = u32(f)

    size = f.tell() - startpos
    f.seek(startpos)
    hash = dhash(f.read(size))

    tx = {}
    tx['hash'] = hash[::-1].encode('hex')
    tx['ver'] = tx_ver
    tx['vin_sz'] = vin_sz
    tx['vout_sz'] = vout_sz
    tx['lock_time'] = lock_time
    tx['size'] = size
    tx['in'] = tx_in
    tx['out'] = tx_out

    return tx

def read_block(f, dump=False):
    magic = u32(f)
    size = u32(f)
    endpos = f.tell() + size

    if not dump:
        f.seek(endpos)
        return False

    header = f.read(80)
    (ver, pb, mr, ts, bits, nonce) = struct.unpack('I32s32sIII', header)
    hash = dhash(header)

    n_tx = var_int(f)

    r = {}
    r['hash'] = hash[::-1].encode('hex')
    r['ver'] = ver
    r['prev_block'] = pb.encode('hex')
    r['mrkl_root'] = mr.encode('hex')
    r['time'] = ts
    r['bits'] = bits
    r['nonce'] = nonce
    r['n_tx'] = n_tx
    r['size'] = size
    r['tx'] = []

    for i in xrange(n_tx):
        r['tx'].append(read_tx(f))

    return r

def read_blockchain(f, fsize, block=None):
    r = []
    fpos = 0
    blocks = 0
    while fpos < fsize:
        dump = (blocks == block)
        r = read_block(f, dump)
        fpos = f.tell()
        blocks += 1
        if not blocks % 1000 or fpos == fsize:
            sys.stderr.write('\r%d blocks' % blocks)
        if dump:
            break
    return r

def dump_blocks(block=None):
    fname = os.path.join(determine_db_dir(), 'blk0001.dat')
    f = open(fname, 'rb')
    f.seek(0, os.SEEK_END)
    fsize = f.tell()
    f.seek(0)
    r = read_blockchain(f, fsize, block)
    f.close()
    print json.dumps(r, indent=True)

def main():
    parser = optparse.OptionParser(usage='%prog [options]', version='%prog 1.0')

    parser.add_option('--dumpblock', dest='block',
        help='dump block by index in json format')

    (options, args) = parser.parse_args()

    if options.block is None:
        print 'A mandatory option is missing\n'
        parser.print_help()
        sys.exit(1)

    dump_blocks( int(options.block) )

if __name__ == '__main__':
    main()

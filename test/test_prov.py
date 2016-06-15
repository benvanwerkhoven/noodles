from noodles.prov import prov_key
from noodles import serial, gather, schedule_hint
from noodles.tutorial import add, sub, mul, accumulate
from noodles.prov import prov_key
from noodles.run.worker import run_job
from noodles.run.run_with_prov import (
    run_single, run_parallel, run_parallel_optional_prov)

import json

def test_prov_00():
    reg = serial.base()
    a = add(3, 4)
    b = sub(3, 4)
    c = add(3, 4)
    d = add(4, 3)
 
    enc = [reg.deep_encode(x._workflow.root_node) for x in [a, b, c, d]]
    key = [prov_key(o) for o in enc]
    assert key[0] == key[2]
    assert key[1] != key[0]
    assert key[3] != key[0]


def test_prov_01():
    reg = serial.base()
    a = add(3, 4)

    enc = reg.deep_encode(a._workflow.root_node)
    dec = reg.deep_decode(enc)

    result = run_job(0, dec)
    assert result.value == 7

def test_prov_02():
    db_file = "prov1.json"

    A = add(1, 1)
    B = sub(3, A)

    multiples = [mul(add(i, B), A) for i in range(6)]
    C = accumulate(gather(*multiples))
    
    result = run_single(C, serial.base, db_file)
    assert result == 42

def test_prov_03():
    db_file = "prov2.json"

    A = add(1, 1)
    B = sub(3, A)

    multiples = [mul(add(i, B), A) for i in range(6)]
    C = accumulate(gather(*multiples))
    
    result = run_parallel(C, 4, serial.base, db_file)
    assert result == 42


@schedule_hint(store=True)
def add2(x, y):
    return x + y


def test_prov_04():
    db_file = "prov3.json"

    A = add2(1, 1)
    B = sub(3, A)

    multiples = [mul(add2(i, B), A) for i in range(6)]
    C = accumulate(gather(*multiples))
    
    result = run_parallel_optional_prov(C, 4, serial.base, db_file)
    assert result == 42

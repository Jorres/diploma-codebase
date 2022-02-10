import sys
import os
  
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
from formula_builder import PicklablePool, TPoolHolder


def test_my_pool_same_as_pysat_pool():
    names = ['a1', 'a2', 'a3', 'a4', 'a1', 'a3', 'a18']

    my_pool = PicklablePool()
    pysat_pool = TPoolHolder()

    ids = list()
    for name in names:
        my_id = my_pool.v_to_id(name)
        pysat_id = pysat_pool.v_to_id(name)
        assert my_id == pysat_id
        ids.append(my_id)

    for id in ids:
        assert my_pool.id_to_v(id) == pysat_pool.id_to_v(id)




from typing import List
from orbdetpy.rpc.messages_pb2 import Settings, SettingsArray
from orbdetpy.rpc.propagation_pb2_grpc import PropagationStub
from orbdetpy.rpc.server import RemoteServer

def propagate_orbits(cfg_list: List[Settings]):
    """Propagate orbits and optionally simulate measurements.

    Parameters
    ----------
    cfg_list: List of Settings objects.

    Returns
    -------
    Propagated state vectors and simulated measurements.
    """

    resp = _propagation_stub.propagate(SettingsArray(array=[p for p in cfg_list]))
    return(resp.array)

if (__name__ != '__main__'):
    __pdoc__ = {m: False for m in ("Settings", "SettingsArray")}
    _propagation_stub = PropagationStub(RemoteServer.channel())

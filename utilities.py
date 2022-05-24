

from typing import List
from orbdetpy.rpc.messages_pb2 import DoubleArray, InterpolateEphemerisInput
from orbdetpy.rpc.server import RemoteServer
from orbdetpy.rpc.utilities_pb2_grpc import UtilitiesStub

def interpolate_ephemeris(source_frame: int, times: List[float], states, num_points: int,
                          dest_frame: int, interp_start: float, interp_end: float, step_size: float):
    """Interpolates the given state vectors.

    Parameters
    ----------
    source_frame : Source reference frame; a constant from Frame.
    times : Times of state vectors; each a TT offset from J2000 epoch [s].
    states : State vectors to interpolate.
    num_points : Number of states to use for interpolation.
    dest_frame : Destination reference frame; a constant from Frame.
    interp_start : Interpolation start time.
    interp_end : Interpolation end time.
    step_size : Interpolation step size [s].

    Returns
    -------
    Interpolated times and state vectors.
    """

    resp = _utilities_stub.interpolateEphemeris(InterpolateEphemerisInput(
        source_frame=source_frame, time=times, ephem=[DoubleArray(array=s) for s in states], num_points=num_points,
        dest_frame=dest_frame, interp_start=interp_start, interp_end=interp_end, step_size=step_size))
    return(resp.array)

if (__name__ != '__main__'):
    __pdoc__ = {m: False for m in ("DoubleArray", "InterpolateEphemerisInput")}
    _utilities_stub = UtilitiesStub(RemoteServer.channel())



from datetime import datetime
from typing import List
from orbdetpy import Constant, Frame, MeasurementType
from orbdetpy.conversion import get_UTC_string
from orbdetpy.rpc.messages_pb2 import ImportTDMInput, Settings
from orbdetpy.rpc.server import RemoteServer
from orbdetpy.rpc.utilities_pb2_grpc import UtilitiesStub

def export_OEM(cfg: Settings, obs, obj_id: str, obj_name: str, time_list: List[str]=None, add_prop_cov: bool=False)->str:
    

    utc_list = get_UTC_string([o.time for o in obs])
    oem_header = f"""CCSDS_OEM_VERS = 2.0
CREATION_DATE = {datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
ORIGINATOR = UT-Austin

META_START
OBJECT_NAME = {obj_name}
OBJECT_ID = {obj_id}
CENTER_NAME = EARTH
REF_FRAME = {cfg.prop_inertial_frame}
TIME_SYSTEM = UTC
START_TIME = {time_list[0] if (time_list) else utc_list[0][:-1]}
STOP_TIME = {time_list[-1] if (time_list) else utc_list[-1][:-1]}
META_STOP

"""

    eph_data, estm_cov, prop_cov, added  = [], [], [], set()
    is_estm = (hasattr(obs[0], "estimated_state") and hasattr(obs[0], "estimated_covariance")
               and hasattr(obs[0], "propagated_covariance"))
    eph_key = "estimated_state" if (is_estm) else "true_state"
    for utc, o in zip(utc_list, obs):
        utc = utc[:-1]
        if (o.time in added):
            continue
        added.add(o.time)
        if (time_list is not None and utc not in time_list):
            continue
        X = [x/1000.0 for x in getattr(o, eph_key)[:6]]
        eph_data.append(f"{utc} {X[0]} {X[1]} {X[2]} {X[3]} {X[4]} {X[5]}")

        if (is_estm and len(o.estimated_covariance) >= 21):
            estm_cov.append(f"\nEPOCH = {utc}")
            for m in range(6):
                n = (m**2 + m)//2
                estm_cov.append(" ".join([str(x/1E6) for x in o.estimated_covariance[n:m+n+1]]))
        if (is_estm and add_prop_cov and len(o.propagated_covariance) >= 21):
            prop_cov.append(f"\nEPOCH = {utc}")
            for m in range(6):
                n = (m**2 + m)//2
                prop_cov.append(" ".join([str(x/1E6) for x in o.propagated_covariance[n:m+n+1]]))

    oem_data = oem_header + "\n".join(eph_data)
    if (len(estm_cov) > 0):
        oem_data += "\n\nCOMMENT Updated covariance\nCOVARIANCE_START" + "\n".join(estm_cov) + "\nCOVARIANCE_STOP"
    if (len(prop_cov) > 0):
        oem_data += "\n\nCOMMENT Propagated covariance\nCOVARIANCE_START" + "\n".join(prop_cov) + "\nCOVARIANCE_STOP"
    return(oem_data)

def export_TDM(cfg: Settings, obs, obj_id: str, station_list: List[str]=None)->str:
    """Export tracking data in CCSDS TDM format.

    Parameters
    ----------
    cfg : Settings object.
    obs : Measurements to export.
    obj_id : Object identifier.
    station_list : List of ground stations to include; None to include all.

    Returns
    -------
    Tracking data in TDM format.
    """

    miter = cfg.measurements.keys()
    utc_list = get_UTC_string([o.time for o in obs])
    if (MeasurementType.RIGHT_ASCENSION in miter and MeasurementType.DECLINATION in miter):
        obstype = f"ANGLE_TYPE = RADEC\nREFERENCE_FRAME = {cfg.prop_inertial_frame}"
        obspath = "1,2"
    if (MeasurementType.AZIMUTH in miter and MeasurementType.ELEVATION in miter):
        obstype = "ANGLE_TYPE = AZEL"
        obspath = "1,2"
    if (MeasurementType.RANGE in miter or MeasurementType.RANGE_RATE in miter):
        obspath = "2,1,2"
        if (MeasurementType.AZIMUTH in miter and MeasurementType.ELEVATION in miter):
            obstype = "RANGE_UNITS = km\nANGLE_TYPE = AZEL"
        else:
            obstype = "RANGE_UNITS = km"

    blocks = []
    tdm_header = f"""CCSDS_TDM_VERS = 1.0
CREATION_DATE = {datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
ORIGINATOR = UT-Austin

"""

    for sname, sinfo in cfg.stations.items():
        if (station_list is not None and sname not in station_list):
            continue
        lat, lon, alt = sinfo.latitude/Constant.DEGREE_TO_RAD, sinfo.longitude/Constant.DEGREE_TO_RAD, sinfo.altitude/1000.0
        blocks.append(f"""META_START
TIME_SYSTEM = UTC
PARTICIPANT_1 = {obj_id}
PARTICIPANT_2 = {sname} (WGS-84 Latitude: {lat} deg, Longitude: {lon} deg, Altitude: {alt} km)
MODE = SEQUENTIAL
PATH = {obspath}
{obstype}
META_STOP
""")
        blocks.append("DATA_START")

        for utc, o in zip(utc_list, obs):
            utc = utc[:-1]
            if (o.station != sname):
                continue
            if (MeasurementType.RANGE in miter or MeasurementType.RANGE_RATE in miter):
                if (MeasurementType.RANGE in miter):
                    blocks.append(f"RANGE = {utc} {o.values[0]/1000.0}")
                if (MeasurementType.RANGE_RATE in miter):
                    blocks.append(f"DOPPLER_INSTANTANEOUS = {utc} {o.values[-1]/1000.0}")
            if ((MeasurementType.AZIMUTH in miter and MeasurementType.ELEVATION in miter) or
                (MeasurementType.RIGHT_ASCENSION in miter and MeasurementType.DECLINATION in miter)):
                blocks.append((f"""ANGLE_1 = {utc} {o.values[0]/Constant.DEGREE_TO_RAD}\n"""
                               f"""ANGLE_2 = {utc} {o.values[1]/Constant.DEGREE_TO_RAD}"""))
        blocks.append(f"DATA_STOP\n")

    return(tdm_header + "\n".join(blocks))

def import_TDM(file_name: str, file_format: int):
    """Import tracking data from CCSDS TDM file.

    Parameters
    ----------
    file_name : Fully qualified TDM file.
    file_format : Constant from TDMFileFormat.

    Returns
    -------
    Measurements object.
    """

    resp = _ccsds_stub.importTDM(ImportTDMInput(file_name=file_name, file_format=file_format))
    return(resp.array)

if (__name__ != '__main__'):
    __pdoc__ = {m: False for m in ("ImportTDMInput", "Settings")}
    _ccsds_stub = UtilitiesStub(RemoteServer.channel())

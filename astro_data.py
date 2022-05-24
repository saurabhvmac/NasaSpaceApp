

import requests
from os import path
from orbdetpy import _data_dir

def format_weather(lines: str)->str:
    """Re-format space weather data into a more efficient form.
    """

    output = []
    c1 = [0, 5,  8, 11, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 47, 51, 55, 59, 63, 67,
          71, 75, 79, 83, 87, 89, 93,  99, 101, 107, 113, 119, 125]
    c2 = [5, 8, 11, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 47, 51, 55, 59, 63, 67, 71,
          75, 79, 83, 87, 89, 93, 99, 101, 107, 113, 119, 125, 131]
    for line in lines.splitlines():
        if (line == "END DAILY_PREDICTED"):
            break
        if (len(line) > 0 and line[0].isnumeric()):
            output.append(",".join([line[i:j] for i, j in zip(c1, c2)]))
    return("\n".join(output))

def update_data()->None:
    """Download and re-format astrodynamics data from multiple sources.
    """

    updates = [["https://datacenter.iers.org/data/latestVersion/7_FINALS.ALL_IAU1980_V2013_017.txt",
                path.join(_data_dir, "Earth-Orientation-Parameters", "IAU-1980", "finals.all"), None],
               ["https://datacenter.iers.org/data/latestVersion/9_FINALS.ALL_IAU2000_V2013_019.txt",
                path.join(_data_dir, "Earth-Orientation-Parameters", "IAU-2000", "finals2000A.all"), None],
               ["http://astria.tacc.utexas.edu/AstriaGraph/SP_ephemeris/tai-utc.dat", path.join(_data_dir, "tai-utc.dat"), None],
               ["http://www.celestrak.com/SpaceData/SW-All.txt", path.join(_data_dir, "SpaceWeather.dat"), format_weather]]
    # http://maia.usno.navy.mil/ser7
    for u in updates:
        print(f"Updating {u[1]}")
        try:
            resp = requests.get(u[0], timeout=10.0)
            if (resp.status_code == requests.codes.ok):
                with open(u[1], "w") as fp:
                    fp.write(u[2](resp.text) if (u[2] is not None) else resp.text)
            else:
                print(f"HTTP error: {resp.status_code}")
        except Exception as exc:
            print(exc)

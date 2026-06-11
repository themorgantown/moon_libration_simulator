import numpy as np
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_body, get_body_barycentric

# Define the initial time and location
initial_time = Time('2024-04-01 00:00:00', scale='utc')
location = EarthLocation(lat=0 * u.deg, lon=0 * u.deg, height=0 * u.m)  # Equator

# Define time range for simulation
t_start = initial_time
t_end = initial_time + 365.25 * u.day
dt = 1 * u.hour
t = np.arange(t_start.jd, t_end.jd, dt.to(u.day).value)

# Initialize lists to store coordinates
x, y, z = [], [], []

# Simulate laser beam path
for t_jd in t:
  time = Time(t_jd, format='jd', scale='utc')
  earth_location = location.get_gcrs(time)
  laser_altaz = AltAz(obstime=time, location=location, az=0*u.deg, alt=90*u.deg)  # Initialize laser_altaz with az and alt values
  laser_gcrs = laser_altaz.transform_to(earth_location)

  # Append coordinates to lists
  x.append(laser_gcrs.cartesian.x.value)
  y.append(laser_gcrs.cartesian.y.value)
  z.append(laser_gcrs.cartesian.z.value)

# Plot the resulting shape
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.plot(x, y, z)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.show()



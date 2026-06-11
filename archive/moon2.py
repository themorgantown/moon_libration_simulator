import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d  # Import the 3D plotting toolkit

from astropy import units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz

# Define the initial time and location
initial_time = Time('2024-04-01 00:00:00', scale='utc')
location = EarthLocation(lat=0 * u.deg, lon=0 * u.deg, height=0 * u.m)  # Equator

# Define time range for simulation
# Define the start time as the initial time
t_start = initial_time
# Define the end time as the initial time plus 7 days
t_end = initial_time + .7 * u.day
# Define the time step as 1 hour
dt = 1 * u.hour
# Generate an array of time values from the start time to the end time with the specified time step
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

# Create a 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the resulting shape
ax.plot(x, y, z, color='lightgreen', linewidth=2)

# Show the plot
plt.show()

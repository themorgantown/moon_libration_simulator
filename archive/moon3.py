import numpy as np
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_body
from astropy.coordinates import get_body_barycentric
from astropy.coordinates.representation import CartesianRepresentation
# Define the initial time and location
initial_time = Time('2024-04-01 00:00:00', scale='utc')
moon_location = get_body("moon", initial_time, ephemeris='jpl')

# Define the laser's initial position and orientation on the Moon
laser_lat = 0 * u.deg
laser_lon = 0 * u.deg
laser_alt = 90 * u.deg
laser_az = 0 * u.deg

laser_location = EarthLocation(lat=laser_lat, lon=laser_lon, height=0 * u.m)

# Define time range for simulation
t_start = initial_time
t_end = initial_time + 7 * u.day
dt = 1 * u.hour
t = np.arange(t_start.jd, t_end.jd, dt.to(u.day).value)

# Initialize lists to store coordinates
x, y, z = [], [], []

# Simulate laser beam path
for t_jd in t:
  time = Time(t_jd, format='jd', scale='utc')
  moon_location = get_body("moon", time, ephemeris='jpl')
  earth_location = get_body_barycentric('earth', time)
  laser_altaz = AltAz(obstime=time, location=laser_location, az=laser_az, alt=laser_alt)
  laser_gcrs = laser_altaz.transform_to(earth_location)

  # Append coordinates to lists
  x.append(laser_gcrs.cartesian.x.value)
  y.append(laser_gcrs.cartesian.y.value)
  z.append(laser_gcrs.cartesian.z.value)

# Create a 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the laser beam path
ax.plot(x, y, z, color='lightgreen', linewidth=2)

# Create a sphere representing the Earth
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
x_sphere = np.outer(np.cos(u), np.sin(v))
y_sphere = np.outer(np.sin(u), np.sin(v))
z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))

# Plot the wireframe sphere
ax.plot_wireframe(x_sphere, y_sphere, z_sphere, color='gray', alpha=0.5)

# Set axis labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

# Show the plot
plt.show()
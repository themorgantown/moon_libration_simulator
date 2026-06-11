from astropy import units as u
from astropy.coordinates import EarthLocation, get_body, AltAz, solar_system_ephemeris
from astropy.time import Time
import numpy as np
import matplotlib.pyplot as plt

# Use JPL ephemerides for accurate positions, including lunar libration
solar_system_ephemeris.set('jpl')

# Observation time and location on Earth
observation_time = Time('2020-04-04T00:00:00')
earth_location = EarthLocation(lat=41.2033*u.deg, lon=-74.0924*u.deg, height=0*u.m)

# Generate times spanning one year with 10 observations per day
num_steps = 365
time_span = 500 * u.day  # Total duration in days
times = observation_time + np.linspace(0, 1, num_steps) * time_span

# Initialize lists to store coordinates and colors
latitudes = []
longitudes = []
colors = []

# Loop through times to calculate positions and colors
for i, t in enumerate(times):
    # Get Moon's position from Earth's location at current time
    moon = get_body('moon', t, earth_location)
    
    # Convert to AltAz to find the position in the sky relative to Earth's surface
    moon_altaz = moon.transform_to(AltAz(obstime=t, location=earth_location))
    
    # Assuming the laser points directly from the Moon to the observer's location
    # We simulate the Earth's rotation by considering the observer's position at different times
    lat = earth_location.lat.deg
    lon = (earth_location.lon.deg + (t - observation_time).to(u.hour).value * 15) % 360
    
    latitudes.append(lat)
    longitudes.append(lon)
    
    # Calculate the color based on the index
    color = (i / (num_steps - 1), i / (num_steps - 1), i / (num_steps - 1))
    colors.append(color)

# Convert to numpy arrays for plotting
latitudes = np.array(latitudes)
longitudes = np.array(longitudes)
colors = np.array(colors)

# Plotting
fig = plt.figure(figsize=(10, 5))
ax = fig.add_subplot(111, projection='mollweide')
ax.scatter(np.radians(longitudes) - np.pi, np.radians(latitudes), color=colors, marker='o', s=10)  # Adjust point size and color
ax.set_title("Path Traced by Laser on Earth Over One year")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(True)

plt.show()

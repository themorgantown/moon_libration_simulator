from astropy import units as u
from astropy.time import Time
from astropy.coordinates import solar_system_ephemeris, get_body, EarthLocation, GeocentricTrueEcliptic
import numpy as np
import matplotlib.pyplot as plt

# Ensure astropy.units is correctly imported and used
initial_time = Time('2019-01-01 00:00:00', scale='utc')
end_time = initial_time + 300 * u.day
delta_time = 1 * u.hour

times = Time(np.arange(initial_time.jd, end_time.jd, delta_time.to(u.day).value), format='jd', scale='utc')

# Set up the plot
fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='3d')

with solar_system_ephemeris.set('jpl'):
    for t in times:
        moon_location = get_body('moon', t, EarthLocation.of_site('greenwich'))
        
        # Transform to GeocentricTrueEcliptic to work with ecliptic coordinates
        moon_ecliptic = moon_location.transform_to(GeocentricTrueEcliptic())
        
        # Here, we use u.deg to ensure that units are correctly applied
        laser_target_lon = moon_ecliptic.lon.wrap_at(180 * u.deg)
        laser_target_lat = moon_ecliptic.lat
        
        # Visualization purposes, Earth's radius is considered 1 unit
        x = np.cos(laser_target_lat) * np.cos(laser_target_lon)
        y = np.cos(laser_target_lat) * np.sin(laser_target_lon)
        z = np.sin(laser_target_lat)
        
        # Calculate the color based on the hour
        hour_index = int((t - initial_time) / delta_time)
        color = (1 - hour_index / len(times), 0, 0)  # Red component decreases with each hour
        
        ax.scatter(x, y, z, color=color, s=10)  # Plot each point where the laser intersects Earth

ax.set_title("Laser Path from Moon to Earth Over 7 Days")
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.show()
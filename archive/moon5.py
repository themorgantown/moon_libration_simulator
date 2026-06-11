from astropy import units as u
from astropy.time import Time
from astropy.coordinates import solar_system_ephemeris, get_body, EarthLocation, GeocentricTrueEcliptic
from astropy import units as u
import numpy as np
import matplotlib.pyplot as plt

# Real-world parameters with scaling
earth_radius_km = 6371  # Earth's radius in kilometers
moon_distance_km = 384400  # Average Moon-Earth distance in kilometers
scale_factor = 1 / 6371  # Scale factor for visualization (making Earth's radius = 1 unit in the plot)

# Time setup
initial_time = Time('2019-04-01 00:00:00', scale='utc')
end_time = initial_time + 1 * u.day
delta_time = 1 * u.hour
times = Time(np.arange(initial_time.jd, end_time.jd, delta_time.to(u.day).value), format='jd', scale='utc')

# Plot setup
fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection='3d')

# Generate points for a sphere (scaled Earth)
u, v = np.mgrid[0:2*np.pi:100j, 0:np.pi:50j]
x_earth = np.cos(u) * np.sin(v)
y_earth = np.sin(u) * np.sin(v)
z_earth = np.cos(v)
ax.plot_surface(x_earth, y_earth, z_earth, color='blue', alpha=0.3)

with solar_system_ephemeris.set('jpl'):
    for t in times:
        moon_location = get_body('moon', t, EarthLocation.of_site('greenwich'))
        moon_ecliptic = moon_location.transform_to(GeocentricTrueEcliptic())
        laser_target_lon = moon_ecliptic.lon.wrap_at(180 * u.degrees)
        laser_target_lat = moon_ecliptic.lat

        # Adjustments for real-world scale in visualization
        x = np.cos(laser_target_lat) * np.cos(laser_target_lon) * scale_factor
        y = np.cos(laser_target_lat) * np.sin(laser_target_lon) * scale_factor
        z = np.sin(laser_target_lat) * scale_factor
        
        # Plot each point where the laser intersects Earth
        ax.scatter(x, y, z, color='red', s=10)

# Customizing the plot
ax.set_title("Laser Path from Moon to Earth Over 600 Days")
ax.set_xlabel('X (in Earth Radii)')
ax.set_ylabel('Y (in Earth Radii)')
ax.set_zlabel('Z (in Earth Radii)')

# Adjusting limits to match the scaled Earth
ax.set_xlim([-1, 1])
ax.set_ylim([-1, 1])
ax.set_zlim([-1, 1])

plt.show()

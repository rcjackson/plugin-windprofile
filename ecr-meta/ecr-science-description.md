## Halo Photonics Doppler lidar spectral processing

This plugin will process Velocity Azimuth Display scans from Halo Photonics Doppler lidars. For these scans, the lidar will make a sweep along a constant elevation at a fixed number of beams that split the range of azimuth angles equally. Typically, 6 beams are used, positioned every 60 degrees. From these profiles, we get a radial wind velocity measurement. In order to convert these radial wind velocities to two-dimensional wind velocities, post-processing techniques must be applied [1]. This plugin will apply these post-processing techniques and then provide both full profiles as well as statistics on the low level jet and hub height winds. The code in this plugin uses the Atmospheric Data community Toolkit [2].

## References

1. Newsom, R. K., Brewer, W. A., Wilczak, J. M., Wolfe, D. E., Oncley, S. P., and Lundquist, J. K.: Validating precision estimates in horizontal wind measurements from a Doppler lidar, Atmos. Meas. Tech., 10, 1229–1240, https://doi.org/10.5194/amt-10-1229-2017, 2017. 
2. Adam Theisen, Ken Kehoe, Zach Sherman, Bobby Jackson, Max Grover, Alyssa J. Sockol, Corey Godine, Jason Hemedinger, Joe O'Brien, jkyrouac, Maxwell Levin, & dennyh-ssec. (2024). ARM-DOE/ACT: ACT Release Version 2.1.6 (v2.1.6). Zenodo. https://doi.org/10.5281/zenodo.14053660

## Arguments
    
    --lidar_ip_addr: Lidar's IP address
    --lidar_uname: Lidar's username
    --lidar_pwd: Lidar's password
    --profname: Name of the scan type to use (VAD, User1, etc.)
    --site: The name of the site for filenames.
    --lat: The site latitude
    --lon: The site longitude
    --alt: The site altitude
    --intensity-threshold: The intensity threshold for processing the data.

# Data description
The plugin will upload two different types of files for the "upload" variable. One netCDF file containing the processed VAD data. The following variables are provided in this netCDF file:

    "wind_speed": The wind speed in m/s.
    "wind_direction": The wind direction in degrees.
    "wind_speed_error": The root mean squared error in the wind speed fit to the radial velocities.
    "wind_direction_error": The root mean squared error in the wind direction fit to the radial velocities.
    "signal_to_noise_ratio": The signal to noise ratio in linear units. Note: in the lidar world, SNR = 0 is the noise floor (not 1!).
    "residual": The Chi-square value of the fit of the wind speed to the radial velocities.
    "correlation": The correlation coefficient of the wind speed fit to the radial velocities.

The other "upload" key shows a .png file with a quicklook of the wind profile. In addition, there are several variables that output basic statistics of the wind profile below 1 km:
     "lidar.hub_wind_spd": The hub height (150 m) wind speed.
     "lidar.hub_wind_dir": The hub height wind direction.
     
These variables provide information about the speed, direction, and prominence of the low level jet:
     "lidar.llj_nose_height": The height of the nose of the low level jet (maximum wind speed in lowest 1 km).
     "lidar.llj_nose_spd": The speed of the nose of the low level jet.
     "lidar.llj_nose_dir": The direction of the nose of the low level jet.
     "lidar.bottom_nose_shear": The speed shear from the low level jet nose to 100 m.
     "lidar.top_nose_shear": The speed shear from the top of the low level jet to the nose (median wind speed above jet - speed at nose).

# Data Query
To query the last hour of data, do:
```
df = sage_data_client.query(
            start="-1h",
            filter={"name": "upload", "vsn": "W0C0",
                   "plugin": "10.31.81.1:5000/local/plugin-windprofile"},).set_index("timestamp")
```                   
The names of the available files are in the *value* key of the dataframe.

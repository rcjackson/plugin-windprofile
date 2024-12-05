import xarray as xr
import os
import paramiko
import time
from waggle.plugin import Plugin
import logging
import act
import shutil
import gzip
import argparse
import datetime
import glob
import numpy as np
import gc
import matplotlib.pyplot as plt

from utils import read_as_netcdf
logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    cur_time = datetime.datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument('--lidar_ip_addr', type=str, default='10.31.81.87',
            help='Lidar IP address')
    parser.add_argument('--lidar_uname', type=str, default='end user',
            help='Lidar username')
    parser.add_argument('--lidar_pwd', type=str, default='',
            help='Lidar password')
    parser.add_argument('--profname', type=str, default="User5",
            help='Number of points to store in processing interval')
    parser.add_argument('--site', type=str, default='caco', 
            help='Site name')
    parser.add_argument('--lat', type=float, default=42.03246980148044,
            help="Site latitude")
    parser.add_argument('--lon', type=float, default=-70.05347316862381,
            help="Site longitude")
    parser.add_argument('--alt', type=float, default=0, help="Site altitude")
    parser.add_argument('--intensity_threshold', type=float, default=1.008,
            help="Intensity threshold for signal")
    args = parser.parse_args()
    lidar_ip_addr = args.lidar_ip_addr
    lidar_uname = args.lidar_uname
    lidar_pwd = args.lidar_pwd
    cur_time = datetime.datetime.now()
            
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.debug("Connecting to %s" % lidar_ip_addr)
        ssh.connect(lidar_ip_addr, username=lidar_uname, password=lidar_pwd)
        year = cur_time.year
        day = cur_time.day
        month = cur_time.month
        hour = cur_time.hour
        prev_day = cur_time - datetime.timedelta(days=1)
        prev_hour = cur_time - datetime.timedelta(hours=1)
        # Look at past 2 days (since we may be running at 0 UTC where no current day data exists)
        file_path = "/C:/Lidar/Data/Proc/%d/%d%02d/%d%02d%02d/" % (year, year, month, year, month, day)
        site = args.site
        file_path_prev = "/C:/Lidar/Data/Proc/%d/%d%02d/%d%02d%02d/" % (prev_day.year, prev_day.year, prev_day.month, prev_day.year, prev_day.month, prev_day.day)
        with ssh.open_sftp() as sftp:
            logging.debug("Connected to the Lidar!")
            time_string = '%d%02d%02d_%02d' % (year, month, day, hour)
            time_string_prev = '%d%02d%02d_%02d' % (prev_hour.year, prev_hour.month, prev_hour.day, prev_hour.hour)
            file_list = sftp.listdir(file_path) + sftp.listdir(file_path_prev)
            file_name = None
            file_list = sorted(file_list)
            dataset = []
            for f in file_list:
                if args.profname in f and (time_string in f or time_string_prev in f):   
                    file_name = f
                    
                    sftp.get(os.path.join(file_path, file_name), file_name)
                    try:
                        ds = read_as_netcdf(file_name, args.lat, args.lon, args.alt)
                        # If we're doing 7-point VADs, then remove the vertical
                        ds = ds.where(ds.elevation < 89., drop=True)
                        ds = ds.drop_dims("sweep")
                    except:
                        continue
                    dataset.append(ds)
            dataset = xr.concat(dataset, dim="time")
            # Get TKE
            ds["radial_velocity"] = ds["radial_velocity"].where(ds["intensity"] > args.intensity_threshold)
            # Get TKE from last 30 min of VADs
            final_time = str(ds["time"][-1].dt.strftime("%Y-%m-%dT%H:%M:%S").values)
            half_hour_before = datetime.datetime.fromisoformat(final_time) - datetime.timedelta(minutes=30)
            half_hour_before = half_hour_before.isoformat()
            tke = 0.5*(ds["radial_velocity"].sel(
                time=slice(half_hour_before, final_time)).std(dim='time')**2)
            sin60 = np.sqrt(3) / 2
            tke_hub = tke.sel(range=(150. / sin60), method='nearest').values
            tke_prof = tke.sel(range=slice(90., 3000.))
            dataset_time = dataset["time"][-1].values
            print(dataset_time)
            dataset = dataset.isel(time=slice(dataset.sizes['time'] - 6, dataset.sizes['time']))
            dataset = act.retrievals.compute_winds_from_ppi(
                    dataset, intensity_name='intensity',
                    snr_threshold=args.intensity_threshold-1)
                    
            fig, ax = plt.subplots(1, 1, figsize=(5, 5))
            ax2 = ax.twiny()
            dataset["wind_speed"].mean(dim='time').plot(y='height', ax=ax, label='Spd', color='b')
            dataset["wind_direction"].mean(dim='time').plot(y="height", ax=ax2, label='Dir', color='r')
            ax.set_ylim([0, 3000])
            ax2.set_ylim([0, 3000])
            ax.set_xlim([0, 30])
            ax2.set_xlim([0, 360.])
            fig.legend()
            ax2.set_xlabel('Direction [degrees]')
            ax.set_xlabel('Speed [m/s]')
            png_out_name = '%s.lidar.wind_profile.%s.png' % (
                    args.site, dataset['time'][0].dt.strftime('%Y%m%s.%H%M%S').values)
            nc_out_name = '%s.lidar.wind_profile.%s.nc' % (
                    args.site, dataset['time'][0].dt.strftime('%Y%m%s.%H%M%S').values)
            fig.savefig(png_out_name, bbox_inches='tight', dpi=150)
            wind_rotor_spd = dataset["wind_speed"].sel(
                        height=150., method='nearest').values
            wind_rotor_dir = dataset["wind_direction"].sel(
                        height=150., method='nearest').values
            llj_nose = dataset["wind_speed"].sel(
                    height=slice(100., 1000)).argmax(dim="height")
            llj_nose_spd = dataset["wind_speed"].isel(height=llj_nose)
            llj_nose_dir = dataset["wind_direction"].isel(height=llj_nose)
            llj_nose_height = dataset["height"][llj_nose].values
            bottom_nose_shear = dataset["wind_speed"].sel(
                    height=llj_nose_height) - dataset["wind_speed"].sel(height=100., method='nearest')
            
            top_nose_shear = dataset["wind_speed"].sel(height=llj_nose_height, method='nearest') - dataset["wind_speed"].sel(height=slice(llj_nose_height[0], 1000.)).median()
            dataset.to_netcdf(nc_out_name)
            with Plugin() as plugin:
                plugin.upload_file(nc_out_name)
                plugin.upload_file(png_out_name)
                plugin.publish("lidar.hub_wind_spd", float(wind_rotor_spd), timestamp=time.time_ns())
                plugin.publish("lidar.hub_wind_dir", float(wind_rotor_dir), timestamp=time.time_ns())
                plugin.publish("lidar.llj_nose_height", float(llj_nose_height), timestamp=time.time_ns())
                plugin.publish("lidar.llj_nose_spd", float(llj_nose_spd), timestamp=time.time_ns())
                plugin.publish("lidar.llj_nose_dir", float(llj_nose_dir), timestamp=time.time_ns())
                plugin.publish("lidar.bottom_nose_shear", float(bottom_nose_shear), timestamp=time.time_ns())
                plugin.publish("lidar.top_nose_shear", float(top_nose_shear), timestamp=time.time_ns())
                    

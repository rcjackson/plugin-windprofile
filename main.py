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
        file_path = "/C:/Lidar/Data/Proc/%d/%d%02d/%d%02d%02d/" % (year, year, month, year, month, day)
        site = args.site
        with ssh.open_sftp() as sftp:
            logging.debug("Connected to the Lidar!")
            file_list = sftp.listdir(file_path)
            file_name = None
            file_list = sorted(file_list) 
            for f in file_list[:-1]:
                if args.profname in f:   
                    file_name = f

            if file_name is not None:
                sftp.get(os.path.join(file_path, file_name), file_name)
                dataset = read_as_netcdf(file_name, args.lat, args.lon, args.alt)
                dataset = dataset.isel(time=slice(dataset.sizes['time'] - 6, dataset.sizes['time']))
                dataset = act.retrievals.compute_winds_from_ppi(dataset, intensity_name='intensity')
                    
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
                png_out_name = '%s.lidar.wind_profile.%s.png' % (args.site, dataset['time'][0].dt.strftime('%Y%m%s.%H%M%S').values)
                nc_out_name = '%s.lidar.wind_profile.%s.nc' % (args.site, dataset['time'][0].dt.strftime('%Y%m%s.%H%M%S').values)
                fig.savefig(png_out_name, bbox_inches='tight', dpi=150)
                dataset.to_netcdf(nc_out_name)
                with Plugin() as plugin:
                        plugin.upload_file(nc_out_name)
                        plugin.upload_file(png_out_name)


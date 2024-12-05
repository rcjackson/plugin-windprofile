FROM waggle/plugin-base:1.1.1-base

WORKDIR /app
RUN apt-get update -y
RUN apt update -y
RUN apt-get install -y python3-h5py gcc python3-dev
RUN apt-get install -y python3-netcdf4
RUN apt-get install -y python3-h5netcdf
RUN pip3 install act-atmos
RUN pip3 install xarray
RUN pip3 install --upgrade pandas
RUN pip3 install paramiko
RUN pip3 install --upgrade pywaggle
COPY . .
ENTRYPOINT ["python3", "main.py"]
